"""Read and proposal tools for ForgeWorks; human confirmation remains outside the model."""
import os
from operations import scenario_answer

def ask(tools, message, api_key='', live=False, history=None):
    if not live:
        return scenario_answer(tools,message)
    if not api_key:
        raise ValueError('Choose Scenario mode until Live AI is configured.')
    from google import genai
    from google.genai import types
    trace=[]
    def run(name,**args):
        try:
            result=getattr(tools,name)(**args)
        except (ValueError,KeyError,PermissionError) as exc:
            result=dict(error=str(exc))
        trace.append(dict(tool=name,result=result))
        return result
    def get_plant_briefing()->dict:
        """Read reconciled output, rejects, downtime and management exceptions for six shifts."""
        return run('get_plant_briefing')
    def get_production_exceptions()->dict:
        """List below-target shifts and shifts with reject rate above three percent."""
        return run('get_production_exceptions')
    def inspect_asset(asset_id:str)->dict:
        """Read asset, work orders and shift evidence by FW-asset ID."""
        return run('inspect_asset',asset_id=asset_id)
    def get_maintenance_queue()->dict:
        """Read maintenance orders and recorded asset conditions."""
        return run('get_maintenance_queue')
    def get_material_risks()->dict:
        """Inspect usable stock cover against supplier lead times, excluding quarantined stock."""
        return run('get_material_risks')
    def get_energy_analysis()->dict:
        """Read grid and metered generator energy for the same shifts; manager-only costs."""
        return run('get_energy_analysis')
    def propose_work_order(asset_id:str,priority:str,issue:str)->dict:
        """Validate a proposed work-order draft. Does not write; human review is required."""
        return run('propose_work_order',asset_id=asset_id,priority=priority,issue=issue)
    prompt=f'''You are ForgeWorks AI, a fictional Lagos packaging plant operating assistant. Role: {tools.role}. Fixed business clock: {tools.state['as_of']}. Production and energy records are six completed shifts, not today's live sensors. Call relevant tools before every factual claim about records, figures, capacity or costs. Cite IDs and evidence. Distinguish produced, rejected and good units. Attainment is not OEE. The downtime_minutes total covers ALL six shifts; never describe it as downtime across only below-target shifts. Use below_target_downtime_minutes when discussing that subset. Downtime entries do not prove a root cause. Never say a recorded condition caused or contributed to missed output; say it was reported during a shift and warrants investigation. Stock cover excludes quarantine; purchase orders are not receipts. Do not invent fault diagnosis, causal savings, energy forecasts or sensor readings. Follow permission errors. Only plant manager sees costs. Propose investigation and administrative work-order drafts, never machine operation, electrical work, isolation steps or production release. No tool can commit an action; direct the user to Action Lab for review and confirmation. Never claim external work, sending or a machine change occurred. Keep answers concise with priorities and evidence.'''
    context='\n'.join(f"{m['role']}: {m['content']}" for m in (history or [])[-6:])
    client=genai.Client(api_key=api_key,http_options=types.HttpOptions(timeout=45000))
    response=client.models.generate_content(model=os.getenv('GEMINI_MODEL','gemini-3.5-flash-lite'),contents=(context+'\nUser: '+message).strip(),config=types.GenerateContentConfig(system_instruction=prompt,temperature=.1,tools=[get_plant_briefing,get_production_exceptions,inspect_asset,get_maintenance_queue,get_material_risks,get_energy_analysis,propose_work_order],automatic_function_calling=types.AutomaticFunctionCallingConfig(maximum_remote_calls=7)))
    return dict(text=response.text or 'No answer returned. Try a focused plant question.',mode='live-ai',trace=trace)
