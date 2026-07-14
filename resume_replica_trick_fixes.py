"""
Resume run_replica_trick_fixes.py from step 2, reusing step 1's genuinely
good output rather than re-running (and re-paying for) it.

WHY: the original run's steps 2, 3, and 4 all silently failed - every one
of them hit a real, now-fixed bug in record_status_starter (it computed a
local current_status = "in progress" but never wrote it back into
context_variables before checking the OLD value inherited from the
previous step, which is always "completed" after a normal step ends; the
check then always failed, agent_to_transfer_to stayed None, and
AgentTarget(None) crashed). This burned the full max_rounds_control budget
on nothing but that error, for steps 2, 3, and 4 alike, producing zero
actual content from engineer, inspirehep_context, or derivation_checker.

Step 1 (cadabra_context) was unaffected, since step 1 uses initial_agent=
"controller" directly rather than "control_starter"/record_status_starter,
and its output is genuinely substantive (closes gaps 1 and 2 analytically
with real, shown derivations) - see
output/2026-07-11_1627_replica_trick_fixes/report/compiled_report.md.

This script uses deep_research()'s restart_at_step parameter to skip
re-planning and skip re-running step 1, loading step 1's pickled context
directly and continuing from step 2 onward - now that the underlying bug
is fixed.

Run from the repo root, with .venv activated (make sure the fixed
cmbagent/functions/status.py is in place first):
    python resume_replica_trick_fixes.py
"""

from cmbagent.workflows.deep_research import deep_research
from cmbagent.utils.utils import get_api_keys_from_env

# Must exactly match the original run's work_dir, so restart_at_step can
# find planning/final_plan.json and context/context_step_1.pkl.
work_dir = "output/2026-07-11_1627_replica_trick_fixes"

# Task text is only used by the (skipped) planning phase when
# restart_at_step > 0, but deep_research() still requires the `task`
# argument to be passed - kept identical to the original run for
# consistency/logging, even though it won't be re-planned.
task = (
    "CONTEXT (verified prior result, treat as a checked starting point, not "
    "something to re-derive from zero): for a free scalar field in D=4 on a "
    "Euclidean Schwarzschild background, via the replica trick with conical "
    "deficit 2*pi*(1-1/n) at the horizon and the Fursaev-Solodukhin "
    "curvature-splitting + Seeley-DeWitt a_2 heat-kernel coefficient, the "
    "leading logarithmic-in-area entropy correction was previously derived "
    "as S1 = -(1/90) log(A/epsilon^2), matching the accepted pre-2020 "
    "literature value (Solodukhin arXiv:1104.3712; Sen arXiv:1108.0411), for "
    "both minimal (xi=0) and conformal (xi=1/6) coupling. Conventions: "
    "Euclidean (++++) signature, Wald/MTW Riemann sign (R>0 for spheres), "
    "operator Delta = -Box + xi*R + m^2 (Vassilevich convention, "
    "E = -xi*R - m^2), natural units G=c=hbar=1, deficit parameter "
    "alpha = 1/n.\n\n"
    "TASK: close the following four specific, previously identified gaps in "
    "that derivation. Do not simply re-assert the -1/90 result - each item "
    "below requires either an actual corrected computation or an actual "
    "shown derivation, not a restated conclusion.\n\n"
    "(1) SIGN CORRECTION: re-derive the full a_2 coefficient term-by-term "
    "from the standard Vassilevich expansion for the given Delta and E. "
    "Confirm explicitly whether the m^2*R cross-term coefficient is "
    "+(xi-1/6)*m^2*R or -(xi-1/6)*m^2*R, and whether the Box-R coefficient "
    "is (1/30 - xi/6) or -(1/5)*(xi-1/6). Show the correction is immaterial "
    "for the Ricci-flat Schwarzschild case specifically (R-bar=0), and then "
    "give the CORRECTED general a_2 formula that would be needed to extend "
    "this derivation to a non-Ricci-flat background (state explicitly that "
    "actually carrying out the RN or dS extension is out of scope for this "
    "task - only the corrected general formula is required).\n\n"
    "(2) AREA REDUCTION, ACTUALLY DERIVED: show, step by step, why "
    "Integral_Sigma R-bar_{inin} dSigma reduces to Area(Sigma) in this "
    "conical-deficit setup, and explicitly demonstrate that the "
    "O((1-alpha)^2) terms in the Riemann^2 conical-curvature expansion do "
    "not contaminate the O(1-alpha) (linear) piece that S1 is extracted "
    "from. If this genuinely requires Fursaev's dimensional-continuation "
    "(D -> D+2*epsilon) technique to do rigorously, use it and show the "
    "steps; do not merely cite that such a technique exists.\n\n"
    "(3) LITERATURE, RE-SEARCHED: perform a fresh, ideally live-queried "
    "(not memory-based) search for any 2020 or later paper that newly "
    "establishes universality of the log-area entropy coefficient across "
    "different matter content (scalar, fermion, vector, higher-spin). "
    "Explicitly evaluate whether such a paper exists; do not cite "
    "Iliesiu-Turiaci (arXiv:2003.02860) as resolving this, since it "
    "originates from the Schwarzian near-extremal zero-mode sector, not "
    "matter heat-kernel universality. If no such paper is found, state that "
    "plainly rather than substituting a partially-relevant citation.\n\n"
    "(4) SCOPE, KEPT SEPARATE: in the final synthesis, explicitly and "
    "separately state (a) that the derived coupling-independence "
    "(xi=0 and xi=1/6 both giving -1/90) is a property of this specific "
    "Ricci-flat Schwarzschild background, not a general coupling-"
    "independence theorem, and (b) whatever the outcome of (3) is regarding "
    "cross-matter-content universality. Do not conflate these two distinct "
    "senses of 'universal.'"
)

results = deep_research(
    task,
    max_rounds_planning=50,
    max_rounds_control=100,
    max_plan_steps=4,
    n_plan_reviews=1,
    plan_instructions="",  # unused when restart_at_step > 0 - planning is skipped entirely
    work_dir=work_dir,
    api_keys=get_api_keys_from_env(),
    restart_at_step=2,   # skip re-planning and skip re-running step 1;
                         # loads context/context_step_1.pkl and continues
    default_llm_model="claude-sonnet-5",
    default_formatter_model="claude-haiku-4-5-20251001",
    planner_model="claude-fable-5",
    plan_reviewer_model="claude-sonnet-5",
    engineer_model="claude-sonnet-5",
    researcher_model="claude-sonnet-5",
    idea_maker_model="claude-fable-5",
    idea_hater_model="claude-fable-5",
    camb_context_model="claude-sonnet-5",
    inspirehep_context_model="claude-sonnet-5",
    cadabra_context_model="claude-sonnet-5",
    derivation_checker_model="claude-sonnet-5",
)

print("\n\n=== DONE ===")
print("work_dir:", work_dir)
print("Run extract_report.py against this work_dir to get a readable compiled report:")
print(f"    python extract_report.py {work_dir}")
