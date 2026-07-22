"""
One-time patch: adds inspirehep_context, cadabra_context, derivation_checker
to (1) all four agent_transfer_map dict definitions and (2) record_status's
agent_for_sub_task Literal type constraint, in cmbagent/functions/status.py.

There are four identical copies of agent_transfer_map's 5-entry dict, at two
different indentation levels (three at 4-space, in _initialize_transfer_flags,
_determine_next_agent_human_in_loop, _determine_next_agent_default; one at
8-space, nested deeper in a formatting/reset method). All four get the same
three new entries.

Root cause: neither the tool schema nor the routing maps knew these three
agents existed, so controller could never route to them regardless of task
content - confirmed via a real test task designed to need all three, which
used none of them.

Run once from the repo root:
    python patch_status_agent_routing.py
"""

path = "cmbagent/functions/status.py"
marker = "hep-theory fork: added inspirehep_context/cadabra_context/derivation_checker"

with open(path, "r") as f:
    content = f.read()

if marker in content:
    print(f"Already patched: {path}")
    raise SystemExit(0)

new_entries = (
    '"inspirehep_context": "transfer_to_inspirehep_context",\n'
    '{indent}    "cadabra_context": "transfer_to_cadabra_context",\n'
    '{indent}    "derivation_checker": "transfer_to_derivation_checker",\n'
    '{indent}'
)

# --- 4-space indent variant (3 occurrences) ---
old_4 = '''    agent_transfer_map = {
        "engineer": "transfer_to_engineer",
        "researcher": "transfer_to_researcher",
        "idea_maker": "transfer_to_idea_maker",
        "idea_hater": "transfer_to_idea_hater",
        "camb_context": "transfer_to_camb_context",
    }'''

new_4 = '''    # hep-theory fork: added inspirehep_context/cadabra_context/derivation_checker
    agent_transfer_map = {
        "engineer": "transfer_to_engineer",
        "researcher": "transfer_to_researcher",
        "idea_maker": "transfer_to_idea_maker",
        "idea_hater": "transfer_to_idea_hater",
        "camb_context": "transfer_to_camb_context",
        "inspirehep_context": "transfer_to_inspirehep_context",
        "cadabra_context": "transfer_to_cadabra_context",
        "derivation_checker": "transfer_to_derivation_checker",
    }'''

count_4 = content.count(old_4)
if count_4 == 0:
    raise SystemExit("No 4-space-indent occurrences found - paste the file content so this can be adjusted.")
content = content.replace(old_4, new_4)  # replaces ALL occurrences
print(f"Replaced {count_4} occurrence(s) of the 4-space-indent agent_transfer_map")

# --- 8-space indent variant (1 occurrence) ---
old_8 = '''        agent_transfer_map = {
            "engineer": "transfer_to_engineer",
            "researcher": "transfer_to_researcher",
            "idea_maker": "transfer_to_idea_maker",
            "idea_hater": "transfer_to_idea_hater",
            "camb_context": "transfer_to_camb_context",
        }'''

new_8 = '''        # hep-theory fork: added inspirehep_context/cadabra_context/derivation_checker
        agent_transfer_map = {
            "engineer": "transfer_to_engineer",
            "researcher": "transfer_to_researcher",
            "idea_maker": "transfer_to_idea_maker",
            "idea_hater": "transfer_to_idea_hater",
            "camb_context": "transfer_to_camb_context",
            "inspirehep_context": "transfer_to_inspirehep_context",
            "cadabra_context": "transfer_to_cadabra_context",
            "derivation_checker": "transfer_to_derivation_checker",
        }'''

count_8 = content.count(old_8)
if count_8 == 0:
    print("WARNING: No 8-space-indent occurrence found - it may already differ from what was seen earlier, or use different indentation. Skipping this one; check manually if needed.")
else:
    content = content.replace(old_8, new_8)
    print(f"Replaced {count_8} occurrence(s) of the 8-space-indent agent_transfer_map")

# --- Literal type constraint on agent_for_sub_task ---
old_literal = '''agent_for_sub_task: Literal["engineer", "researcher", "idea_maker", "idea_hater",
                                    "camb_context", "classy_context", "aas_keyword_finder"],'''

new_literal = '''agent_for_sub_task: Literal["engineer", "researcher", "idea_maker", "idea_hater",
                                    "camb_context", "classy_context", "aas_keyword_finder",
                                    "inspirehep_context", "cadabra_context", "derivation_checker"],'''

count_lit = content.count(old_literal)
if count_lit == 0:
    print("WARNING: Literal type hint block not found exactly - paste the actual "
          "'grep -n \"agent_for_sub_task: Literal\" -A 3 cmbagent/functions/status.py' "
          "output so this can be adjusted.")
else:
    content = content.replace(old_literal, new_literal, 1)
    print(f"Replaced Literal type hint ({count_lit} occurrence)")

with open(path, "w") as f:
    f.write(content)

print(f"\nPatched: {path}")
