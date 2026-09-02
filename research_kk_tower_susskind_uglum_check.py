"""
Focused follow-up to output/2026-07-16_1726_kk_tower_entanglement_entropy
(verdict: PASS). That work found the KK-tower-summed log-area entanglement
entropy coefficient diverges naively, and that smooth regularization
schemes (Riemann/Epstein zeta, Abel/exponential-cutoff) give a
scheme-dependent value of 0 - explicitly NOT scheme-independent, since a
hard mode-number cutoff would give a different, divergent answer instead.
The literature search in that run (27 live queries) did not surface
Susskind & Uglum, "Black Hole Entropy in Canonical Quantum Gravity and
Superstring Theory" (arXiv:hep-th/9401070) - a foundational paper on
exactly this class of divergence (a sum over field species/modes near a
horizon) and its resolution via renormalization of Newton's constant.

THIS TASK: check that paper directly, then honestly assess whether/how its
mechanism bears on the KK-tower divergence already found - do not force
the connection if it doesn't actually hold up (e.g. if Susskind-Uglum's
"species" are conceptually distinct from KK modes specifically, or if
their renormalization mechanism doesn't apply to the log-coefficient the
same way it applies to the leading area-law term). This is a genuine
scientific check, not a foregone conclusion either way.

Run from the repo root, with .venv activated:
    python research_kk_tower_susskind_uglum_check.py
"""

import datetime
from cmbagent.workflows.deep_research import deep_research
from cmbagent.utils.utils import get_api_keys_from_env

timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H%M")
work_dir = f"output/{timestamp}_kk_tower_susskind_uglum_check"

task = (
    "CONTEXT (verified prior result from output/2026-07-16_1726_kk_tower_"
    "entanglement_entropy, verdict PASS - treat as established, do not "
    "redo): for a 5D free scalar KK-reduced on S^1 (radius R) to a tower "
    "of 4D modes m_n^2 = n^2/R^2 propagating on Euclidean Schwarzschild, "
    "every individual mode contributes an IDENTICAL log-area entanglement "
    "entropy coefficient -(1/90)log(A/epsilon^2), because all mass/coupling "
    "-dependent terms in the corrected a_2 heat-kernel coefficient vanish "
    "identically on Ricci-flat Schwarzschild (independently verified). "
    "Summed over the infinite tower, this diverges. Two independent smooth "
    "regularization schemes were actually computed and cross-checked: "
    "Riemann/Epstein zeta continuation and Abel/exponential-cutoff "
    "resummation, both giving a regularized coefficient of exactly 0. A "
    "third scheme, a hard mode-number cutoff Sum_{|n|<N} 1 = 2N+1, was "
    "shown to give a DIFFERENT, divergent, cutoff-dependent, non-zero "
    "answer instead - so the '0' result is explicitly SCHEME-DEPENDENT, "
    "not scheme-independent. The prior literature search (27 live INSPIRE "
    "queries) did not surface Susskind & Uglum, 'Black Hole Entropy in "
    "Canonical Quantum Gravity and Superstring Theory' (arXiv:hep-th/"
    "9401070) - a foundational paper on divergences from summing field "
    "species/modes near a black hole horizon, and their resolution via "
    "renormalization of Newton's constant (the 'species problem').\n\n"
    "TASK:\n\n"
    "(1) Retrieve Susskind & Uglum (arXiv:hep-th/9401070) via a live, "
    "targeted INSPIRE query, and establish precisely what mechanism it "
    "actually proposes: what divergence does it address, what is being "
    "summed over (matter field species specifically, or a more general "
    "class of degrees of freedom near the horizon), and how does the "
    "renormalization of Newton's constant absorb that divergence such "
    "that the total (bare gravitational + matter-entanglement) entropy "
    "remains the semiclassical Bekenstein-Hawking area law. Also check "
    "whether it addresses the LOGARITHMIC (sub-leading) term specifically, "
    "or only the leading (linearly UV-divergent, area-law-renormalizing) "
    "piece - this distinction matters and must not be glossed over, since "
    "the prior work's divergence is specifically in the LOG coefficient, "
    "not the leading area term.\n\n"
    "(2) Honestly assess whether this mechanism actually bears on the "
    "KK-tower divergence found in the prior work. Specific questions to "
    "address, not assume an answer to: (a) are Susskind-Uglum's 'species' "
    "conceptually the same kind of object as KK modes of a single field "
    "(both are towers of degrees of freedom near the horizon, but "
    "Susskind-Uglum's original motivation is typically framed around "
    "distinct matter field species, e.g. from a GUT particle content, not "
    "a single field's KK tower specifically - state plainly whether the "
    "mechanism is agnostic to this distinction or not, per what the paper "
    "actually says); (b) if the mechanism does apply, does it resolve, "
    "reframe, or leave unchanged the scheme-dependence (0 vs divergent) "
    "found in the prior work - e.g. does renormalizing G effectively pick "
    "out one of the previously-tested regularization schemes as the "
    "physically correct one, or does it operate at a different level "
    "(the leading area term) that doesn't directly interact with the "
    "log-coefficient's regularization-scheme ambiguity at all; (c) if "
    "Susskind-Uglum's mechanism specifically concerns the leading linear "
    "divergence (not the log term), state this plainly as a limitation of "
    "how directly it applies here, rather than forcing a connection to "
    "the log-coefficient result that the paper doesn't actually support.\n\n"
    "(3) Update the established-vs-open assessment from the prior work in "
    "light of this: does bringing in Susskind-Uglum move any of the "
    "previously 'GENUINELY OPEN' items into 'ESTABLISHED', partially "
    "clarify them, or leave them genuinely still open (in which case say "
    "so plainly - this is real research, and 'this reference clarifies "
    "the leading term but not the log-coefficient scheme-dependence' is a "
    "legitimate, valuable outcome, not a failure to find a full "
    "resolution).\n\n"
    "Do not re-derive or re-run the prior regularization computation - it "
    "is established context above. This task is specifically about "
    "checking the missed reference and honestly integrating (or "
    "explicitly declining to integrate) its implications."
)

results = deep_research(
    task,
    max_rounds_planning=20,
    max_rounds_control=50,
    max_plan_steps=3,
    n_plan_reviews=0,
    plan_instructions=(
        "Exactly two or three steps. Step 1: inspirehep_context retrieves "
        "and characterizes Susskind-Uglum (arXiv:hep-th/9401070) via a "
        "live targeted query, per task item (1). Step 2: cadabra_context "
        "or engineer performs the honest assessment in task items (2) and "
        "(3) - this is primarily an analytical/literature-integration "
        "task, not necessarily requiring new symbolic computation, but if "
        "engineer needs to check any specific claim numerically/"
        "symbolically (e.g. comparing the structure of Susskind-Uglum's "
        "divergence to the KK-tower sum), it should do so with real "
        "executed code, not assertion. If a third step is used, it should "
        "be derivation_checker reviewing whether the connection drawn in "
        "step 2 is honestly scoped and well-supported by what Susskind-"
        "Uglum actually says (not overclaimed), and whether the updated "
        "established-vs-open assessment is accurate. Do not assign "
        "derivation_checker to originate any analysis itself."
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
