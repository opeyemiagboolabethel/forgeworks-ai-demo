"""Reproducible factory records and checked, session-only work-order actions."""
import copy
import json
from pathlib import Path

ROLES = {'manager': 'Plant manager', 'production': 'Production supervisor', 'maintenance': 'Maintenance coordinator'}

def load_state():
    return json.loads((Path(__file__).parent / 'data/operations.json').read_text())

class FactoryTools:
    def __init__(self, state, role='manager'):
        if role not in ROLES:
            raise PermissionError('Unknown demo role.')
        self.state, self.role = state, role

    def _record(self, collection, key, value):
        for record in self.state[collection]:
            if record[key] == value:
                return copy.deepcopy(record)
        raise ValueError(f'Unknown {key}: {value}')

    def get_plant_briefing(self):
        shifts = self.state['shifts']
        target = sum(s['target_units'] for s in shifts)
        made = sum(s['produced_units'] for s in shifts)
        rejected = sum(s['rejected_units'] for s in shifts)
        return dict(as_of=self.state['as_of'], period=self.state['period'],
                    target_units=target, produced_units=made, good_units=made-rejected,
                    rejected_units=rejected, gross_attainment_pct=round(made/target*100, 1),
                    good_attainment_pct=round((made-rejected)/target*100, 1),
                    reject_rate_pct=round(rejected/made*100, 2),
                    downtime_minutes=sum(s['downtime_minutes'] for s in shifts),
                    below_target_shifts=sum(s['produced_units'] < s['target_units'] for s in shifts),
                    total_shifts=len(shifts), material_alerts=len(self.get_material_risks()['records']),
                    open_work_orders=sum(w['status']=='Open' for w in self.state['work_orders']),
                    note='Completed-shift records; attainment is not OEE. Losses are not causal estimates.')

    def get_production_exceptions(self):
        return dict(records=[copy.deepcopy(s) for s in self.state['shifts'] if s['produced_units'] < s['target_units'] or s['rejected_units']/s['produced_units'] > .03],
                    rule='Below gross target, or recorded reject rate above 3%. Notes need investigation.')

    def inspect_asset(self, asset_id: str):
        asset = self._record('assets', 'asset_id', asset_id)
        orders = [copy.deepcopy(w) for w in self.state['work_orders'] if w['asset_id']==asset_id]
        return dict(asset=asset, work_orders=orders,
                    related_shifts=[copy.deepcopy(s) for s in self.state['shifts'] if s['asset_id']==asset_id])

    def get_maintenance_queue(self):
        return dict(records=copy.deepcopy(self.state['work_orders']),
                    assets=copy.deepcopy(self.state['assets']))

    def get_material_risks(self):
        records=[]
        for m in self.state['materials']:
            row=copy.deepcopy(m)
            row['usable_stock']=max(0, m['on_hand']-m['quarantined'])
            row['days_cover']=round(row['usable_stock']/m['daily_use'], 2)
            row['risk']=row['days_cover'] < m['lead_time_days']
            if row['risk']:
                records.append(row)
        return dict(records=records, rule='Usable stock / daily use < stated supplier lead time. Open purchase orders are not treated as received stock.')

    def get_energy_analysis(self):
        rows=[]
        for e in self.state['energy']:
            row=copy.deepcopy(e)
            row['cost_ngn']=round(e['grid_kwh']*e['grid_ngn_per_kwh']+e['diesel_litres']*e['diesel_ngn_per_litre'], 2)
            row['total_metered_kwh']=e['grid_kwh']+e['generator_kwh']
            rows.append(row)
        good=self.get_plant_briefing()['good_units']
        total=sum(r['cost_ngn'] for r in rows)
        result=dict(period=self.state['period'], records=rows,
                    metered_kwh=sum(r['total_metered_kwh'] for r in rows),
                    kwh_per_good_unit=round(sum(r['total_metered_kwh'] for r in rows)/good, 3),
                    note='Energy and production cover the same six completed shifts. Costs include grid and diesel only, excluding maintenance and capital costs. No savings claim or dispatch recommendation.')
        if self.role=='manager':
            result.update(cost_ngn=total, cost_per_good_unit_ngn=round(total/good, 2))
        else:
            for row in rows:
                for key in ['grid_ngn_per_kwh','diesel_ngn_per_litre','cost_ngn']:
                    row.pop(key, None)
        return result

    def propose_work_order(self, asset_id: str, priority: str, issue: str):
        if self.role not in {'manager','maintenance'}:
            raise PermissionError('Only plant management or maintenance can propose work orders.')
        asset=self._record('assets', 'asset_id', asset_id)
        if priority not in {'High','Normal'}:
            raise ValueError('Choose High or Normal priority.')
        issue=issue.strip()
        if not 12 <= len(issue) <= 300:
            raise ValueError('Describe the issue in 12–300 characters.')
        if any(w['asset_id']==asset_id and w['status']=='Open' for w in self.state['work_orders']):
            raise ValueError('An open work order already exists for this asset. Review it before creating another.')
        return dict(asset_id=asset_id, asset_name=asset['name'], priority=priority, issue=issue,
                    revision=self.state['revision'], role=self.role,
                    action='Create a session-only work-order draft; no machine or schedule change.')

    def commit_work_order(self, proposal, confirmed=False):
        if confirmed is not True:
            raise ValueError('Explicit confirmation is required.')
        if proposal.get('role')!=self.role:
            raise PermissionError('The proposal belongs to a different role.')
        if proposal.get('revision')!=self.state['revision']:
            raise ValueError('Records changed. Prepare a fresh proposal.')
        checked=self.propose_work_order(proposal['asset_id'],proposal['priority'],proposal['issue'])
        if checked!=proposal:
            raise ValueError('Proposal changed. Prepare and review a fresh proposal.')
        row=dict(work_order_id=f"FW-WO-{len(self.state['work_orders'])+1:03}", asset_id=proposal['asset_id'],
                 priority=proposal['priority'], issue=proposal['issue'], status='Open', created_at=self.state['as_of'])
        self.state['work_orders'].append(row)
        self.state['revision']+=1
        audit=dict(action_id=f"FW-ACT-{len(self.state['actions'])+1:03}", actor=self.role,
                   at=self.state['as_of'], revision=self.state['revision'], before=None, after=copy.deepcopy(row))
        self.state['actions'].append(audit)
        return copy.deepcopy(audit)

