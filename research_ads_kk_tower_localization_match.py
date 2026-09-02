"""
Direction (ii) from the KK-tower follow-up discussion: reproduce ONE
existing, literature-established zeta-regularized KK-tower log(N)
coefficient in a supersymmetric AdS_d x S^k compactification, and match it
against the corresponding supersymmetric-localization result on the dual
CFT side. This is a VALIDATION run, not new physics - the goal is to
confirm that this pipeline's zeta/Epstein-regularization machinery
(exercised on a real but open question in run (i), Schwarzschild x S^1)
reproduces a KNOWN answer when pointed at a case with an independent,
published target.

WHY THIS MATTERS FOR THE STANDING OPEN QUESTION: run (i) established that
naive 4D KK-mode-sum regularization schemes (zeta vs hard-cutoff) disagree
with each other and, per run (i)'s own direct 5D calculation, the
zeta-regularized answer does NOT cleanly correspond to any single term of
the true finite-answer. This run tests the SAME regularization machinery
(tower-summed, zeta-regularized log coefficient of a one-loop
determinant/entropy) against a case where segment of the AdS/CFT
literature - Bhattacharyya, Grassi, Marino, Sen and follow-ups - already
computed the answer TWO independent ways (bulk one-loop zeta-function sum
over the KK tower, and boundary SUSY localization) and found agreement.
If this pipeline reproduces that agreement, the regularization stack
itself is validated on a case with ground truth; if it does not, that is
equally important to know before trusting scheme choices in run (i) or
future runs.

Run from the repo root, with .venv activated:
    python research_ads_kk_tower_localization_match.py
"""

import datetime
from cmbagent.workflows.deep_research import deep_research
from cmbagent.utils.utils import get_api_keys_from_env

timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H%M")
work_dir = f"output/{timestamp}_ads_kk_tower_localization_match"

task = (
    "CONTEXT (from a separate, completed prior run - background only, not "
    "to be re-derived or assumed to constrain this run's target choice): "
    "a direct 5D conical-singularity calculation on Schwarzschild_4 x S^1 "
    "confirmed that a naive zeta-regularized sum over an infinite KK tower "
    "of a per-mode log-coefficient does NOT cleanly correspond to any "
    "single term of the true, finite-cutoff answer for that specific "
    "non-supersymmetric, non-AdS setup. This run is a DELIBERATELY "
    "DIFFERENT, independent test of zeta-regularized KK-tower summation: "
    "a case where the literature has an established, cross-checked "
    "target answer, to validate the general regularization technique "
    "(not to extend or reinterpret the prior result).\n\n"
    "NEW TASK: identify and reproduce ONE existing, published match "
    "between (a) a zeta-function-regularized sum over a KK tower's "
    "one-loop contribution to a bulk AdS_d x S^k partition function or "
    "free energy - specifically the coefficient of log(N) (N being the "
    "rank/flux parameter on the dual CFT side) - and (b) the "
    "corresponding coefficient computed independently via "
    "supersymmetric localization on the dual CFT (e.g. the S^3 or S^4 "
    "partition function, an ABJM-type theory, or another compactification "
    "with a clean published match). Do NOT assume in advance which "
    "specific compactification (AdS4 x S7 / ABJM, AdS5 x S5, AdS7 x S4, "
    "or another) has the cleanest, most citable match - this must be "
    "determined by the literature search below, not assumed from general "
    "recollection.\n\n"
    "(1) LITERATURE FIRST, EXHAUSTIVE ON THIS POINT: search INSPIRE for "
    "the log(N) one-loop correction / KK-tower zeta-regularization "
    "literature in AdS_d x S^k compactifications and its comparison "
    "against supersymmetric localization - e.g. terms like 'log N "
    "correction AdS4 CFT3 localization', 'one-loop free energy KK tower "
    "AdS7', 'zeta function regularization AdS x sphere partition "
    "function', 'ABJM log N free energy one loop', 'M-theory one-loop "
    "test AdS4 CFT3', and author-anchored searches (Bhattacharyya, "
    "Grassi, Marino, Sen; and any 2015-present follow-ups extending the "
    "program to other compactifications). For EACH candidate match found, "
    "record: (a) which AdS_d x S^k compactification, (b) the exact "
    "published log(N) coefficient (bulk side) and how it was derived "
    "(what tower, what regularization), (c) the exact matching "
    "localization coefficient (boundary side) and which CFT/observable it "
    "came from, (d) the precision/form of the claimed agreement (exact "
    "symbolic match, numerical match to some precision, or only "
    "parametric/scaling agreement), (e) an assessment of which candidate "
    "has the SIMPLEST, most self-contained bulk-side derivation to "
    "actually reproduce computationally in this task, given this "
    "pipeline's tools (Cadabra2, sympy, mpmath - no numerical GR/other "
    "heavy machinery). Recommend ONE target compactification with clear "
    "justification before any computation begins.\n\n"
    "(2) Once a specific target is chosen and justified in (1), specify "
    "precisely the bulk-side one-loop computation to reproduce: the exact "
    "KK tower (masses/multiplicities of the relevant fields on S^k), the "
    "heat-kernel or zeta-function method used in the literature source, "
    "and the exact regularization prescription (Epstein zeta, "
    "Barnes zeta, or another) that produces the published log(N) "
    "coefficient. State this specification explicitly and completely "
    "enough for direct implementation - do not leave any regularization "
    "or normalization convention implicit.\n\n"
    "(3) Execute the actual computation with real Cadabra2/sympy/mpmath "
    "code, printed intermediate steps, reproducing the published bulk-side "
    "log(N) coefficient from the tower data and regularization "
    "prescription specified in (2). Do not simply assert agreement with "
    "the literature value - compute it and print the comparison "
    "explicitly, with a stated numerical tolerance and PASS/FAIL verdict, "
    "the same standard used in prior runs.\n\n"
    "(4) State the localization-side coefficient from the literature "
    "found in (1) as the independent target (do not attempt to "
    "re-derive supersymmetric localization itself, which is out of "
    "scope) and give the explicit final comparison: computed bulk value "
    "vs. published bulk value vs. published localization value, with "
    "every discrepancy (if any) reported honestly rather than minimized.\n\n"
    "(5) Produce a clear final statement: does this pipeline's "
    "zeta-regularization machinery reproduce the published, "
    "localization-matched answer for the chosen compactification? If "
    "yes, this validates the general technique used in the prior "
    "Schwarzschild x S^1 run even though that run's own tower sum did not "
    "map cleanly onto its true finite answer - state explicitly why a "
    "regularization technique can be validated on a SUSY/AdS case and "
    "still fail to have a clean correspondence in the prior non-SUSY, "
    "non-AdS case (e.g., holographic/SUSY cases have an independent "
    "boundary answer forcing the correct scheme, while the prior case's "
    "regularization had no such external anchor). If no clean "
    "reproduction is achieved, report exactly where the computation "
    "diverges from the published value and by how much."
)

