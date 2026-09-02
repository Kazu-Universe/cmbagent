"""
Direction (iii) from the KK-tower follow-up discussion: relate the
Schwarzschild_4 x S^1 black-string results (run (i), fully completed and
independently checked) to species-scale / Swampland distance-conjecture
reasoning, specifically the moduli-dependent species scale extracted by
van de Heisteeg, Vafa, and Wiesner (vdHVW) from higher-curvature
corrections.

CONTEXT (why this task is framed the way it is, not the way it was
originally proposed before run (i) existed): the original framing imagined
identifying eps ~ 1/Lambda_s(moduli) inside a surviving log(A/eps^2) term.
Run (i) then established, via a real direct 5D calculation (not
assumption), that NO log(eps) term survives in 5D at all (H1) - so that
original framing doesn't apply. What actually survives is two distinct
things, addressed as two separate sub-questions below:
  (A) a crossover log -(1/90)*log(A/R^2) (H2) that is ALREADY
      moduli(R)-dependent on its own, no species-scale substitution
      needed;
  (B) a power divergence c1*(R/eps), c1 = 2*sqrt(pi) (H3), where the
      species-scale identification eps ~ 1/Lambda_s(R) genuinely applies,
      turning this into c1*R*Lambda_s(R).

LESSON CARRIED FORWARD FROM RUN (ii): that run's chosen validation target
(BGMS) turned out, on derivation_checker's own honest review, not to
literally test the technique it was meant to validate - it took real
effort to discover and only got fully resolved by finding a second paper.
This task is scoped to avoid repeating that mistake: it does NOT assume
our toy S^1 compactification is directly, numerically comparable to
vdHVW's actual examples (which use genuine string-theoretic moduli
spaces, not a flat compactification radius). Step 1 must assess this
honestly before any comparison is attempted, and the task explicitly
allows for a structural/parametric comparison (same qualitative
divergence behavior, same scaling exponents) as a legitimate, honestly-
labeled outcome distinct from a literal numerical match.

Run from the repo root, with .venv activated:
    python research_species_scale_moduli_dependence.py
"""

import datetime
from cmbagent.workflows.deep_research import deep_research
from cmbagent.utils.utils import get_api_keys_from_env

timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H%M")
work_dir = f"output/{timestamp}_species_scale_moduli_dependence"

task = (
    "CONTEXT (verified prior results from a completed, independently "
    "checked run - treat as checked starting points, do not re-derive):\n\n"
    "(A) On (Euclidean Schwarzschild_4) x S^1 (S^1 of radius R, "
    "transverse to the horizon), a direct 5D conical-singularity "
    "calculation established: H1, no log(eps) divergence survives in the "
    "5D UV/small-t sector at all; H2, the surviving finite crossover term "
    "is exactly -(1/90)*log(A/R^2), matching a single-mode 4D log with R "
    "as the UV matching scale (A = 4*pi*r_h^2, the 4D horizon area); H3, "
    "two power divergences DO survive: "
    "S ~ [A*R/(6*sqrt(pi))]/eps^3 + [-sqrt(pi)*R/45]/eps + "
    "(-(1/90))*log(A/R^2) + O(eps^0 finite remainder), with the eps^-1 "
    "coefficient independently confirmed (two ways: direct 5D calculation, "
    "and a separate Gamma-function-tower-sum reconciliation matching to "
    "1e-16 precision) as c1*(R/eps) with c1 = 2*sqrt(pi).\n\n"
    "NEW TASK, two sub-questions, addressed independently and not forced "
    "to relate to each other unless the computation genuinely supports "
    "it:\n\n"
    "PART 1 - LITERATURE FIRST, before any computation: locate the "
    "van de Heisteeg-Vafa-Wiesner (vdHVW) species-scale program precisely "
    "(search INSPIRE for e.g. 'species scale higher curvature corrections', "
    "'sharpening species scale', 'higher derivative corrections quantum "
    "gravity cutoff', author-anchored searches for van de Heisteeg, Vafa, "
    "Wiesner and follow-ups). For their ACTUAL worked examples, extract: "
    "(a) exactly which moduli space(s) and compactifications they use "
    "(these are expected to be genuine string-theoretic moduli, not a "
    "single flat compactification radius - confirm or refute this "
    "expectation against the real papers), (b) the precise functional "
    "form and scaling behavior of Lambda_s(moduli) they derive or extract "
    "- symbolic form, asymptotic scaling exponents in relevant limits, "
    "and how it is obtained (via higher-curvature/higher-derivative "
    "corrections, as the task's framing above assumes - confirm this "
    "against the real method, don't assume it), (c) an explicit, honest "
    "assessment of whether ANY of their examples is structurally close "
    "enough to a simple single-circle Kaluza-Klein compactification "
    "(5D on M4 x S^1, the setup in run (i)) for a literal, apples-to-"
    "apples numerical comparison, or whether only a structural/parametric "
    "comparison (same qualitative divergence behavior and scaling "
    "exponents, not matching numerical coefficients) is honestly "
    "supportable. Do not force a literal-comparison framing if the "
    "literature search doesn't support one - a clearly-justified "
    "structural-only comparison is an acceptable and valuable outcome, "
    "the same way run (ii) ultimately needed to scope down its own "
    "claim.\n\n"
    "PART 2A - the crossover log's own R-dependence (uses H2 only, "
    "already established, do not re-derive): analyze -(1/90)*log(A/R^2) "
    "as a function of R at fixed horizon area A. State explicitly: (a) "
    "its behavior as R -> infinity (the decompactification/infinite-"
    "distance limit) and as R -> 0; (b) whether this divergence structure "
    "is qualitatively consistent with distance-conjecture-type behavior "
    "(a quantity growing without bound in an infinite-distance limit), "
    "citing the actual Swampland distance conjecture literature for what "
    "'consistent with' should mean precisely, not an impressionistic "
    "claim; (c) whether the literature located in Part 1 discusses any "
    "directly analogous log-divergent quantity as a function of a "
    "modulus, and if so, how it compares.\n\n"
    "PART 2B - the power-divergence term under a species-scale cutoff "
    "(uses H3 only, already established, do not re-derive): using the "
    "simple EFT identification Lambda_s(R) ~ (M_pl^2/R)^(1/3) "
    "(from imposing self-consistency N ~ Lambda_s*R with "
    "Lambda_s = M_pl/sqrt(N) on the KK tower of run (i)'s setup - derive "
    "this explicitly with shown algebra, do not just assert it), and "
    "identifying eps ~ 1/Lambda_s(R) in the eps^-1 term from (A) above: "
    "(a) compute the resulting entropy-correction term c1*R*Lambda_s(R) "
    "explicitly as a function of R, with c1 = 2*sqrt(pi) from the "
    "verified prior result; (b) determine its scaling exponent in R "
    "(e.g., R^(2/3) or similar - show the algebra); (c) compare this "
    "scaling behavior against vdHVW's actual Lambda_s(moduli) scaling "
    "found in Part 1 - either a literal comparison if Part 1 found a "
    "structurally analogous case, or an explicit structural/parametric "
    "comparison (do the scaling exponents/qualitative behaviors align) "
    "if not, following Part 1's own honest assessment; (d) report any "
    "genuine agreement or disagreement without forcing a conclusion "
    "either way.\n\n"
    "PART 3 - final honest assessment: state clearly and separately for "
    "2A and 2B what was established (structural or literal comparison, "
    "confirmed alignment or not) versus what remains open, and whether "
    "the two sub-questions (2A, 2B) turn out to be related to each other "
    "or should be treated as genuinely independent observations about "
    "the same underlying setup - report the actual finding, don't assume "
    "a relationship exists."
)

