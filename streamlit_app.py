"""ForgeWorks AI: a production, maintenance, material and energy operating desk."""
import copy
import json
import os
import pandas as pd
import streamlit as st
from operations import FactoryTools, ROLES, load_state
from agent import ask

st.set_page_config(page_title='ForgeWorks AI | ONE Light Analytics',page_icon='🏭',layout='wide')
st.markdown('''<style>
.stApp{background:#f7f5ef;color:#102536}.block-container{padding-top:2rem;padding-bottom:3rem}
.fw-hero{padding:32px;background:linear-gradient(115deg,#071522,#203e4b);border-radius:16px;color:white;margin-bottom:24px}
.fw-hero h1{color:white;font-size:3rem;margin:12px 0}.fw-hero p{color:#d5dfe3;max-width:780px;font-size:1.05rem}
.fw-kicker{color:#e5bf7c;letter-spacing:.14em;font-size:12px;text-transform:uppercase}
[data-testid="stMetric"]{background:white;border:1px solid #d6dadd;border-radius:12px;padding:18px}
[data-testid="stMetricValue"]{color:#102536}.stButton button{min-height:44px;border-color:#b18a4c}.stButton button p{color:#102536}
</style>''',unsafe_allow_html=True)
if 'fw_state' not in st.session_state:
    st.session_state.fw_state=load_state()
if 'fw_messages' not in st.session_state:
    st.session_state.fw_messages=[]
with st.sidebar:
    st.subheader('ForgeWorks AI')
    st.caption('Manufacturing & energy operating demonstration')
    st.link_button('ONE Light Analytics','https://onelightanalytics.com/')
    role=st.selectbox('Demo role',list(ROLES),format_func=ROLES.get,key='fw_role')
    api_key=os.getenv('GEMINI_API_KEY') or os.getenv('GOOGLE_API_KEY') or ''
    if not api_key:
        try:
            api_key=st.secrets.get('GEMINI_API_KEY','') or st.secrets.get('GOOGLE_API_KEY','')
        except Exception:
            api_key=''
    modes=['Scenario mode']+(['Live AI'] if api_key else [])
    mode=st.radio('Agent mode',modes,index=len(modes)-1,key='fw_mode')
    st.caption('Scenario mode uses fixed operating tools. Live AI selects those tools. Both use fictional records.')
    if st.button('Reset plant session'):
        for k in ['fw_state','fw_messages','fw_pending','fw_proposal','fw_confirmed']:
            st.session_state.pop(k,None)
        st.rerun()
    st.caption('Fixed clock: 10 October 2026, 09:00 WAT. Records cover six completed shifts on 8–9 October. Role switching demonstrates permissions; it is not production authentication.')
context=(role,mode)
if st.session_state.get('fw_context')!=context:
    st.session_state.fw_context=context
    st.session_state.fw_messages=[]
    st.session_state.pop('fw_proposal',None)
    st.session_state.pop('fw_pending',None)
tools=FactoryTools(st.session_state.fw_state,role)
b=tools.get_plant_briefing()
st.markdown('''<div class="fw-hero"><div class="fw-kicker">ONE Light Analytics · Sector AI 03 / Manufacturing & energy</div><h1>ForgeWorks AI</h1><p>Keep production decisions connected to the whole plant.</p><p>Follow output losses, material exposure, maintenance work and energy use to the records behind them.</p></div>''',unsafe_allow_html=True)
if st.session_state.get('fw_flash'):
    st.success(st.session_state.pop('fw_flash'))
with st.expander('Start here · a three-minute plant walkthrough'):
    st.markdown('**1. Read Plant overview.** Separate gross output from saleable output.\n\n**2. Ask AI Agent.** Request a briefing, material risks or energy cost per good unit. Inspect tool evidence.\n\n**3. Review Action Lab.** Prepare a maintenance work-order draft for FW-A03. Confirm only after review, then inspect Audit trail. This changes fictional session records only.')
overview,chat,desk,lab,audit=st.tabs(['Plant overview','AI Agent','Evidence desk','Action Lab','Audit trail'])
with overview:
    st.subheader('Output is one part of the operating picture.')
    for cols,values in [(st.columns(3),[('Good units',f"{b['good_units']:,}"),('Good-output attainment',f"{b['good_attainment_pct']}%"),('Recorded rejects',f"{b['reject_rate_pct']}%")]),(st.columns(3),[('Downtime · line minutes',b['downtime_minutes']),('Material risks',b['material_alerts']),('Open work orders',b['open_work_orders'])])]:
        for col,(label,value) in zip(cols,values):
            col.metric(label,value)
    st.caption(f"{b['produced_units']:,} produced − {b['rejected_units']:,} rejected = {b['good_units']:,} good units; plan {b['target_units']:,}. Gross attainment {b['gross_attainment_pct']}%. This is not OEE. Downtime sums recorded line minutes across six shifts.")
    left,right=st.columns(2)
    with left:
        st.markdown('#### Production recovery')
        st.dataframe(pd.DataFrame(tools.get_production_exceptions()['records']),hide_index=True,width='stretch')
    with right:
        st.markdown('#### Material exposure')
        st.dataframe(pd.DataFrame(tools.get_material_risks()['records']),hide_index=True,width='stretch')
    energy=tools.get_energy_analysis()
    st.markdown('#### Energy per usable unit')
    cols=st.columns(3)
    cols[0].metric('Metered plant energy',f"{energy['metered_kwh']:,} kWh")
    cols[1].metric('Energy per good unit',f"{energy['kwh_per_good_unit']} kWh")
    if role=='manager':
        cols[2].metric('Grid + diesel cost per good unit',f"₦{energy['cost_per_good_unit_ngn']:,.2f}")
    else:
        cols[2].info('Cost details require the plant-manager role.')
    st.caption(energy['note'])
