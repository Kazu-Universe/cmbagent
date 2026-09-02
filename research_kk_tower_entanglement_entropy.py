"""
New research direction, grounded in Kazu's actual work: does the black-hole
entanglement entropy log-coefficient, summed over a Kaluza-Klein tower from
a compactified extra dimension, converge - and if not, what does this imply
about the validity of the 4D effective field theory at/above the KK scale?

PHYSICS SETUP: a 5D free scalar on M4 x S^1 (S^1 of radius R), KK-reduced to
an infinite tower of 4D scalars phi_n(x) with masses m_n^2 = n^2/R^2,
n in Z, propagating on the SAME Euclidean Schwarzschild background used in
the already-completed replica-trick derivation (see
reports/replica_trick_derivation.md). The compact direction is transverse
to the horizon/entangling surface - the replica construction only ever
touches the 4D external spacetime; the KK label n enters only through each
mode's mass.

THE PUZZLE THIS TASK EXISTS TO INVESTIGATE: the completed derivation
established (Gap 1, independently verified) that on Ricci-flat Schwarzschild
(R-bar=0, R-bar_ab=0), EVERY xi- and m^2-dependent term in the corrected
general a_2 heat-kernel coefficient vanishes IDENTICALLY, for ANY mass and
coupling - leaving only the mass/coupling-independent (1/180)(Riem^2-Ric^2)
term as the sole source of the -1/90 log-coefficient. This means, naively,
EVERY KK mode contributes the IDENTICAL S1^(n) = -(1/90)log(A/eps^2)
regardless of n - so summing over the infinite tower gives a divergent
total (a sum of infinitely many identical nonzero terms).

This is not necessarily a dead end - KK sums of this exact shape are
regularized all the time (Casimir-energy-style zeta-function/Epstein-zeta
regularization of "sum over n of 1"). The genuinely open questions this
task should investigate honestly, not force a predetermined answer to:
  (a) What does zeta-function regularization actually give for this sum?
  (b) Does that regularized value connect to anything physically sensible,
      or established in the literature on KK towers / Casimir energies /
      entanglement entropy with compact extra dimensions?
  (c) Does the DIVERGENCE ITSELF (before any regularization) signal
      something real - e.g. that naive mode-by-mode summation of a_2
      coefficients is not the physically correct procedure for a
      genuinely compactified theory, and that the 4D effective field
      theory description of entanglement entropy breaks down at or above
      the KK scale (m ~ 1/R), connecting to species-scale / Swampland
      distance conjecture considerations about towers of light states
      lowering the quantum gravity cutoff?

Run from the repo root, with .venv activated:
    python research_kk_tower_entanglement_entropy.py
"""

import datetime
from cmbagent.workflows.deep_research import deep_research
from cmbagent.utils.utils import get_api_keys_from_env

timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H%M")
work_dir = f"output/{timestamp}_kk_tower_entanglement_entropy"

