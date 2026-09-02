"""
Direction (i) from the KK-tower follow-up discussion: the direct 5D
conical-singularity / replica calculation on the black string
Schwarzschild_4 x S^1, closing the "genuinely open" item flagged by the
2026-07-16 run (output/2026-07-16_1726_kk_tower_entanglement_entropy):
does a true 5D calculation reproduce, modify, or bypass the divergence
structure of the naive 4D KK-mode sum?

PHYSICS SETUP: same 5D free scalar on (Euclidean Schwarzschild_4) x S^1
(S^1 of radius R, transverse to the horizon) as the previous run - but now
the replica/conical construction is applied to the FULL 5D geometry rather
than mode-by-mode in 4D. Because the deficit lives entirely in the 4D
factor and the S^1 is flat and transverse, the 5D conical heat-kernel
trace factorizes EXACTLY:

    Tr K_5^{cone}(t) = Tr K_4^{cone}(t) * Theta(t),
    Theta(t) = Sum_{n in Z} exp(-t n^2 / R^2),

so the "direct 5D calculation" is the single proper-time integral of this
product - NOT a per-mode coefficient extraction followed by an n-sum.

HYPOTHESES THIS RUN EXISTS TO TEST (test, do not force):
  (H1) Odd-dimensional UV: Poisson resummation of Theta shifts all powers
       of t by -1/2 at small t, so the t^0 term sourcing log(eps)
       vanishes -> NO log(eps) divergence in 5D; only odd power
       divergences (1/eps^3, 1/eps) with coefficients tied to the
       3d horizon volume A_3 = A * 2*pi*R.
  (H2) Crossover: for t >> R^2 only n=0 survives, so the 4D log term
       reappears with the KK scale as its UV matching end:
       -(1/90) log(A/eps^2)  -->  -(1/90) log(A/R^2)  (+ finite).
  (H3) Scheme diagnosis: the previous run's zeta-regularized "0"
       corresponds to the absence of any NET log from the n != 0 tower,
       while the untested hard-cutoff answer ~2N+1 corresponds to the
       linear R/eps power divergence; the invalid step in the naive sum
       is the interchange of Sum_n with the log-coefficient extraction,
       visible in the incomplete-gamma structure Gamma(0, eps^2 m_n^2)
       of the true per-mode integral.

Run from the repo root, with .venv activated:
    python research_5d_black_string_log_coefficient.py
"""

import datetime
from cmbagent.workflows.deep_research import deep_research
from cmbagent.utils.utils import get_api_keys_from_env

timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H%M")
work_dir = f"output/{timestamp}_5d_black_string_log_coefficient"

