"""
Example driver for the hep-theory extension of cmbagent.

Run after:
  pip install -e ".[hep-theory]"   # from your cmbagent fork root
  export ANTHROPIC_API_KEY=...

This sketch assumes you've added the three new agent folders under
cmbagent/agents/ (inspirehep_context, cadabra_context, derivation_checker),
registered them in cmbagent's internal agent_classes discovery (it auto-discovers
folders under agents/ the same way camb_context etc. are discovered — check
cmbagent.py's init_agents() for the exact glob if it doesn't pick them up
automatically), and added 'inspirehep' and 'cadabra' style rag/context wiring
to hand_offs.py so the planner knows when to route to them.
"""

from cmbagent import CMBAgent

# Model assignment rationale:
# - idea_maker / idea_hater / planner: exploratory, long-context synthesis across
#   disparate literature -> Fable 5.
# - engineer: multi-step iterative coding (symbolic algebra, retries on errors) ->
#   claude-sonnet-5. If you wire Claude Code in as the actual execution backend
#   (see note below), this entry mostly governs the *reasoning/explanation* text
#   the engineer agent produces alongside the code it hands off.
# - derivation_checker: needs to be skeptical and consistent, not creative ->
#   claude-sonnet-5 rather than Fable 5, to keep critique grounded rather than
#   exploratory.
# - formatters: cheap, mechanical reformatting -> claude-haiku-4-5-20251001.

agent_llm_configs = {
    "planner":            {"model": "claude-fable-5"},
    "idea_maker":         {"model": "claude-fable-5"},
    "idea_hater":         {"model": "claude-fable-5"},
    "inspirehep_context": {"model": "claude-fable-5"},
    "cadabra_context":    {"model": "claude-sonnet-5"},
    "engineer":           {"model": "claude-sonnet-5"},
    "derivation_checker": {"model": "claude-sonnet-5"},
    "planner_response_formatter":  {"model": "claude-haiku-4-5-20251001"},
    "engineer_response_formatter": {"model": "claude-haiku-4-5-20251001"},
}

cmbagent = CMBAgent(
    agent_list=[
        "engineer",
        "planner",
        "idea_maker",
        "idea_hater",
        "inspirehep_context",
        "cadabra_context",
        "derivation_checker",
    ],
    agent_llm_configs=agent_llm_configs,
)

# Benchmark task with a known ground-truth answer, so you can actually judge whether
# the pipeline is doing correct physics rather than producing plausible-sounding text.
# Start here rather than an open-ended "make progress on the information paradox" task.
task = (
    "Derive the Page curve for an evaporating Schwarzschild black hole under the "
    "assumption of information-preserving unitary evaporation, following the original "
    "counting argument (Page 1993). State the assumptions explicitly, derive the "
    "entanglement entropy as a function of radiated fraction, and identify the Page "
    "time. Check the result against the known closed-form expression in the literature."
)

results = cmbagent.solve(task)
