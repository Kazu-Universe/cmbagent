"""
One-time patch: decouples plan_recorder's routing (OnContextCondition, based on
feedback_left) from its own custom Python logic, moving the conditional routing
to a new pass-through node (plan_router). This fixes plan_recorder's
_record_plan_reply never executing (confirmed: AG2's swarm framework runs
OnContextConditions "before any other reply function" for whichever agent owns
them, and our earlier condition=None fix made the two branches mutually
exhaustive, so the context-condition check always fired first and permanently
preempted plan_recorder's own logic).

Three changes:
1. core_agent_names: add 'plan_router'
2. simple_handoffs: change plan_recorder's entry from a comment-only "special
   case" to an actual unconditional ('plan_recorder', 'plan_router') entry;
   the OLD add_context_conditions block on plan_recorder is removed
3. Add a new add_context_conditions block for plan_router with the same two
   conditions plan_recorder used to have

Run once:
    python patch_plan_recorder_routing.py
"""

path = "cmbagent/hand_offs.py"
marker = "hep-theory fork: plan_router decoupling"

with open(path, "r") as f:
    content = f.read()

if marker in content:
    print(f"Already patched: {path}")
    raise SystemExit(0)

# --- 1. Add plan_router to core_agent_names ---
old_core = "        'derivation_checker'\n    ]"
new_core = "        'derivation_checker',\n        'plan_router',  # hep-theory fork: plan_router decoupling\n    ]"

if content.count(old_core) != 1:
    raise SystemExit(
        f"Expected exactly 1 occurrence of the core_agent_names closing line, "
        f"found {content.count(old_core)}. Paste the relevant section so this can be adjusted."
    )
content = content.replace(old_core, new_core, 1)

# --- 2. Replace the OnContextCondition block on plan_recorder ---
old_routing = '''    agents['plan_recorder'].agent.handoffs.add_context_conditions([
        OnContextCondition(
            target=AgentTarget(agents['terminator'].agent),
            condition=ExpressionContextCondition(ContextExpression("${feedback_left} == 0")),
        ),
        OnContextCondition(
            target=AgentTarget(agents['plan_reviewer'].agent),
            condition=ExpressionContextCondition(ContextExpression("${feedback_left} != 0")),
        ),
    ])'''

new_routing = '''    # hep-theory fork: plan_router decoupling.
    # plan_recorder now hands off unconditionally to plan_router, so its own
    # Python logic (_record_plan_reply) actually gets to run and set
    # final_plan/proposed_plan/number_of_steps_in_plan. plan_router (which has
    # no competing custom reply logic of its own) carries the actual
    # feedback_left-based routing decision.
    agents['plan_recorder'].agent.handoffs.set_after_work(AgentTarget(agents['plan_router'].agent))

    agents['plan_router'].agent.handoffs.add_context_conditions([
        OnContextCondition(
            target=AgentTarget(agents['terminator'].agent),
            condition=ExpressionContextCondition(ContextExpression("${feedback_left} == 0")),
        ),
        OnContextCondition(
            target=AgentTarget(agents['plan_reviewer'].agent),
            condition=ExpressionContextCondition(ContextExpression("${feedback_left} != 0")),
        ),
    ])'''

if content.count(old_routing) != 1:
    raise SystemExit(
        f"Expected exactly 1 occurrence of the plan_recorder OnContextCondition block, "
        f"found {content.count(old_routing)}. Paste the relevant section so this can be adjusted."
    )
content = content.replace(old_routing, new_routing, 1)

with open(path, "w") as f:
    f.write(content)

print(f"Patched: {path}")
print("Added 'plan_router' to core_agent_names")
print("Replaced plan_recorder's OnContextCondition block with unconditional handoff to plan_router")
print("Added plan_router's own OnContextCondition block (same two conditions)")
