import cmbagent

task = """
FORMULATION-AND-SEARCH TASK (no heavy numerics expected): sharpen and
literature-anchor the following open structural question in the operator-
algebraic approach to black hole entanglement entropy.

BACKGROUND (established in our prior runs; treat as given inputs, do not
re-derive):
- On Schwarzschild_4 x S^1, the naive procedure "extract each 4D KK mode's
  log-divergence coefficient, then sum over the tower" fails: the epsilon->0
  limit and the KK sum do not commute. The honest per-mode object is
  -(1/90)*Gamma(0, eps^2 n^2 / R^2), and the tower-summed divergence is a
  power law c_1/eps with c_1 = 2*sqrt(pi), not a log. A citable, general
  published statement of this interchange error exists: arXiv:2606.01167
  (Arrighi & Casarin) states that direct zeta-regularization of per-level
  coefficients followed by summing over KK levels does not yield correct
  results, on dimensional grounds.
- The genuinely 5D calculation has NO log(eps) term at all (odd bulk
  dimension, no a_{5/2}-type t^0 heat-kernel coefficient), verified
  numerically to ~1e-15 in our prior run.

THE QUESTION TO FORMULATE PRECISELY:
The UV divergence of entanglement entropy reflects the Type III_1 nature of
the subregion von Neumann algebra. Crossed-product constructions
(Leutheusser-Liu; Witten; Chandrasekaran-Penington-Witten and related work)
convert Type III_1 to Type II, where a renormalized entropy - essentially
generalized entropy - is well defined up to a state-independent constant.
In our compactified setting:
- Each 4D KK mode (mass m_n = |n|/R) furnishes a QFT on the Schwarzschild_4
  exterior whose horizon-exterior algebra is a Type III_1 factor.
- The full tower assembles into the algebra of the single 5D field outside
  the black-string horizon on Schwarzschild_4 x S^1.
Does the crossed-product renormalization COMMUTE with the KK decomposition?
That is: (a) is the Type II entropy of the 5D algebra equal to a suitably
regularized sum of per-mode Type II entropies, and (b) does the species/
tower divergence reappear as a concrete obstruction anywhere in that
assembly (e.g. in the choice of trace normalization per mode, in the
tensor-product structure over modes, or in the modular-crossed-product
construction applied mode-wise vs. to the whole algebra at once)? Note the
suggestive parallel: our heat-kernel result already shows a per-mode-first
procedure fails at the level of divergence coefficients - the question is
whether the same interchange failure has an algebraic avatar.

WHAT TO PRODUCE:
1. An exhaustive INSPIRE-HEP literature scan establishing: (i) the current
   state of the crossed-product/Type II program (key papers, constructions
   used, what spacetimes and matter content have been treated); (ii)
   whether ANY existing work treats compact internal dimensions, KK towers,
   or species-scale physics within crossed-product constructions; (iii) the
   nearest existing results if the exact question is untreated (e.g. tensor
   products of Type III factors, crossed products of infinite tensor
   products, mode decompositions in algebraic QFT). Log exact query strings
   and hit counts for auditability.
2. A precise mathematical formulation document: define the per-mode
   algebras and the 5D algebra; state the two candidate constructions
   (crossed product applied mode-wise then assembled, vs. applied once to
   the full 5D algebra); state precisely what "commutes" means, including
   how the trace/entropy normalization ambiguity per mode enters; identify
   where the tower divergence could obstruct the assembly; and state the
   conjecture(s) in a form a mathematical physicist could attack.
3. An honest novelty verdict: is this question genuinely open, partially
   treated, or already answered? Include a candidate first tractable
   sub-problem (e.g. two modes instead of the full tower, or free fields
   on Rindler_4 x S^1 instead of Schwarzschild).
Do NOT attempt heavy symbolic or numerical computation - this is a
formulation and literature task. Modest symbolic bookkeeping to state the
constructions precisely is fine.
"""

results = cmbagent.deep_research(
    task=task,
    max_plan_steps=3,
    n_plan_reviews=1,
    plan_instructions=(
        "Three steps: (1) inspirehep_context performs the exhaustive "
        "literature scan; (2) researcher writes the precise mathematical "
        "formulation document and novelty assessment, building on the "
        "scan; (3) derivation_checker adversarially reviews the "
        "formulation for asserted-but-not-demonstrated claims, "
        "tautological framing, and scope-narrowing - its usual failure "
        "modes to catch. No engineer step is needed unless the "
        "controller finds modest symbolic bookkeeping genuinely "
        "necessary mid-step."
    ),
    max_rounds_control=100,
    researcher_filename="crossed_product_kk_formulation",
    work_dir="output/2026-07-23_crossed_product_kk_formulation",
)
