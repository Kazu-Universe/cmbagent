"""
One-time patch: fixes deep_research.py's per-step loop only loading the plan
file's actual sub_task/instructions/agent for step==1. For step>1, it only set
agent_for_sub_task (inherited stale from previous step's context) and never
set current_sub_task/current_instructions from the plan file at all - meaning
every step after the first showed frozen Step-1 task text instead of
advancing through the actual plan.

Run once from the repo root:
    python patch_deep_research_step_advance.py
"""

path = "cmbagent/workflows/deep_research.py"
marker = "hep-theory fork: explicit per-step plan loading"

with open(path, "r") as f:
    content = f.read()

if marker in content:
    print(f"Already patched: {path}")
    raise SystemExit(0)

old = '''        if step == 1:
            plan_input = load_plan(os.path.join(work_dir, "planning/final_plan.json"))["sub_tasks"]
            agent_for_step = plan_input[0]['sub_task_agent']
        else:
            agent_for_step = current_context['agent_for_sub_task']

        parsed_context = copy.deepcopy(current_context)
        parsed_context["agent_for_sub_task"] = agent_for_step
        parsed_context["current_plan_step_number"] = step
        parsed_context["n_attempts"] = 0  # reset number of failures for each step'''

new = '''        # hep-theory fork: explicit per-step plan loading. The plan file is now
        # loaded and applied for EVERY step, not just step 1 - previously,
        # current_sub_task/current_instructions were never set from the plan
        # file for step>1, only inherited stale from the previous step's
        # context, causing every step after the first to show frozen Step-1
        # task text instead of advancing through the actual plan.
        plan_input = load_plan(os.path.join(work_dir, "planning/final_plan.json"))["sub_tasks"]
        this_step_entry = plan_input[step - 1]
        agent_for_step = this_step_entry['sub_task_agent']

        parsed_context = copy.deepcopy(current_context)
        parsed_context["agent_for_sub_task"] = agent_for_step
        parsed_context["current_sub_task"] = this_step_entry.get('sub_task', parsed_context.get('current_sub_task'))
        parsed_context["current_instructions"] = "\\n".join(
            f"- {b}" for b in this_step_entry.get('bullet_points', [])
        ) or parsed_context.get('current_instructions')
        parsed_context["current_plan_step_number"] = step
        parsed_context["n_attempts"] = 0  # reset number of failures for each step'''

if old not in content:
    raise SystemExit(
        f"Expected exact block not found in {path} - paste the file content "
        "so it can be adjusted (the plan_input JSON key names may differ "
        "from what this patch assumes - check final_plan.json's actual "
        "structure with: python -c \"import json; print(json.load(open('output/.../planning/final_plan.json'))['sub_tasks'][0].keys())\")"
    )

content = content.replace(old, new)

with open(path, "w") as f:
    f.write(content)

print(f"Patched: {path}")