results = deep_research(
    task,
    max_rounds_planning=30,
    max_rounds_control=90,
    max_plan_steps=5,
    n_plan_reviews=1,
    plan_instructions=(
        "Structure as up to five steps. Step 1 must be inspirehep_context "
        "performing the exhaustive literature search of task Part 1, with "
        "live queries, explicit query/hit-count logs, and an explicit, "
        "honestly-justified assessment of whether a literal or only a "
        "structural comparison is supportable - this determination must "
        "be made BEFORE any computation in later steps, and later steps "
        "must respect it rather than silently attempting a literal match "
        "regardless. Step 2 must be cadabra_context specifying the exact "
        "algebra needed for both Part 2A and Part 2B precisely enough for "
        "direct implementation, including explicit derivation of "
        "Lambda_s(R) ~ (M_pl^2/R)^(1/3) from the stated self-consistency "
        "condition. Step 3 must be engineer executing Part 2A and 2B with "
        "real printed sympy output for every algebraic step (derivation "
        "of Lambda_s(R), the resulting c1*R*Lambda_s(R) term, its scaling "
        "exponent, and the comparison against Part 1's target from either "
        "a literal or structural framing as Step 1 determined). Step 4 "
        "must be researcher assembling Part 3's final honest assessment, "
        "explicitly flagging which comparisons are literal vs structural "
        "and stating plainly if 2A and 2B turn out unrelated. The final "
        "step must be derivation_checker verifying: that Step 1's "
        "literal-vs-structural determination is genuinely evidence-based, "
        "not assumed; that every algebraic step in Part 2A/2B is shown, "
        "not asserted (this includes checking the Lambda_s(R) derivation "
        "and the resulting scaling exponent by hand); that Step 3 respects "
        "Step 1's literal-vs-structural framing rather than overclaiming a "
        "numerical match where only a structural comparison was "
        "justified; and that Part 3's final statement does not force a "
        "relationship between 2A and 2B that the computation doesn't "
        "actually support. Do not assign derivation_checker to originate "
        "any derivation itself."
    ),
    work_dir=work_dir,
    api_keys=get_api_keys_from_env(),
    default_llm_model="claude-sonnet-5",
    default_formatter_model="claude-haiku-4-5-20251001",
    planner_model="claude-fable-5",
    plan_reviewer_model="claude-sonnet-5",
    engineer_model="claude-sonnet-5",
    researcher_model="claude-haiku-4-5-20251001",
    idea_maker_model="claude-fable-5",
    idea_hater_model="claude-fable-5",
    camb_context_model="claude-sonnet-5",
    inspirehep_context_model="claude-haiku-4-5-20251001",
    cadabra_context_model="claude-sonnet-5",
    derivation_checker_model="claude-sonnet-5",
)

print("\n\n=== DONE ===")
print("work_dir:", work_dir)
print("Watch stdout above for any '[STEP-SAVE-DEBUG]' lines - if the")
print("save-mechanism bug recurs even with the fork's fixes in place,")
print("that's important new signal.")
print("Run extract_report.py against this work_dir to get a readable compiled report:")
print(f"    python extract_report.py {work_dir}")
