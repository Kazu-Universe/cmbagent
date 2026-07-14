"""
Narrow follow-up fixing only the Gap 4 synthesis document regression from
output/2026-07-13_1723_replica_trick_gap2_gap4 (Step 2/Step 3 of that run).

WHAT HAPPENED: derivation_checker correctly caught that a re-attempt meant
to apply only a narrow Section (a.3) RN/dS fix instead silently rewrote and
stripped required content from Sections (b) and (c), while explicitly
claiming those sections were "unchanged from the previously-passed version"
- a real, confirmed instance of the exact silent-scope-narrowing failure
mode this review process exists to catch.

WHY A FRESH, NARROW RUN INSTEAD OF RESUMING: deep_research()'s
restart_at_step reruns the ORIGINAL plan.json instructions, which only say
"produce the Gap 4 synthesis document" generically - it has no mechanism to
inject the specific verbatim text this fix needs, which is exactly what
caused the regression (engineer reconstructing content "from memory"
instead of copying it exactly). This task supplies the required verbatim
text directly, so there is nothing left to reconstruct.

GROUNDING:
- Section (a.3)'s RN/dS content is unaffected and already correct - not
  reissued here, only referenced.
- Section (b) must be the Gap-3 verdict exactly as it appears in the
  original CONTEXT block (continue_replica_trick_gap2_gap4.py), quoted
  verbatim below - not paraphrased, not shortened.
- Section (c) must contain the false-premise retraction, the 8pi result,
  both confirming methods, the dimensional-analysis genericity argument,
  and Step 1's actual printed block-(f) conclusion, quoted verbatim below
  from the real sympy output (confirmed identical across two independent
  print statements in the transcript).

Run from the repo root, with .venv activated:
    python fix_gap4_synthesis_verbatim.py
"""

import datetime
from cmbagent.workflows.deep_research import deep_research
from cmbagent.utils.utils import get_api_keys_from_env

timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H%M")
work_dir = f"output/{timestamp}_gap4_synthesis_fix"

# Verbatim from continue_replica_trick_gap2_gap4.py's CONTEXT block - Section
# (b) must reproduce this exactly, not a paraphrase or summary.
gap3_verdict_verbatim = (
    "no live INSPIRE-HEP retrieval tool is available in this environment "
    "(confirmed after repeated attempted invocation). Recall-based fallback "
    "delivered: no post-2020 paper was found establishing cross-matter-"
    "content (scalar/fermion/vector/higher-spin) log-coefficient "
    "universality via heat-kernel methods; the pre-2020 picture "
    "(log-coefficients are generically spin/matter-content-dependent, Sen "
    "arXiv:1005.3044) stands unoverturned as far as could be determined. "
    "Iliesiu-Turiaci arXiv:2003.02860 was correctly excluded (Schwarzian "
    "near-extremal zero-mode sector, not matter heat-kernel universality - "
    "a structurally different question). The Wald-entropy/anomaly-"
    "coefficient sense of 'universal' was correctly flagged as a distinct "
    "notion from matter-content universality."
)

# Verbatim from the actual passed Step 1 sympy output (identical at two
# independent print points in the real transcript) - Section (c) must
# quote this exactly for the log-argument-convention conclusion.
block_f_verbatim = (
    "(f) Open-convention statement about logarithmic argument\n"
    "(f) The pairing log(A/eps_uv**2) rather than log(const/eps_uv**2) is a "
    "scheme/RG-matching\n"
    "(f) convention inherited from the Area-proportional a_0/a_1 leading "
    "term; it is NOT\n"
    "(f) independently derived from the a_2-order pure-number (8*pi) "
    "piece. This remains an\n"
    "(f) OPEN scheme-convention choice, not a first-principles "
    "derivation.\n"
    "(f) The log-divergent coefficient itself (entropy_coeff = -1/90) is a "
    "pure number, unrelated\n"
    "(f) to A, M, or eps_uv individually; only the pairing with "
    "'Area(Sigma)' inside the log\n"
    "(f) argument (as opposed to some other constant with dimensions of "
    "length^2) is a convention,\n"
    "(f) inherited from matching onto the genuinely Area-proportional "
    "leading power-divergent term."
)

