"""
One-time patch: fixes two issues in cmbagent/functions/planning.py's
create_record_plan_constraints (plan_setter's tool function):

1. needed_agents' Literal type constraint doesn't include
   inspirehep_context/cadabra_context/derivation_checker (same class of gap
   fixed elsewhere for record_status and the planner's own schema).

2. More importantly, a genuine pre-existing fragility, unrelated to our
   agents: the function unconditionally calls get_agent_from_name() on every
   LLM-selected agent name, with no check for whether it's actually
   registered in this session's agent_list. get_agent_from_name() calls
   sys.exit() on a miss - meaning ANY Literal-permitted-but-unregistered
   choice (e.g. "classy_context", which is a legitimate Literal option but
   was never added to our agent_list) crashes the entire process outright.
   Confirmed via a real crash: plan_setter selected "classy_context" for a
   black-hole-entropy task where it's irrelevant, and the whole run died.

   Fixed by skipping (with a printed warning) any selected agent that isn't
   actually registered, rather than crashing.

Run once from the repo root:
    python patch_plan_setter_agent_lookup.py
"""

path = "cmbagent/functions/planning.py"
marker = "hep-theory fork: added inspirehep_context/cadabra_context/derivation_checker"

with open(path, "r") as f:
    content = f.read()

if marker in content:
    print(f"Already patched: {path}")
    raise SystemExit(0)

# --- 1. Literal type constraint ---
old_literal = '''        needed_agents: List[Literal["engineer", "researcher", "idea_maker", "idea_hater",
                                    "camb_context", "classy_context", "aas_keyword_finder"]],'''

new_literal = '''        # hep-theory fork: added inspirehep_context/cadabra_context/derivation_checker
        needed_agents: List[Literal["engineer", "researcher", "idea_maker", "idea_hater",
                                    "camb_context", "classy_context", "aas_keyword_finder",
                                    "inspirehep_context", "cadabra_context", "derivation_checker"]],'''

count_lit = content.count(old_literal)
if count_lit != 1:
    raise SystemExit(
        f"Expected exactly 1 occurrence of the Literal block, found {count_lit}. "
        "Paste the actual content so this can be adjusted."
    )
content = content.replace(old_literal, new_literal, 1)

# --- 2. Defensive agent lookup, skip unregistered choices instead of crashing ---
old_loop = '''        for agent in set(needed_agents):
            agent_object = cmbagent_instance.get_agent_from_name(agent)
            str_to_append += f'- {agent}: {agent_object.description}\''''

new_loop = '''        # hep-theory fork: defensive lookup - skip any LLM-selected agent name
        # that isn't actually registered in this session, rather than crashing
        # the whole process via get_agent_from_name()'s sys.exit() on a miss.
        registered_names = {a.info['name'] for a in cmbagent_instance.agents}
        for agent in set(needed_agents):
            if agent not in registered_names:
                print(f"WARNING: plan_setter selected '{agent}' but it is not "
                      f"registered in this session's agent_list - skipping.")
                continue
            agent_object = cmbagent_instance.get_agent_from_name(agent)
            str_to_append += f'- {agent}: {agent_object.description}\''''

count_loop = content.count(old_loop)
if count_loop != 1:
    raise SystemExit(
        f"Expected exactly 1 occurrence of the lookup loop, found {count_loop}. "
        "Paste the actual content so this can be adjusted."
    )
content = content.replace(old_loop, new_loop, 1)

with open(path, "w") as f:
    f.write(content)

print(f"Patched: {path}")
print("Added inspirehep_context/cadabra_context/derivation_checker to needed_agents Literal")
print("Made agent lookup defensive against unregistered agent choices (fixes classy_context crash)")
