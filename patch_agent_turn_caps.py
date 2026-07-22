"""
One-time patch: fixes an unbounded tool-call loop risk in set_assistant_agent
(base_agent.py) that was silently draining tokens - confirmed via real cost
reports from the 2026-07-22 AdS KK-tower localization run, where
inspirehep_context alone used 44,313,274 prompt tokens in one step (roughly
4,300x the controller's usage in the same step), consistent with an agent
whose tool-call turns are uncapped resending its full, growing conversation
history as the prompt on every turn.

ROOT CAUSE: set_code_agent (used by engineer) passes
max_consecutive_auto_reply=self.info["max_consecutive_auto_reply"] to its
underlying agent. set_assistant_agent - used by inspirehep_context,
cadabra_context, and derivation_checker (all added in this fork), and also
by the upstream camb_context - never passes this parameter at all, for any
of its branches. CmbAgentSwarmAgent is a bare ConversableAgent subclass
with no override, so the framework default (unbounded) applies with no cap
in this code path.

THIS PATCH:
1. Wires max_consecutive_auto_reply through in set_assistant_agent's
   default branch (used by inspirehep_context/cadabra_context/
   derivation_checker/camb_context), reading it from self.info via .get()
   with a None default - so any agent whose yaml does NOT set this key
   keeps its exact current (unbounded) behavior. This is a pure additive
   change: nothing is capped unless a yaml explicitly asks for it.
2. Adds an explicit cap to inspirehep_context.yaml (40 - comfortably above
   the 35 live queries a real successful run already needed) and to
   cadabra_context.yaml / derivation_checker.yaml (30 each - lower risk,
   since neither has an iterative live-search tool, but bounded as
   defense-in-depth).

camb_context.yaml (upstream, not fork-added) is deliberately left
untouched - only the fork's own three agents get an explicit cap here.

CAVEAT, worth reading before trusting this as fully closed: these values
are reasoned engineering judgment (comfortably above demonstrated
legitimate need), not measured optima from a turn-by-turn trace of the
actual runaway conversation. Watch the next run's cost_report_step_*.json
files for two things: (a) that inspirehep_context's prompt-token count
drops to a sane order of magnitude, and (b) that no agent's output looks
truncated/cut off mid-task, which would mean a cap is too tight and needs
raising.

Run once from the repo root:
    python patch_agent_turn_caps.py
"""

path_base_agent = "cmbagent/base_agent.py"
marker_base_agent = "hep-theory fork: bound runaway tool-call loops"

with open(path_base_agent, "r") as f:
    content = f.read()

if marker_base_agent in content:
    print(f"Already patched: {path_base_agent}")
else:
    old_else = '        else:\n            self.agent = CmbAgentSwarmAgent(\n                name=self.name,\n                # system_message=self.info["instructions"],\n                update_agent_state_before_reply=[UpdateSystemMessage(self.info["instructions"]),],\n                description=self.info.get("description", f"Agent {self.name}"),\n                llm_config=self.llm_config,\n            cmbagent_debug=cmbagent_debug,\n            functions=functions,\n            )'
    new_else = '        else:\n            self.agent = CmbAgentSwarmAgent(\n                name=self.name,\n                # system_message=self.info["instructions"],\n                update_agent_state_before_reply=[UpdateSystemMessage(self.info["instructions"]),],\n                description=self.info.get("description", f"Agent {self.name}"),\n                llm_config=self.llm_config,\n                # hep-theory fork: bound runaway tool-call loops for\n                # yaml-driven assistant agents (inspirehep_context and\n                # similar) - previously unset here (only set_code_agent\n                # passed this through), so an agent with a live search\n                # tool and no explicit yaml cap could auto-reply to\n                # itself indefinitely, resending the full accumulated\n                # conversation as the prompt on every turn. .get()\n                # default of None preserves exactly the old (unbounded)\n                # behavior for every agent whose yaml doesn\'t set this key.\n                max_consecutive_auto_reply=self.info.get("max_consecutive_auto_reply"),\n            cmbagent_debug=cmbagent_debug,\n            functions=functions,\n            )'

    if old_else not in content:
        raise SystemExit(
            "Could not find the expected set_assistant_agent default branch "
            "in " + path_base_agent + " - the file may have changed since "
            "this patch was written. Aborting without modifying anything."
        )

    content = content.replace(old_else, new_else)
    with open(path_base_agent, "w") as f:
        f.write(content)
    print(f"Patched: {path_base_agent}")


yaml_caps = {
    "cmbagent/agents/inspirehep_context/inspirehep_context.yaml": (
        'name: "inspirehep_context"', 40
    ),
    "cmbagent/agents/cadabra_context/cadabra_context.yaml": (
        'name: "cadabra_context"', 30
    ),
    "cmbagent/agents/derivation_checker/derivation_checker.yaml": (
        'name: "derivation_checker"', 30
    ),
}

for yaml_path, (name_line, cap) in yaml_caps.items():
    with open(yaml_path, "r") as f:
        yaml_content = f.read()

    if "max_consecutive_auto_reply:" in yaml_content:
        print(f"Already patched: {yaml_path}")
        continue

    if name_line not in yaml_content:
        raise SystemExit(
            f"Could not find {name_line!r} in {yaml_path} - the file may "
            "have changed since this patch was written. Aborting without "
            "modifying this file."
        )

    yaml_content = yaml_content.replace(
        name_line,
        name_line + f"\nmax_consecutive_auto_reply: {cap}",
        1,
    )
    with open(yaml_path, "w") as f:
        f.write(yaml_content)
    print(f"Patched: {yaml_path} (cap={cap})")