task = (
    "CONTEXT (verified prior result, treat as a checked starting point): for "
    "a free scalar field in D=4 on Euclidean Schwarzschild, via the replica "
    "trick with Fursaev-Solodukhin curvature-splitting + Seeley-DeWitt a_2, "
    "the corrected general heat-kernel coefficient is\n\n"
    "a_2 = (4*pi)^-2 * Integral d^4x sqrt(g) [ (1/180)(Riem^2 - Ric^2) "
    "+ (1/2)(xi-1/6)^2 R^2 + (xi-1/6) m^2 R + (1/2) m^4 "
    "+ (1/30 - xi/6) Box(R) ]\n\n"
    "On Ricci-flat Schwarzschild (R-bar=0, R-bar_ab=0), EVERY xi- and "
    "m^2-dependent term vanishes IDENTICALLY for any mass and coupling - "
    "independently verified, not asserted - leaving only the "
    "mass/coupling-independent (1/180)(Riem^2-Ric^2) term as the sole "
    "source of S1 = -(1/90) log(A/epsilon^2).\n\n"
    "NEW TASK: consider a 5D free scalar field on M4 x S^1 (S^1 of radius "
    "R), KK-reduced to an infinite tower of 4D scalars phi_n(x) with masses "
    "m_n^2 = n^2/R^2 for n in Z, each propagating on the SAME Euclidean "
    "Schwarzschild background as an ordinary 4D scalar of that mass. The "
    "compact S^1 direction is transverse to the horizon/entangling surface "
    "- the replica construction only touches the 4D external spacetime; "
    "the KK index n enters only through each mode's mass, and the "
    "compact direction is summed over as an internal label after the "
    "individual-mode entropy is computed, not woven into the conical "
    "geometry itself.\n\n"
    "Investigate the following honestly, as a genuine open exploration - "
    "do not force a predetermined conclusion either way:\n\n"
    "(1) LITERATURE FIRST: search for existing work on entanglement "
    "entropy / logarithmic corrections to black hole entropy with "
    "Kaluza-Klein towers or compact extra dimensions - e.g. terms like "
    "'entanglement entropy Kaluza-Klein tower', 'logarithmic corrections "
    "black hole entropy compact extra dimensions', 'higher-dimensional "
    "heat kernel entanglement entropy compactification', 'Casimir energy "
    "Kaluza-Klein zeta function regularization'. Establish what is already "
    "known before re-deriving anything, and report explicitly whether this "
    "specific question (does the KK-mode-summed log-coefficient diverge, "
    "and what regularizes it) has already been addressed in the "
    "literature.\n\n"
    "(2) Since each mode contributes an IDENTICAL -(1/90)log(A/epsilon^2) "
    "regardless of n (per the verified Ricci-flat vanishing above), the "
    "naive sum over the full tower Sum_{n=-infinity}^{infinity} "
    "[-(1/90)log(A/epsilon^2)] is a sum of infinitely many identical "
    "nonzero terms - state explicitly whether this is divergent as "
    "literally written (it is, by direct inspection - do not hedge on "
    "this part), then apply the standard KK zeta-function/Epstein-zeta "
    "regularization to Sum_{n=-infinity}^{infinity} 1 and report the "
    "actual regularized numerical/symbolic result. Show this computation "
    "explicitly (e.g. via real Cadabra2/sympy/wolframscript execution, not "
    "assertion), do not just cite that such regularization exists.\n\n"
    "(3) Assess honestly whether the regularized value from (2) has any "
    "clear physical interpretation, connects to anything found in (1), or "
    "whether the divergence itself (prior to regularization) is more "
    "physically meaningful than any particular regularized value - i.e. "
    "whether it signals that naive mode-by-mode summation of a_2 "
    "coefficients is not the physically correct procedure for a "
    "genuinely compactified theory, and that the 4D effective description "
    "of this entanglement entropy calculation breaks down at or above the "
    "KK scale m ~ 1/R. If this connects to species-scale / Swampland "
    "distance conjecture considerations (a tower of light states lowering "
    "the quantum gravity cutoff), say so explicitly and cite the relevant "
    "literature from step (1) - but do not force this connection if the "
    "actual computation doesn't support it.\n\n"
    "(4) Produce a clear final statement of what was actually established "
    "versus what remains genuinely open - this is real research into a "
    "question without a known-in-advance answer, not a derivation with a "
    "target result to hit, so an honest 'this is unresolved and here is "
    "specifically why' is an acceptable and valuable outcome, not a "
    "failure."
)

results = deep_research(
    task,
    max_rounds_planning=30,
    max_rounds_control=80,
    max_plan_steps=4,
    n_plan_reviews=1,
    plan_instructions=(
        "Structure as up to four steps. Step 1 must be inspirehep_context "
        "performing the literature search described in task item (1), "
        "using live queries. Subsequent step(s) should have cadabra_context "
        "specify the zeta-regularization approach and engineer execute the "
        "actual regularized computation (task item 2) with real printed "
        "output (sympy and/or wolframscript, whichever is more natural for "
        "an Epstein/Hurwitz-zeta-type sum - cadabra_context should decide "
        "and justify which). A final step should have derivation_checker "
        "review whether the computation is genuine (not asserted), whether "
        "the literature claims from step 1 are accurately represented, and "
        "whether the final honest-assessment statement (task item 4) "
        "avoids overclaiming a physical interpretation the computation "
        "doesn't actually support. Do not assign derivation_checker to "
        "originate any derivation itself."
    ),
    work_dir=work_dir,
    api_keys=get_api_keys_from_env(),
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
