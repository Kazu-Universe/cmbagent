"""
Diagnostic run: monkeypatches _generate_group_tool_reply to print the agent
name and message content right before the crash point, so we can see exactly
which agent produced a message with tool_calls=[] instead of a real tool call
or no tool_calls key at all.

Run once for diagnosis, then discard — this is not meant to be a permanent fix.
"""

from autogen.agentchat.group import group_tool_executor as gte

_original = gte.GroupToolExecutor._generate_group_tool_reply

def _patched(self, agent, messages=None, sender=None, config=None):
    msgs = messages if messages is not None else agent._oai_messages[sender]
    last_msg = msgs[-1] if msgs else None
    print(f"\n>>> DIAGNOSTIC: _generate_group_tool_reply called")
    print(f">>> agent.name = {getattr(agent, 'name', '?')}")
    print(f">>> 'tool_calls' in message: {'tool_calls' in last_msg if last_msg else 'N/A'}")
    if last_msg and "tool_calls" in last_msg:
        print(f">>> tool_calls value: {last_msg['tool_calls']}")
    print(f">>> message content (truncated): {str(last_msg.get('content'))[:300] if last_msg else 'N/A'}")
    return _original(self, agent, messages=messages, sender=sender, config=config)

gte.GroupToolExecutor._generate_group_tool_reply = _patched

# ---- rest is identical to test_bh_entropy.py ----

from cmbagent import CMBAgent
from cmbagent.utils.utils import get_api_keys_from_env

agent_llm_configs = {
    "aas_keyword_finder":            {"model": "claude-haiku-4-5-20251001"},
    "engineer":                      {"model": "claude-sonnet-5"},
    "planner":                       {"model": "claude-fable-5"},
    "plan_reviewer":                 {"model": "claude-sonnet-5"},
    "summarizer_response_formatter": {"model": "claude-haiku-4-5-20251001"},
    "researcher":                    {"model": "claude-sonnet-5"},
    "summarizer":                    {"model": "claude-haiku-4-5-20251001"},
    "idea_maker":                    {"model": "claude-fable-5"},
    "idea_hater":                    {"model": "claude-fable-5"},
    "camb_context":                  {"model": "claude-sonnet-5"},
    "derivation_checker":            {"model": "claude-sonnet-5"},
    "cadabra_context":               {"model": "claude-sonnet-5"},
    "inspirehep_context":            {"model": "claude-sonnet-5"},
}

c = CMBAgent(
    agent_list=[
        "engineer", "controller", "planner",
        "inspirehep_context", "cadabra_context", "derivation_checker",
    ],
    api_keys=get_api_keys_from_env(),
    default_llm_model="claude-sonnet-5",
    default_formatter_model="claude-haiku-4-5-20251001",
    agent_llm_configs=agent_llm_configs,
    top_p=None,
)

task = (
    "Verify that the Bekenstein-Hawking entropy formula S = A / (4G) "
    "(in natural units, hbar = c = k_B = 1) is dimensionally consistent. "
    "Then state explicitly what the formula reduces to in the classical "
    "limit hbar -> 0, and note that the semiclassical treatment breaks down "
    "in that limit rather than the formula having a smooth classical analog."
)

c.solve(
    task,
    initial_agent="planner",
    mode="default",
    max_rounds=10,
)
