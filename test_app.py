"""End-to-end scenario, approval and permission checks against Streamlit."""
from pathlib import Path
from streamlit.testing.v1 import AppTest

at=AppTest.from_file(str(Path(__file__).parent/'streamlit_app.py'),default_timeout=20).run()
assert not at.exception
assert at.metric[0].value=='50,498'
next(b for b in at.button if b.label=='Plant briefing').click().run()
assert not at.exception
assert len(at.session_state['fw_messages'])==2
assert '50,498' in at.session_state['fw_messages'][-1]['content']
next(b for b in at.button if b.label=='Prepare work-order proposal').click().run()
assert at.session_state['fw_proposal']['asset_id']=='FW-A03'
next(b for b in at.button if b.label=='Confirm simulated work order').click().run()
assert any('confirmation' in e.value.lower() for e in at.error)
assert len(at.session_state['fw_state']['work_orders'])==2
next(c for c in at.checkbox if c.key=='fw_confirmed').check().run()
next(b for b in at.button if b.label=='Confirm simulated work order').click().run()
assert not at.exception
assert len(at.session_state['fw_state']['actions'])==1
assert at.session_state['fw_state']['work_orders'][-1]['work_order_id']=='FW-WO-003'
at.selectbox(key='fw_role').select('production').run()
assert not at.exception
assert at.session_state['fw_messages']==[]
assert not any(b.label=='Prepare work-order proposal' for b in at.button)
assert not any(m.label=='Grid + diesel cost per good unit' for m in at.metric)
next(b for b in at.button if b.label=='Reset plant session').click().run()
assert not at.exception
assert len(at.session_state['fw_state']['work_orders'])==2
print('PASS: application renders, scenario response, explicit confirmation, audit, role isolation and reset')