task = (
    "CONTEXT (verified prior results, treat as checked starting points):\n\n"
    "(A) For a free scalar of any mass m and coupling xi in D=4 on Euclidean "
    "Schwarzschild, via the replica trick with Fursaev-Solodukhin "
    "curvature-splitting + Seeley-DeWitt a_2, every xi- and m^2-dependent "
    "term in the corrected a_2 vanishes identically on the Ricci-flat "
    "background, leaving the mass/coupling-independent "
    "(1/180)(Riem^2 - Ric^2) term as the sole source of the log-divergent "
    "entropy contribution S1 = -(1/90) log(A/eps^2), with A = 4*pi*r_h^2 "
    "the 4D horizon area and eps the UV cutoff length.\n\n"
    "(B) A completed prior run (KK tower on M4 x S^1, masses "
    "m_n^2 = n^2/R^2, n in Z, each mode treated as an independent 4D "
    "scalar) established: the naive tower sum of identical per-mode "
    "log-coefficients is divergent as literally written; the smooth "
    "regularizations (Riemann-zeta via 1 + 2*zeta(0), Epstein-zeta limit "
    "at s=0, Abel/exponential cutoff finite remainder) all agree on the "
    "regularized count Sum_{n in Z} 1 = 0; a hard mode-number cutoff "
    "|n| < N instead gives 2N+1, divergent and scheme-dependent; and the "
    "run explicitly flagged as GENUINELY OPEN (i) whether the regularized "
    "0 is physical, and (ii) what a direct first-principles 5D "
    "replica/conical calculation on Schwarzschild x S^1 would give. THIS "
    "run exists to close (ii) and thereby inform (i).\n\n"
    "NEW TASK: perform the direct 5D conical-singularity calculation of "
    "the one-loop entanglement-entropy divergence structure for a free "
    "5D scalar on (Euclidean Schwarzschild_4) x S^1, S^1 of radius R "
    "transverse to the horizon, and reconcile it quantitatively with the "
    "naive 4D mode-sum of prior result (B).\n\n"
    "Central technical device (state and justify, do not silently "
    "assume): on this PRODUCT geometry the 5D Laplacian separates and "
    "the conical deficit of the replica construction lives entirely in "
    "the 4D factor, so the 5D conical heat-kernel trace factorizes "
    "EXACTLY as Tr K_5^{cone}(t) = Tr K_4^{cone}(t) * Theta(t) with "
    "Theta(t) = Sum_{n in Z} exp(-t*n^2/R^2). No new curvature couplings "
    "arise because the S^1 is flat. The 'direct 5D calculation' is then "
    "the single proper-time integral over t of this product, with the "
    "SAME entropy-extraction prescription (replica derivative at the "
    "conical point) and the SAME verified 4D conical ingredients as in "
    "(A) - the difference from run (B) is solely that the n-sum sits "
    "INSIDE the proper-time integral instead of outside the "
    "coefficient extraction.\n\n"
    "Investigate the following honestly, as a genuine open exploration - "
    "hypotheses below are stated to be TESTED, not forced; refuting any "
    "of them cleanly is as valuable as confirming it:\n\n"
    "(1) LITERATURE FIRST (targeted, complementary to run (B)'s recorded "
    "searches - do not simply repeat its 27 queries): search INSPIRE for "
    "(a) direct conical-singularity / replica entanglement-entropy "
    "calculations in five or general odd dimensions, and on black-string "
    "or (black hole) x S^1 backgrounds specifically; (b) the established "
    "statement that in odd bulk dimensions the entanglement-entropy "
    "divergence expansion contains no logarithmic term for smooth "
    "entangling surfaces (no conformal anomaly / no integer-order "
    "a_{d/2} coefficient), e.g. in the CFT and heat-kernel literature; "
    "(c) Poisson resummation / winding decomposition of KK heat-kernel "
    "traces and its use in Casimir-energy and effective-action "
    "computations; (d) decoupling of heavy modes in entanglement-entropy "
    "or effective-action proper-time integrals (incomplete-gamma-type "
    "suppression). Report explicitly whether the specific factorized "
    "black-string calculation posed here already exists.\n\n"
    "(2) SMALL-t / UV STRUCTURE (tests H1): apply Poisson resummation "
    "Theta(t) = R*sqrt(pi/t) * Sum_{w in Z} exp(-pi^2*R^2*w^2/t) and "
    "derive, with real executed symbolics (sympy; series manipulation "
    "and term-by-term proper-time integration with printed intermediate "
    "steps), the divergence structure of the 5D entropy as eps -> 0 at "
    "fixed R, r_h. Specifically: (a) show whether the t^0 coefficient of "
    "the entropy integrand vanishes after the w=0 continuum piece "
    "multiplies the 4D conical expansion - i.e., whether ANY log(eps) "
    "term survives in 5D; (b) enumerate the power divergences that DO "
    "appear (expected: t^{-3/2} and t^{-1/2} integrands giving 1/eps^3 "
    "and 1/eps), expressing their coefficients in terms of the 3d "
    "horizon volume A_3 = A * 2*pi*R with explicit dimensional "
    "bookkeeping; (c) treat the w != 0 winding terms honestly: show they "
    "are non-perturbatively suppressed at small t and therefore "
    "contribute NO divergences, and either compute or rigorously bound "
    "their finite R-dependent (Casimir-like) contribution.\n\n"
    "(3) CROSSOVER / IR STRUCTURE (tests H2): split the proper-time "
    "integral at t ~ R^2 (the crossover scale already located "
    "numerically in run (B)'s heat-kernel diagnostic). For t >> R^2, "
    "Theta(t) -> 1 + 2*exp(-t/R^2) + ...: show that only the n=0 mode "
    "survives and determine whether the surviving logarithm of the full "
    "5D calculation is -(1/90) log(A/R^2) - i.e., the single-mode 4D "
    "log with the KK scale R replacing eps as the UV matching end - "
    "plus eps-independent finite terms. Track explicitly which "
    "dimensionless log arguments (A/eps^2, A/R^2, R/eps, R^2/eps^2) "
    "appear anywhere in the final assembled answer, since conflating "
    "them is the most likely bookkeeping error in this calculation.\n\n"
    "(4) RECONCILIATION WITH THE NAIVE MODE SUM (tests H3): the honest "
    "per-mode object underlying run (B) is not a bare log-coefficient "
    "but the proper-time integral with the mode's Boltzmann factor, "
    "i.e. an incomplete-gamma structure ~ Gamma(0, eps^2 * m_n^2) per "
    "mode (up to the verified -1/90 normalization), exponentially "
    "suppressed once m_n * eps >> 1. (a) Derive this per-mode form "
    "explicitly and state precisely which interchange (n-sum vs "
    "coefficient extraction / t-integral) run (B) performed and why it "
    "is invalid at fixed eps << R. (b) Compute the asymptotics of "
    "Sum_{n in Z} Gamma(0, eps^2*n^2/R^2) for eps/R -> 0 analytically, "
    "AND verify it numerically (mpmath/numpy: evaluate the sum directly "
    "for several small eps/R values and fit against the predicted "
    "structure, e.g. c_1*(R/eps) + c_log*log(...) + c_0, printing the "
    "fit residuals). (c) Show whether this correctly reproduces the "
    "direct 5D answer from items (2)-(3), and give the explicit "
    "dictionary: which piece of the true 5D answer the zeta-regularized "
    "'0' of run (B) corresponds to, and which piece the hard-cutoff "
    "'2N+1' corresponds to (expected under H3: absence of net tower log, "
    "and the linear R/eps divergence with N ~ R/eps, respectively) - "
    "but report the actual computed correspondence even if it differs.\n\n"
    "(5) PHYSICAL ASSESSMENT (hedge interpretive claims explicitly): if "
    "and only if supported by the computations above, assess: (a) "
    "whether run (B)'s regularized 0 is now explained as the "
    "dimensional-reduction shadow of an odd-dimensional UV theory with "
    "no log term, i.e. physical rather than scheme artifact within the "
    "smooth-regulator family; (b) the EFT reading - the 4D description's "
    "log is IR-matched at the KK scale and the residual eps-divergences "
    "are genuinely 5D - and its connection to species-scale / Swampland "
    "reasoning (tower of light states lowering the cutoff; the "
    "candidate references recorded in run (B): 2303.13580, 2310.04488, "
    "2305.10489, 2304.03902, plus anything new from step (1)), with any "
    "such connection explicitly labeled as this analysis's own "
    "interpretive link unless a found paper states it; (c) what the "
    "R-dependence of the surviving log term implies as R -> infinity "
    "(decompactification / infinite-distance limit) - flag but do not "
    "develop the moduli-dependence question, which is scoped for a "
    "separate follow-up run.\n\n"
    "(6) Produce a clear final statement of what was actually "
    "established versus what remains genuinely open, including an "
    "explicit verdict on each of H1, H2, H3 (confirmed / refuted / "
    "undecided-and-why). This is real research; an honest 'H_k is "
    "refuted' or 'undecided because X' is an acceptable and valuable "
    "outcome, not a failure."
)

