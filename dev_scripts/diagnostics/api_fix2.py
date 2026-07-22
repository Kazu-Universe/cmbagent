import autogen
autogen.cmbagent_debug = True
from cmbagent import CMBAgent
from cmbagent.utils.utils import get_api_keys_from_env

c = CMBAgent(
    agent_list=['engineer', 'controller', 'inspirehep_context', 'cadabra_context', 'derivation_checker'],
    api_keys=get_api_keys_from_env(),
    default_llm_model='claude-sonnet-5',
    default_formatter_model='claude-haiku-4-5-20251001',
)
print(c.agent_names)