task = (
    "CONTEXT: a prior review cycle correctly PASSED a Gap 4 synthesis "
    "document's Section (a) [RN/de Sitter xi-independence discussion, "
    "unaffected, not reissued here] but then a subsequent narrow-fix "
    "attempt, meant to touch ONLY Section (a.3), instead silently rewrote "
    "and stripped required content from Sections (b) and (c) while falsely "
    "claiming they were unchanged. This task reissues ONLY Sections (b) and "
    "(c), correctly this time, by supplying the exact required text "
    "directly below so nothing needs to be reconstructed from memory.\n\n"
    "TASK: produce a single, corrected Gap 4 synthesis document containing "
    "exactly these two sections (do not include Section (a) - it is "
    "unaffected and handled elsewhere):\n\n"
    "SECTION (b) - must be the following Gap-3 verdict reproduced VERBATIM, "
    "word for word, with no truncation, no paraphrase, and no added or "
    "substituted closing sentences:\n\n"
    f'"{gap3_verdict_verbatim}"\n\n'
    "SECTION (c) - must explicitly and separately contain ALL of the "
    "following, in this order, with no omissions:\n"
    "1. The false-premise retraction, stated explicitly: the original task "
    "premise 'Integral_Sigma R-bar_{inin} dSigma reduces to Area(Sigma)' is "
    "FALSE AS STATED for Schwarzschild.\n"
    "2. The corrected result: Integral_Sigma R-bar_{inin} dSigma = 8*pi "
    "exactly - an M-independent PURE NUMBER, not proportional to "
    "Area(Sigma).\n"
    "3. Both confirming methods, named explicitly: (i) direct orthonormal-"
    "frame evaluation (R-bar_{inin} = 4M/r^3 at r=2M), and (ii) the "
    "Gauss-Codazzi route via R_Sigma = 2/(2M)^2.\n"
    "4. The dimensional-analysis genericity argument: Schwarzschild has "
    "exactly one scale M, so ANY local curvature-squared surface integral "
    "evaluated at r=2M is forced by dimensional analysis to be a pure "
    "number, not an Area-scaling quantity - this is not a computational "
    "coincidence specific to R-bar_{inin}.\n"
    "5. Where the genuine Area(Sigma)/epsilon^2 dependence in the final "
    "entropy formula actually originates: a DIFFERENT, lower heat-kernel "
    "order - the trivial identity heat-kernel trace over the transverse "
    "cone (a_0/a_1 order), not the a_2-order curvature-squared term that "
    "supplies the -1/90 coefficient itself.\n"
    "6. The following block-(f) conclusion from Step 1's actual sympy "
    "output, reproduced VERBATIM (this is the real printed output, "
    "confirmed identical at two independent points in the prior "
    "transcript):\n\n"
    f'"{block_f_verbatim}"\n\n'
    "Do not add commentary questioning or re-deriving any of the above - "
    "reproduce it as specified. Do not conflate items 1-6 with each other "
    "or compress them into fewer statements than listed."
)

results = deep_research(
    task,
    max_rounds_planning=30,
    max_rounds_control=60,
    max_plan_steps=2,
    n_plan_reviews=1,
    plan_instructions=(
        "This is a narrow, fully-specified fix - the exact required text "
        "for both sections is already given verbatim in the task. Step 1 "
        "assigns engineer to produce the corrected document by reproducing "
        "the given text exactly, with minimal additional framing/"
        "formatting only. Step 2 assigns derivation_checker to verify "
        "Section (b) and Section (c) each match the task's required text "
        "verbatim (word-for-word comparison, not paraphrase-equivalence), "
        "and to explicitly flag any drift, omission, or substitution if "
        "found. Do not assign derivation_checker to originate any "
        "derivation."
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
