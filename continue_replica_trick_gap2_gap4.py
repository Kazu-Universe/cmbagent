"""
Continuation of output/2026-07-11_1627_replica_trick_fixes, targeting only
the two gaps still genuinely open: Gap 2's symbolic verification and Gap 4's
standalone synthesis document.

WHY A FRESH RUN INSTEAD OF restart_at_step: restart_at_step=2 would re-run
the ORIGINAL plan's Step 2 instructions, which still assume the false
premise cadabra_context's later fix retracted (that
Integral_Sigma R-bar_{inin} dSigma reduces to Area(Sigma)). That premise is
now known to be wrong - the integral is a pure, M-independent number (8*pi
for Schwarzschild). Re-running the stale instructions would reproduce the
same mistake. Posing the remaining work as a fresh plan, quoting the
ALREADY-VERIFIED correct results as context, avoids this entirely.

WHY TWO SEPARATE STEPS FOR THE TWO FIXES: the real prior run confirmed
engineer's response was silently truncated (autogen's Anthropic wrapper
returned an empty message with no error - see patch_anthropic_truncation_
warning.py) when asked to produce BOTH the Gap-2 symbolic verification AND
the Gap-4 synthesis document in a single turn - both attempts hit exactly
max_tokens=16000. controller.yaml already warns against bundling these, but
evidently that alone wasn't reliably followed - so this plan keeps them as
two separate, smaller plan steps by construction rather than relying on
controller to split a bundled instruction correctly.

GROUNDING: the CONTEXT block below quotes the actual verified content from
Step 1 (cadabra_context, gap 1 + corrected gap 2 mechanism) and Step 3
(inspirehep_context, gap 3 literature fallback) of the prior run, both of
which derivation_checker independently reviewed and closed across two real
review cycles - these are treated as checked starting points here, not
re-derived from scratch.

Run from the repo root, with .venv activated (make sure
patch_anthropic_truncation_warning.py has been applied first):
    python continue_replica_trick_gap2_gap4.py
"""

import datetime
from cmbagent.workflows.deep_research import deep_research
from cmbagent.utils.utils import get_api_keys_from_env

timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H%M")
work_dir = f"output/{timestamp}_replica_trick_gap2_gap4"

