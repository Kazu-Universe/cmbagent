"""
Verification script: tests the multi-agent step-summary extraction logic
directly against a synthetic chat_history, matching the exact real scenario
from an earlier run (derivation_checker as the plan-assigned agent, with
controller also invoking inspirehep_context mid-step).

This is a standalone reproduction of the patched logic - not calling
deep_research() itself - to verify correctness deterministically without
depending on LLM behavior variance across runs.

Run:
    python verify_multi_agent_summary.py
"""

# Synthetic chat_history matching the real Step 3 scenario: derivation_checker
# is the plan-assigned agent, but controller also re-invoked inspirehep_context
# mid-step for extra literature verification.
fake_chat_history = [
    {"name": "control_starter", "content": "Step 3 starting."},
    {"name": "controller", "content": ""},
    {"name": "derivation_checker", "content": "Verdict: UNRESOLVED-DEGENERATE (first pass)"},
    {"name": "controller", "content": ""},
    {"name": "inspirehep_context", "content": "Re-checked literature: still no confirmed 2020+ paper."},
    {"name": "controller", "content": ""},
    {"name": "derivation_checker", "content": "Verdict: UNRESOLVED-DEGENERATE (final, after re-check)"},
    {"name": "terminator", "content": ""},
]

agent_for_step = "derivation_checker"
step = 3

# ---- exact patched logic, reproduced here for isolated testing ----
original_agent_for_step = agent_for_step
stripped_agent_for_step = agent_for_step.removesuffix("_context").removesuffix("_agent")
watched_names = {
    "engineer", "researcher", "cadabra_context",
    "inspirehep_context", "derivation_checker",
    original_agent_for_step, stripped_agent_for_step,
    f"{stripped_agent_for_step}_nest",
    f"{stripped_agent_for_step}_response_formatter",
}
agent_msgs = {}
for msg in fake_chat_history:
    name = msg.get('name')
    msg_content = (msg.get('content') or '').strip()
    if name in watched_names and msg_content:
        agent_msgs[name] = msg_content  # overwrite -> last message per agent wins

if agent_msgs:
    parts = [f"#### {name}\n{c}" for name, c in agent_msgs.items()]
    this_step_execution_summary = "\n\n".join(parts)
    summary = f"### Step {step}\n{this_step_execution_summary.strip()}"
else:
    summary = "(no content captured)"

# ---- checks ----
print("=== Captured agent_msgs keys ===")
print(list(agent_msgs.keys()))
print()
print("=== Full summary ===")
print(summary)
print()

assert "derivation_checker" in agent_msgs, "FAIL: derivation_checker not captured"
assert "inspirehep_context" in agent_msgs, "FAIL: inspirehep_context not captured (this is the bug we're fixing)"
assert "final, after re-check" in agent_msgs["derivation_checker"], \
    "FAIL: did not capture the LAST derivation_checker message (got an earlier one instead)"

print("PASS: both agents captured, and the LAST message per agent was kept (not an earlier one).")
