from types import SimpleNamespace
from unittest.mock import patch
from operations import FactoryTools, load_state
from agent import ask

def generate(**kwargs):
    functions=kwargs['config'].tools
    assert len(functions)==7
    assert 'commit_work_order' not in [fn.__name__ for fn in functions]
    assert functions[0]()['good_units']==50498
    assert functions[-1]('FW-A03','High','Investigate recurring label stoppages')['revision']==0
    return SimpleNamespace(text='Review the production and maintenance evidence.')
with patch('google.genai.Client',return_value=SimpleNamespace(models=SimpleNamespace(generate_content=generate))):
    t=FactoryTools(load_state())
    r=ask(t,'What needs attention?','test-only-placeholder',True)
    assert len(r['trace'])==2 and r['mode']=='live-ai'
    assert len(t.state['work_orders'])==2
print('PASS: SDK tool wiring, retained evidence, non-mutating proposal and no model commit tool')
