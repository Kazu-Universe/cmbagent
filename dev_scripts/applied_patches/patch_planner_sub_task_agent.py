"""
One-time patch: adds inspirehep_context, cadabra_context, derivation_checker
to planner_response_formatter's sub_task_agent Literal type constraint.

This is the actual root gate: the planner's structured-output schema
(PlannerResponse, enforced via Pydantic response_format) restricts
sub_task_agent to a fixed Literal set. Even with record_status's routing
fixed (previous patch), the plan itself could never assign a step to one of
our three agents, since the schema rejected it as an invalid enum value -
meaning deep_research()'s step loop would never even attempt to route there.

Run once from the repo root:
    python patch_planner_sub_task_agent.py
"""

path = "cmbagent/agents/planning/planner_response_formatter/planner_response_formatter.py"
marker = "hep-theory fork: added inspirehep_context/cadabra_context/derivation_checker"

with open(path, "r") as f:
    content = f.read()

if marker in content:
    print(f"Already patched: {path}")
    raise SystemExit(0)

old = '    sub_task_agent: Literal["engineer", "researcher", "idea_maker", "idea_hater", "camb_context"] =  Field(..., description="The name of the agent in charge of the sub-task")'

new = (
    '    # hep-theory fork: added inspirehep_context/cadabra_context/derivation_checker\n'
    '    sub_task_agent: Literal["engineer", "researcher", "idea_maker", "idea_hater", "camb_context",\n'
    '                            "inspirehep_context", "cadabra_context", "derivation_checker"] =  '
    'Field(..., description="The name of the agent in charge of the sub-task")'
)

count = content.count(old)
if count != 1:
    raise SystemExit(
        f"Expected exactly 1 occurrence, found {count}. Paste the actual line "
        "(grep -n 'sub_task_agent: Literal' <path>) so this can be adjusted."
    )

content = content.replace(old, new, 1)

with open(path, "w") as f:
    f.write(content)

print(f"Patched: {path}")