def scenario_answer(tools, message):
    text=message.lower()
    if 'energy' in text or 'cost' in text:
        tool='get_energy_analysis'; data=tools.get_energy_analysis()
        answer=f"Metered energy is {data['metered_kwh']:,} kWh across six shifts, or {data['kwh_per_good_unit']} kWh per good unit."
        if 'cost_ngn' in data:
            answer+=f" Recorded grid and diesel cost is ₦{data['cost_ngn']:,.0f} (₦{data['cost_per_good_unit_ngn']:,.2f} per good unit)."
        answer+=' Compare source mix and output by shift; these figures do not establish achievable savings.'
    elif 'material' in text or 'stock' in text:
        tool='get_material_risks'; data=tools.get_material_risks()
        answer='Material exposure: '+ '; '.join(f"{r['material_id']} {r['name']}: {r['days_cover']} days usable cover versus {r['lead_time_days']} days lead time" for r in data['records'])+'. Verify quarantine and supplier receipt dates before committing production.'
    elif 'maintenance' in text or 'work order' in text:
        tool='get_maintenance_queue'; data=tools.get_maintenance_queue()
        answer='Review existing work orders: '+ '; '.join(f"{r['work_order_id']} ({r['asset_id']}): {r['priority']} — {r['issue']}" for r in data['records'])+'. New proposals require review in Action Lab; no machine command is available.'
    elif 'production' in text or 'shift' in text:
        tool='get_production_exceptions'; data=tools.get_production_exceptions()
        answer='Investigate '+', '.join(r['shift_id'] for r in data['records'])+'. Compare target, actual output, rejects and downtime in the evidence. The recorded issue note does not prove causation.'
    else:
        tool='get_plant_briefing'; data=tools.get_plant_briefing()
        answer=f"The six completed shifts produced {data['produced_units']:,} units against {data['target_units']:,} planned. After {data['rejected_units']:,} rejects, {data['good_units']:,} good units remain ({data['good_attainment_pct']}% of plan). Recorded downtime totals {data['downtime_minutes']} minutes. Review {data['below_target_shifts']} below-target shifts, {data['material_alerts']} material risks and {data['open_work_orders']} open work orders."
    return dict(text=answer,mode='scenario',trace=[dict(tool=tool,result=data)])
