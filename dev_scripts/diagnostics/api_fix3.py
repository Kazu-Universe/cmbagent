from cmbagent import CMBAgent
from cmbagent.utils.utils import get_api_keys_from_env

agent_llm_configs = {
    "aas_keyword_finder":           {"model": "claude-haiku-4-5-20251001"},
    "engineer":                     {"model": "claude-sonnet-5"},
    "planner":                      {"model": "claude-fable-5"},
    "plan_reviewer":                {"model": "claude-sonnet-5"},
    "summarizer_response_formatter":{"model": "claude-haiku-4-5-20251001"},
    "researcher":                   {"model": "claude-sonnet-5"},
    "summarizer":                   {"model": "claude-haiku-4-5-20251001"},
    "idea_maker":                   {"model": "claude-fable-5"},
    "idea_hater":                   {"model": "claude-fable-5"},
    "camb_context":                 {"model": "claude-sonnet-5"}
}

c = CMBAgent(
    agent_list=['engineer', 'controller', 'inspirehep_context', 'cadabra_context', 'derivation_checker'],
    api_keys=get_api_keys_from_env(),
    default_llm_model='claude-sonnet-5',
    default_formatter_model='claude-haiku-4-5-20251001',
    agent_llm_configs=agent_llm_configs,
)
print(c.agent_names)