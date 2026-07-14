"""
Continuation of the replica-trick / heat-kernel log-area entropy correction
derivation, via deep_research() - the real multi-step research pipeline
(not the mode="default" single-call diagnostic scripts used for today's
sanity checks).

GROUNDING: this task is built directly on the verified compiled report at
output/2026-07-11_0916_derive-the-leading-order-correction-to-t/report/compiled_report.md
(re-read in full before drafting this, after an earlier mis-recollection in
conversation was caught and corrected - do not trust a paraphrase of this
task's own history without checking the actual file). That run's verdict was
PASS WITH CAVEATS, established S1 = -(1/90) log(A/eps^2) for a free scalar
on Euclidean Schwarzschild (D=4, replica trick, Fursaev-Solodukhin + Seeley-
DeWitt a_2), and flagged four concrete, still-open required fixes. This task
treats that result as a VERIFIED STARTING POINT and targets exactly those
four gaps, rather than re-deriving everything from scratch:

  1. Sign error: the standard Vassilevich a_2 expansion (Delta=-Box+xi*R+m^2,
     E=-xi*R-m^2) gives +(xi-1/6)*m^2*R for the m^2 R cross-term, not the
     -(xi-1/6)*m^2*R written in the prior derivation; the Box-R coefficient
     was also off (1/30 - xi/6 is standard, not -(1/5)(xi-1/6)). Both were
     harmless for the Ricci-flat Schwarzschild case (R-bar=0 kills both
     terms), but must be corrected before this a_2 formula is reused on any
     non-Ricci-flat background (Reissner-Nordstrom, de Sitter).
  2. The step Integral_Sigma R-bar_{inin} dSigma -> Area(Sigma), used to go
     from the symbolic Riemann^2-splitting formula to the proper-time
     integral, was ASSERTED ("standard reduction") rather than derived. This
     exact step is a documented historical trouble spot in Fursaev-
     Solodukhin-type calculations (requiring Fursaev's dimensional-
     continuation trick to handle correctly) and must actually be shown,
     including a demonstration that the O((1-alpha)^2) terms genuinely do
     not contaminate the linear-in-(1-alpha) piece used for S1.
  3. Literature: no 2020+ paper was confirmed to newly establish universality
     of the log-area coefficient across matter content (scalar vs fermion vs
     vector vs higher-spin). Iliesiu-Turiaci (arXiv:2003.02860) is
     mechanistically off-target (Schwarzian zero-mode origin, not matter
     heat-kernel universality) and must not be cited as resolving this. This
     gap should be actively re-searched (ideally via a live INSPIRE/arXiv
     query rather than recollection) rather than simply re-asserted as
     closed.
  4. The derived coupling-independence (minimal xi=0 and conformal xi=1/6
     both give -1/90) is specific to the Ricci-flat Schwarzschild background
     - it must not be conflated with, or presented as, universality across
     matter content. These are two distinct senses of "universal" and the
     final write-up must keep them explicitly separate.

Run from the repo root, with .venv activated:
    python run_replica_trick_fixes.py
"""

import datetime
from cmbagent.workflows.deep_research import deep_research
from cmbagent.utils.utils import get_api_keys_from_env

timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H%M")
work_dir = f"output/{timestamp}_replica_trick_fixes"

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
    max_plan_steps=4,   # one step per required fix is a natural shape here,
                         # though the planner may reasonably combine (1)+(2)
                         # into a single cadabra_context derivation step
                         # followed by a literature step and a review step
    n_plan_reviews=1,
    plan_instructions=(
        "This task has four explicit, independently checkable required "
        "fixes (numbered 1-4 in the task text) carried forward from a prior "
        "derivation_checker review. Structure the plan so each fix is "
        "clearly addressed by a specific step - do not let any of the four "
        "be silently absorbed into a vague 'finalize the derivation' step. "
        "Fixes (1) and (2) are computational and belong with cadabra_context "
        "(and, if actual symbolic/numeric execution is needed to show the "
        "O((1-alpha)^2) non-contamination in fix (2), the engineer agent "
        "should be used for that specific sub-step, since cadabra_context "
        "cannot execute code itself). Fix (3) is a literature task for "
        "inspirehep_context. Fix (4) is a synthesis/write-up requirement "
        "that the final step (derivation_checker) must explicitly verify "
        "was honored, not a separate computational step. Do not assign "
        "derivation_checker to originate or produce any derivation itself - "
        "its role is strictly to review what other agents produced."
    ),
    work_dir=work_dir,
    api_keys=get_api_keys_from_env(),
    # hep-theory fork bug fix: deep_research()'s own defaults for these two
    # are OpenAI models (default_llm_model='gpt-4.1-...',
    # default_formatter_model='o3-mini-...'), NOT Claude - o3-mini in
    # particular requires max_completion_tokens instead of max_tokens and
    # crashes with a BadRequestError under this codebase's current OpenAI
    # client call path. Every earlier test script in this session set these
    # explicitly to Claude models; this script originally did not, which is
    # what actually caused the crash on the first attempt - unrelated to any
    # of today's other fixes or to any previously-applied patch scripts.
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
