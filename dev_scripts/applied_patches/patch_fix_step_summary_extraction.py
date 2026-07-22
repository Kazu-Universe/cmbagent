"""
One-time patch: fixes deep_research.py's cross-step summary extraction. The
existing logic strips "_context"/"_agent" from agent_for_step before
searching chat_history for a matching message name - a naming convention
built for camb_context (which has a camb_response_formatter companion, so
the stripped name + "_response_formatter" correctly matches). Our
inspirehep_context and cadabra_context agents deliberately don't have
_response_formatter companions (they hand off directly to controller), so
this lookup never found a match - meaning their real output silently never
got threaded into previous_steps_execution_summary at all. Confirmed via a
real run: derivation_checker correctly reported "Full output from previous
plan steps" as empty, even after adding the template variable to its prompt
(the variable itself was never populated in the first place).

Fix: also check the ORIGINAL, unstripped agent name against the message
name - computed once before the search loop rather than mutated in-place on
every iteration (the original code re-derived the stripped name inside the
loop body on every message, which is idempotent-safe but messy).

Run once from the repo root:
    python patch_fix_step_summary_extraction.py
"""

path = "cmbagent/workflows/deep_research.py"
marker = "hep-theory fork: check original unstripped agent name"

with open(path, "r") as f:
    content = f.read()

if marker in content:
    print(f"Already patched: {path}")
    raise SystemExit(0)

old = '''        for msg in results['chat_history'][::-1]:
            if 'name' in msg:
                agent_for_step = agent_for_step.removesuffix("_context")
                agent_for_step = agent_for_step.removesuffix("_agent")
                if msg['name'] == agent_for_step or msg['name'] == f"{agent_for_step}_nest" or msg['name'] == f"{agent_for_step}_response_formatter":
                    this_step_execution_summary = msg['content']
                    summary = f"### Step {step}\\n{this_step_execution_summary.strip()}"
                    step_summaries.append(summary)
                    cmbagent.final_context['previous_steps_execution_summary'] = "\\n\\n".join(step_summaries)
                    break'''

new = '''        # hep-theory fork: check original unstripped agent name - fixes
        # custom agents (inspirehep_context, cadabra_context) that don't have
        # a _response_formatter companion, so the stripped-name lookup below
        # (built for camb_context's convention) never matched their real
        # output, silently leaving previous_steps_execution_summary empty.
        original_agent_for_step = agent_for_step
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

count = content.count(old)
if count != 1:
    raise SystemExit(
        f"Expected exactly 1 occurrence, found {count}. Paste the actual "
        "content (lines 438-447) so this can be adjusted."
    )

content = content.replace(old, new, 1)

with open(path, "w") as f:
    f.write(content)

print(f"Patched: {path}")