task = (
    "CONTEXT (verified prior results from a completed review cycle - treat "
    "as checked starting points, not something to re-derive): for a free "
    "scalar field in D=4 on Euclidean Schwarzschild, via the replica trick "
    "with conical deficit and Fursaev-Solodukhin + Seeley-DeWitt a_2, the "
    "following are independently verified and CLOSED:\n\n"
    "GAP 1 (closed): the corrected general a_2 formula is\n"
    "a_2 = (4*pi)^-2 * Integral d^4x sqrt(g) [ (1/180)(Riem^2 - Ric^2) "
    "+ (1/2)(xi-1/6)^2 * R^2 + (xi-1/6) * m^2 * R + (1/2) m^4 "
    "+ (1/30 - xi/6) * Box(R) ]\n"
    "with Delta = -Box + xi*R + m^2 (Vassilevich E = -xi*R - m^2). Both "
    "disputed sign coefficients are resolved: the m^2*R cross-term is "
    "+(xi-1/6), and Box-R is (1/30 - xi/6), NOT -(1/5)(xi-1/6) (confirmed "
    "algebraically distinct, difference = xi/30). On Ricci-flat Schwarzschild "
    "(R-bar=0, R-bar_ab=0), every xi- and m^2-dependent term vanishes "
    "identically, leaving only the xi,m^2-independent (1/180)(Riem^2-Ric^2) "
    "term as the sole source of -1/90.\n\n"
    "GAP 2 MECHANISM (corrected - the original task premise was FALSE AS "
    "STATED and has been retracted): Integral_Sigma R-bar_{inin} dSigma does "
    "NOT reduce to Area(Sigma). Direct orthonormal-frame computation gives "
    "R-bar_{inin} = 4M/r^3 at the Schwarzschild horizon (r=2M), so "
    "Integral_Sigma R-bar_{inin} dSigma = 8*pi exactly - an M-independent "
    "PURE NUMBER, not proportional to Area(Sigma) (confirmed by two "
    "independent methods: direct orthonormal-frame evaluation, and the "
    "Gauss-Codazzi route via R_Sigma = 2/(2M)^2). This is generic: "
    "Schwarzschild has exactly one scale M, so ANY local curvature-squared "
    "surface integral evaluated at r=2M is forced by dimensional analysis "
    "to be a pure number, not an Area-scaling quantity. The genuine "
    "Area(Sigma)/epsilon^2 dependence in the final entropy formula instead "
    "originates at a DIFFERENT, lower heat-kernel order: the trivial "
    "identity heat-kernel trace over the transverse cone, "
    "Tr_sing^(0)(s) ~ (Area(Sigma)/(4*pi*s)) * (1/12)(1/alpha - alpha), "
    "which produces the leading Area(Sigma)/epsilon^2 divergence "
    "(Bekenstein-Hawking-type area law) at a_0/a_1 order - a lower order "
    "than the a_2-level curvature-squared correction that supplies the "
    "-1/90 coefficient itself. Pairing the a_2-order log divergence with "
    "the SAME scale Area(Sigma) (rather than some other dimensionful "
    "constant) is a scheme/RG-matching convention inherited from the "
    "genuinely Area-proportional leading term, not something independently "
    "derived from the R-bar_{inin} integral - this specific point (why "
    "Area(Sigma) rather than a different constant) was left as a still-open "
    "item in the prior review and should be addressed below.\n\n"
    "GAP 3 (closed under documented tooling limitation): no live INSPIRE-HEP "
    "retrieval tool is available in this environment (confirmed after "
    "repeated attempted invocation). Recall-based fallback delivered: no "
    "post-2020 paper was found establishing cross-matter-content (scalar/"
    "fermion/vector/higher-spin) log-coefficient universality via heat-"
    "kernel methods; the pre-2020 picture (log-coefficients are generically "
    "spin/matter-content-dependent, Sen arXiv:1005.3044) stands unoverturned "
    "as far as could be determined. Iliesiu-Turiaci arXiv:2003.02860 was "
    "correctly excluded (Schwarzian near-extremal zero-mode sector, not "
    "matter heat-kernel universality - a structurally different question). "
    "The Wald-entropy/anomaly-coefficient sense of 'universal' was correctly "
    "flagged as a distinct notion from matter-content universality.\n\n"
    "TASK: close the following two specific, still-open gaps. Do not "
    "re-derive Gap 1 or Gap 3 - they are established context above.\n\n"
    "GAP 2 - SYMBOLIC VERIFICATION (never yet executed in any prior "
    "attempt): implement in sympy, with clear printed output at every step:\n"
    "(a) Build c_1 (the linear-in-(1-alpha) coefficient feeding "
    "S1 = (alpha*d/d(alpha) - 1) log Z |_{alpha=1}) from TWO pieces: the "
    "a_0/a_1-order Tr_sing^(0)(s) ~ Area(Sigma)/(4*pi*s) term (genuinely "
    "Area-proportional), and the a_2-order pure-number curvature integral "
    "(8*pi for Schwarzschild - NOT Area-proportional, per the corrected "
    "mechanism above).\n"
    "(b) Keep the D = 4+2*epsilon dimensional-continuation combination "
    "symbolic (epsilon-dependent) BEFORE taking epsilon->0 and alpha->1 "
    "limits; print this explicit epsilon-dependent expression.\n"
    "(c) Apply S1 = (alpha*d/d(alpha) - 1) log Z at alpha=1 symbolically; "
    "show explicitly that the O((1-alpha)^2) piece does not contaminate the "
    "linear piece.\n"
    "(d) Structural robustness test: perturb the O((1-alpha)^2) coefficient "
    "to an arbitrary nonzero toy value and confirm the entropy operator "
    "still annihilates it at alpha=1, for ANY such value.\n"
    "(e) Produce a SYMBOLIC (sympy simplify/equals, not merely numeric) "
    "confirmation that the resulting log-coefficient equals -1/90, with M, "
    "Area, epsilon kept symbolic throughout.\n"
    "(f) Explicitly address why the final log argument is written as "
    "log(Area(Sigma)/epsilon^2) rather than log(const/epsilon^2), given the "
    "a_2-order piece is a pure number, not Area-proportional: either close "
    "this via an actual first-principles argument, or state plainly that it "
    "remains an open scheme-convention choice inherited from the leading "
    "term - do not assert it is derived if it is not.\n\n"
    "GAP 4 - STANDALONE SYNTHESIS DOCUMENT (never yet produced as its own "
    "deliverable in any prior attempt - must not be scattered across "
    "'Scope and limitations' notes): produce a single document stating "
    "explicitly and separately:\n"
    "(a) The xi-independence of -1/90 (both xi=0 and xi=1/6 give the same "
    "result) is a property SPECIFIC to Ricci-flat Schwarzschild (R-bar=0 "
    "kills all xi,m^2-dependent E-terms) - NOT a general coupling-"
    "independence theorem; it would NOT hold on a non-Ricci-flat "
    "background (RN, dS), where the Gap-1 corrected general a_2 formula's "
    "xi-dependent terms remain active.\n"
    "(b) The Gap-3 literature verdict verbatim (no post-2020 cross-matter "
    "universality paper found, recall-based, tooling-limited).\n"
    "(c) Explicit carry-forward: the original premise 'Integral_Sigma "
    "R-bar_{inin} dSigma reduces to Area(Sigma)' is FALSE AS STATED for "
    "Schwarzschild - it is a pure, M-independent number (8*pi), not "
    "Area-proportional - and the corrected mechanism (per Gap 2 above) must "
    "be summarized here so this correction is not lost in an intermediate "
    "step.\n"
    "Do not conflate (a), (b), and (c) with each other."
)

results = deep_research(
    task,
    max_rounds_planning=50,
    max_rounds_control=100,
    max_plan_steps=3,
    n_plan_reviews=1,
    plan_instructions=(
        "This task has exactly two remaining deliverables (labeled GAP 2 "
        "and GAP 4 in the task text), and they must be produced as TWO "
        "SEPARATE plan steps, never bundled into one agent turn - a prior "
        "attempt confirmed that combining a full symbolic derivation with "
        "printed output AND a full written synthesis document in a single "
        "engineer turn causes the response to be silently truncated at the "
        "token limit, losing the entire turn's work. Structure the plan as: "
        "Step 1 assigns engineer to execute ONLY the Gap 2 symbolic "
        "verification (sympy, with printed output). Step 2 assigns engineer "
        "or cadabra_context to produce ONLY the Gap 4 standalone synthesis "
        "document. Step 3 assigns derivation_checker to independently "
        "re-verify Step 1's symbolic work and Step 2's synthesis, and "
        "confirm the CONTEXT block's Gap 1 and Gap 3 claims are accurately "
        "carried through into Step 2's synthesis, then render a final "
        "verdict on the full four-gap derivation. Do not assign "
        "derivation_checker to originate or produce any derivation itself."
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