results = deep_research(
    task,
    max_rounds_planning=30,
    max_rounds_control=100,
    max_plan_steps=5,
    n_plan_reviews=1,
    plan_instructions=(
        "Structure as up to five steps. Step 1 must be inspirehep_context "
        "performing the exhaustive literature search of task item (1), "
        "with live queries, explicit query/hit-count logs, and a clearly "
        "justified recommendation of ONE target compactification before "
        "any computation is planned or attempted. Step 2 must be "
        "cadabra_context producing the complete computational "
        "specification of task item (2), fully explicit about the tower "
        "data and regularization prescription, with no implicit "
        "conventions. Step 3 must be engineer executing task item (3) "
        "with real printed code output, including a printed comparison "
        "against the published bulk-side value with tolerance and "
        "PASS/FAIL. Step 4 must be engineer or researcher (planner's "
        "choice) executing task items (4)-(5), the localization-side "
        "comparison and final honest assessment. The final step must be "
        "derivation_checker verifying: that Step 1's chosen target is "
        "genuinely the best-justified candidate found (not an arbitrary "
        "choice); that Step 2's specification matches the literature "
        "source's actual method, not a plausible-sounding approximation "
        "of it; that Step 3's computation is genuinely executed, not "
        "asserted, and that its comparison to the literature value is "
        "reported honestly including any discrepancy; and that Step 4's "
        "explanation of why this case can validate the technique despite "
        "run (i)'s non-correspondence is logically sound and not "
        "hand-waved. Do not assign derivation_checker to originate any "
        "derivation itself."
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
print("Watch stdout above for any '[STEP-SAVE-DEBUG]' lines - if the")
print("save-mechanism bug from the 5D black-string run recurs, the debug")
print("patch will print the real exception here instead of failing silently.")
print("Run extract_report.py against this work_dir once the underlying")
print("save bug is confirmed fixed (or not) - it may still be empty:")
print(f"    python extract_report.py {work_dir}")