with chat:
    left,right=st.columns([1.7,1])
    with left:
        st.subheader('Ask ForgeWorks AI')
        for msg in st.session_state.fw_messages[-12:]:
            with st.chat_message(msg['role']):
                st.markdown(msg['content'])
                if msg.get('trace'):
                    with st.expander('Inspect tool evidence'):
                        st.json(msg['trace'])
        message=st.chat_input('Ask about production, materials, maintenance or energy',key='fw_chat')
        if st.session_state.get('fw_pending'):
            message=st.session_state.pop('fw_pending')
        if message:
            history=copy.deepcopy(st.session_state.fw_messages)
            st.session_state.fw_messages.append(dict(role='user',content=message))
            with st.chat_message('user'):
                st.markdown(message)
            with st.chat_message('assistant'):
                try:
                    with st.spinner('Checking the plant records…'):
                        result=ask(tools,message,api_key,mode=='Live AI',history)
                    st.markdown(result['text'])
                    st.caption(f"Mode: {result['mode']} · {ROLES[role]}")
                    with st.expander('Inspect tool evidence'):
                        st.json(result['trace'])
                    st.session_state.fw_messages.append(dict(role='assistant',content=result['text'],trace=result['trace']))
                except Exception:
                    st.error('The request could not complete. Try Scenario mode or a focused plant question. No work order or machine change was executed.')
    with right:
        st.subheader('Questions that lead to decisions')
        for label,prompt in {'Plant briefing':'Give me the plant briefing and immediate priorities.','Production losses':'Which production shifts need investigation?','Material risks':'Which materials could interrupt production?','Maintenance queue':'Show maintenance work orders and asset conditions.','Energy intensity':'Explain energy use and cost per good unit.'}.items():
            if st.button(label,key='fw_'+label,width='stretch'):
                st.session_state.fw_pending=prompt
                st.rerun()
        st.info('Read the evidence before approving an action. The agent cannot issue machine commands, release materials or send purchase orders.')
with desk:
    st.subheader('Follow a figure to its source.')
    collection=st.selectbox('Record collection',['Production shifts','Material risks','Maintenance orders','Energy records'])
    records={'Production shifts':tools.get_production_exceptions()['records'],'Material risks':tools.get_material_risks()['records'],'Maintenance orders':tools.get_maintenance_queue()['records'],'Energy records':tools.get_energy_analysis()['records']}[collection]
    if collection=='Production shifts':
        if st.checkbox('Include shifts without exceptions'):
            records=copy.deepcopy(tools.state['shifts'])
    frame=pd.DataFrame(records)
    st.dataframe(frame,hide_index=True,width='stretch')
    st.download_button('Download displayed records',frame.to_csv(index=False),'forgeworks-records.csv','text/csv')
    asset_id=st.selectbox('Inspect an asset',[a['asset_id'] for a in tools.state['assets']])
    st.json(tools.inspect_asset(asset_id))
with lab:
    st.subheader('Turn a verified issue into a reviewed work-order draft.')
    st.caption('Administrative simulation only. No equipment is stopped, serviced or restarted. No technician is contacted.')
    if role in {'manager','maintenance'}:
        with st.form('fw_prepare'):
            asset_id=st.selectbox('Asset',[a['asset_id'] for a in tools.state['assets']],index=2)
            priority=st.selectbox('Priority',['High','Normal'])
            issue=st.text_area('Issue for qualified maintenance review',value='Investigate recurring label stoppages recorded on packing line shifts.')
            prepare=st.form_submit_button('Prepare work-order proposal')
        if prepare:
            st.session_state.pop('fw_proposal',None)
            try:
                st.session_state.fw_proposal=tools.propose_work_order(asset_id,priority,issue)
                st.session_state.fw_confirmed=False
            except (ValueError,PermissionError) as exc:
                st.error(str(exc))
        proposal=st.session_state.get('fw_proposal')
        if proposal:
            st.json(proposal)
            with st.form('fw_commit'):
                confirmed=st.checkbox('I reviewed this asset, issue and priority; create the simulated work order.',key='fw_confirmed')
                commit=st.form_submit_button('Confirm simulated work order')
            if commit:
                try:
                    result=tools.commit_work_order(proposal,confirmed)
                    st.session_state.fw_flash=f"{result['after']['work_order_id']} created in this session. No external maintenance action occurred."
                    st.session_state.pop('fw_proposal',None)
                    st.rerun()
                except (ValueError,PermissionError) as exc:
                    st.error(str(exc))
    else:
        st.info('Production supervisors can inspect evidence. Work-order proposals require maintenance or plant management.')
with audit:
    st.subheader('A visible record of each confirmed simulation.')
    if tools.state['actions']:
        st.json(tools.state['actions'])
    else:
        st.info('No work-order draft has been committed in this session.')
    st.download_button('Download session audit',json.dumps(tools.state['actions'],indent=2),'forgeworks-audit.json','application/json')
st.caption('ForgeWorks Manufacturing is fictional. Demonstration data is synthetic and reproducible. These figures are not client results, live telemetry or achieved savings. Session reset discards simulated changes.')
