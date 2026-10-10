import copy
import unittest
from operations import FactoryTools, load_state, scenario_answer

class FactoryChecks(unittest.TestCase):
    def setUp(self):
        self.t=FactoryTools(load_state())
    def test_reconciled_production(self):
        b=self.t.get_plant_briefing()
        self.assertEqual((b['target_units'],b['produced_units'],b['rejected_units'],b['good_units']),(56000,51800,1302,50498))
        self.assertEqual((b['below_target_shifts'],b['downtime_minutes'],b['material_alerts']),(4,290,2))
        self.assertEqual(b['good_attainment_pct'],90.2)
    def test_material_quarantine_and_open_po(self):
        rows=self.t.get_material_risks()['records']
        self.assertEqual([r['material_id'] for r in rows],['FW-M01','FW-M03'])
        self.assertEqual(rows[0]['usable_stock'],6800)
        self.assertEqual(rows[0]['days_cover'],3.4)
    def test_energy_matched_period(self):
        e=self.t.get_energy_analysis()
        self.assertEqual((e['metered_kwh'],e['cost_ngn'],e['cost_per_good_unit_ngn']),(5950,1687500,33.42))
        self.assertEqual({r['shift_id'] for r in e['records']},{r['shift_id'] for r in self.t.state['shifts']})
    def test_cost_permissions(self):
        for role in ['production','maintenance']:
            e=FactoryTools(load_state(),role).get_energy_analysis()
            self.assertNotIn('cost_ngn',e)
            self.assertNotIn('cost_per_good_unit_ngn',e)
            for r in e['records']:
                self.assertFalse({'cost_ngn','diesel_ngn_per_litre','grid_ngn_per_kwh'} & r.keys())
    def test_requires_confirmation_and_is_non_mutating(self):
        before=copy.deepcopy(self.t.state)
        p=self.t.propose_work_order('FW-A03','High','Investigate recurring label stoppages')
        self.assertEqual(before,self.t.state)
        with self.assertRaises(ValueError):self.t.commit_work_order(p)
        self.assertEqual(before,self.t.state)
        result=self.t.commit_work_order(p,True)
        self.assertEqual(result['after']['work_order_id'],'FW-WO-003')
        self.assertEqual(self.t.get_plant_briefing()['open_work_orders'],3)
        self.assertEqual(len(self.t.state['actions']),1)
        self.assertEqual(load_state()['revision'],0)
    def test_duplicates_unknown_and_role(self):
        with self.assertRaises(ValueError):self.t.propose_work_order('FW-A01','High','Investigate recorded vibration')
        with self.assertRaises(ValueError):self.t.propose_work_order('FW-NOTFOUND','High','Investigate reported problem')
        with self.assertRaises(PermissionError):FactoryTools(load_state(),'production').propose_work_order('FW-A03','High','Investigate recorded stoppages')
    def test_stale_tampered_and_cross_role(self):
        p=self.t.propose_work_order('FW-A03','High','Investigate recurring label stoppages')
        with self.assertRaises(PermissionError):FactoryTools(self.t.state,'maintenance').commit_work_order(p,True)
        bad=copy.deepcopy(p);bad['asset_name']='Forged name'
        with self.assertRaises(ValueError):self.t.commit_work_order(bad,True)
        self.t.state['revision']+=1
        with self.assertRaises(ValueError):self.t.commit_work_order(p,True)
    def test_scenarios_have_evidence(self):
        for prompt in ['briefing','production shifts','stock material','energy costs','maintenance']:
            r=scenario_answer(self.t,prompt)
            self.assertTrue(r['trace'][0]['result'])
            self.assertEqual(r['mode'],'scenario')

if __name__=='__main__':unittest.main()
