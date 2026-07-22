"""
One-time patch: fixes deep_research.py's step-summary extraction to capture
EVERY content-bearing agent that spoke during a step, not just the single
agent matching agent_for_step (the plan-assigned agent).

Root cause: controller can invoke additional agents at its own discretion
beyond the plan's assignment (confirmed via a real run: Step 3 was assigned
to derivation_checker, but controller also re-invoked inspirehep_context
mid-step for extra literature verification). The previous fix (checking the
original unstripped agent name) correctly captures the ONE plan-assigned
agent, but any additional discretionarily-invoked agent's contribution was
still silently dropped from previous_steps_execution_summary - harmless if
that step happens to be the last one, but would silently drop real context
from any earlier step in a longer plan.

Fix: iterate forward through chat_history once, keeping the LAST message
seen for every agent whose name is either a known content-bearing agent
(engineer, researcher, cadabra_context, inspirehep_context,
derivation_checker) or matches the plan-assigned agent / its
_response_formatter variant (preserving backward compatibility with
camb_context's convention). Combine all captured agents' final messages into
one labeled summary block per step, rather than just the single
plan-assigned agent's output.

Run once from the repo root:
    python patch_multi_agent_step_summary.py
"""

path = "cmbagent/workflows/deep_research.py"
marker = "hep-theory fork: capture ALL content-bearing agents"

with open(path, "r") as f:
    content = f.read()

if marker in content:
    print(f"Already patched: {path}")
    raise SystemExit(0)

old = '''        original_agent_for_step = agent_for_step
        stripped_agent_for_step = agent_for_step.removesuffix("_context").removesuffix("_agent")
        for msg in results['chat_history'][::-1]:
            if 'name' in msg:
                if (msg['name'] == original_agent_for_step
                        or msg['name'] == stripped_agent_for_step
                        or msg['name'] == f"{stripped_agent_for_step}_nest"
                        or msg['name'] == f"{stripped_agent_for_step}_response_formatter"):
                    this_step_execution_summary = msg['content']
                    summary = f"### Step {step}\\n{this_step_execution_summary.strip()}"
                    step_summaries.append(summary)
                    cmbagent.final_context['previous_steps_execution_summary'] = "\\n\\n".join(step_summaries)
                    break'''

new = '''        # hep-theory fork: capture ALL content-bearing agents that spoke this
        # step, not just the single plan-assigned agent - controller can
        # invoke additional agents at its own discretion (e.g. re-checking
        # literature via inspirehep_context mid-step), and their
        # contributions were previously silently dropped if they weren't the
        # one agent matching agent_for_step.
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
        for msg in results['chat_history']:
            name = msg.get('name')
            msg_content = (msg.get('content') or '').strip()
            if name in watched_names and msg_content:
                agent_msgs[name] = msg_content  # overwrite -> last message per agent wins
        if agent_msgs:
            parts = [f"#### {name}\\n{c}" for name, c in agent_msgs.items()]
            this_step_execution_summary = "\\n\\n".join(parts)
            summary = f"### Step {step}\\n{this_step_execution_summary.strip()}"
            step_summaries.append(summary)
            cmbagent.final_context['previous_steps_execution_summary'] = "\\n\\n".join(step_summaries)'''

count = content.count(old)
if count != 1:
    raise SystemExit(
        f"Expected exactly 1 occurrence, found {count}. Paste the actual "
        "content so this can be adjusted."
    )

content = content.replace(old, new, 1)

with open(path, "w") as f:
    f.write(content)

print(f"Patched: {path}")