results = deep_research(
    task,
    max_rounds_planning=30,
    max_rounds_control=100,
    max_plan_steps=5,
    n_plan_reviews=1,
    plan_instructions=(
        "Structure as up to five steps. Step 1 must be inspirehep_context "
        "performing the targeted literature search of task item (1) with "
        "live queries and recorded query/hit-count logs, complementary to "
        "(not repeating) the prior run's searches. Step 2 must be "
        "cadabra_context specifying the computation precisely enough for "
        "direct implementation: the exact factorized heat-kernel object, "
        "the entropy-extraction prescription reused from the verified 4D "
        "result, the Poisson-resummation identity to be verified in code "
        "(not just quoted), conventions (natural units; A, A_3, eps, R "
        "dimensions; n=0 counted once; which limits are taken in which "
        "order), and the tool choice with justification - sympy/mpmath is "
        "expected to suffice since the product geometry reuses the "
        "already-verified 4D conical ingredients and no new tensor "
        "algebra should arise; Cadabra2 only if re-verification of a 4D "
        "conical ingredient is genuinely needed. The engineer work (task "
        "items 2-4) may be a single step or split into two steps at the "
        "planner's discretion - if split, the natural seam is the direct "
        "5D calculation (items 2-3) versus the mode-sum reconciliation "
        "(item 4); either way every claimed identity must be backed by "
        "real printed symbolic/numeric output, including the numerical "
        "fit of item (4b). The final step must be derivation_checker "
        "verifying at minimum: that the factorization "
        "Tr K_5 = Tr K_4 * Theta is justified for the product geometry, "
        "not silently assumed; that the Poisson-resummed small-t "
        "expansion and its term-by-term integration are genuinely "
        "executed and internally consistent (spot-check coefficients by "
        "hand); that log arguments (A/eps^2 vs A/R^2 vs R/eps) are never "
        "conflated and dimensional bookkeeping of A_3 = A*2*pi*R is "
        "explicit; that the item-(4) reconciliation is computed, not "
        "asserted, with the numerical fit actually printed; that H1-H3 "
        "verdicts follow from the computations rather than from the "
        "hypothesis framing; and that interpretive species-scale/"
        "Swampland links in item (5) are hedged as this analysis's own "
        "connections. Do not assign derivation_checker to originate any "
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
print("Run extract_report.py against this work_dir to get a readable compiled report:")
print(f"    python extract_report.py {work_dir}")
