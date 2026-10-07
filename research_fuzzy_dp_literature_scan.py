"""
Fuzzy del Pezzo programme, job 1: literature and novelty scan.

Context: revisiting Furuuchi-Okuyama arXiv:1008.5012 (fuzzy del Pezzo D4-branes
from D0-brane quiver gauge theories), with Franco-Torroba arXiv:1010.4029 and
Yamazaki's brane-tiling review arXiv:0803.4474. Four candidate claims came out
of the revisit (listed in the task). Before investing in the continuum-limit
derivation, we need to know which of them are already in the literature.

This is a LITERATURE run, not a computation. It deliberately does NOT describe
the C_i mass-spectrum result on fuzzy CP^2: that result is reserved for a later
blind-reproduction benchmark, so it must not appear in this run's context or
outputs.

Structured as four plan steps (fresh group chat each), per PROJECT_STATUS.md
section 3: no single step scans more than five topics.

Run from the repo root, with .venv activated:
    python research_fuzzy_dp_literature_scan.py
"""

import datetime
from cmbagent.workflows.deep_research import deep_research
from cmbagent.utils.utils import get_api_keys_from_env

timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H%M")
work_dir = f"output/{timestamp}_fuzzy_dp_literature_scan"

task = (
    "BACKGROUND (for search targeting only - not to be re-derived or assumed "
    "true): arXiv:1008.5012 constructed D4-branes wrapped on fuzzy toric del "
    "Pezzo surfaces as classical solutions of D0-brane quiver gauge theories "
    "for C^3/Z_3 and toric dP_1, dP_2, dP_3, by deleting some arrows and "
    "realising the rest as Fock-space oscillators on fixed-charge sectors. "
    "The dP_2 and dP_3 cases left one gauge node unbound. A recent revisit "
    "produced four candidate claims. For EACH, this run must establish "
    "whether it is already in the literature:\n"
    "  (A) Arrow deletion equals setting one INTERNAL brane-tiling perfect "
    "matching to zero (restriction to the compact divisor of K_S); corner "
    "perfect matchings become Cox-coordinate oscillators; for dP_2 some "
    "arrows must then be quadratic monomials in the oscillators.\n"
    "  (B) With dressings X = Phi_h c m(a) Phi_t^{-1}, Phi diagonal in the "
    "Fock basis, the fuzzy D-term equations are the critical-point equations "
    "of a convex Kempf-Ness functional on the graph of Fock states, and a "
    "solution exists iff a strictly positive network flow with prescribed "
    "net inflow exists (a linear program; a fuzzy form of King stability).\n"
    "  (C) The 2010 dP_2 solution lies exactly on a wall of marginal "
    "stability (FI parameter of one node = 0), where the D4 decays into a "
    "sub-object plus fractional branes at that node.\n"
    "  (D) At large N the quiver D-terms select an emergent Kahler metric on "
    "fuzzy dP_2 that differs at O(1) from the GLSM (Guillemin) metric.\n\n"
    "(1) QUIVER / STABILITY LITERATURE - at most five topics, live INSPIRE "
    "queries with logged query strings and hit counts: (i) all INSPIRE "
    "citations of arXiv:1008.5012 and arXiv:1010.4029, and which (if any) "
    "construct fuzzy or noncommutative D-brane solutions in quivers for "
    "toric CY3 cones; (ii) moment-map / Kempf-Ness / King-stability "
    "treatments of quiver representations realised on Fock spaces or on "
    "fuzzy toric varieties; (iii) Pi-stability and Bridgeland-stability walls "
    "for D4-branes (line bundles) on local P^2 and local del Pezzos via "
    "exceptional collections (e.g. Douglas-Fiol-Romelsberger, Aspinwall, "
    "Bridgeland, Bousseau); (iv) perfect matchings, cuts and exceptional "
    "collections (e.g. Ishii-Ueda arXiv:0911.4529, Bocklandt, Hanany-Herzog-"
    "Vegh) - specifically whether statement (A) appears; (v) D4-D2-D0 / "
    "Vafa-Witten counting on local del Pezzos from quivers (e.g. Beaujard-"
    "Manschot-Pioline).\n\n"
    "(2) EMERGENT-GEOMETRY LITERATURE - at most five topics, same logging "
    "standard: (i) Berezin-Toeplitz and Bergman-kernel quantization of toric "
    "Kahler metrics (e.g. Zelditch, Song-Zelditch, Burns-Guillemin); (ii) "
    "Donaldson's balanced metrics on toric varieties and their relation to "
    "symplectic potentials and the Guillemin metric, including finite-N "
    "discretised equations and numerics; (iii) emergent Kahler geometry from "
    "matrix models and fuzzy spaces (e.g. Ishiki, Steinacker, Berenstein, "
    "Heckman-Verlinde); (iv) canonical metrics on the blow-up of P^2 at two "
    "points: Kahler-Einstein obstruction, extremal and conformally-Kahler "
    "Einstein-Maxwell metrics, Abreu's equation; (v) quiver descriptions of "
    "noncommutative instantons on toric surfaces.\n\n"
    "(3) NOVELTY MAP: for each of (A)-(D), classify as ESTABLISHED (give the "
    "paper and the exact statement), PARTIAL (closest prior result and the "
    "precise gap), or NOT FOUND (list the queries that would have found it). "
    "Cite arXiv/INSPIRE IDs only for papers actually retrieved in steps "
    "(1)-(2); never cite from recollection. End with the three references "
    "most important to read in full before any further work.\n\n"
    "(4) VERIFICATION: every citation in (3) must be checked against its "
    "retrieved INSPIRE record (title, authors, arXiv ID), and every "
    "ESTABLISHED/PARTIAL verdict against what the retrieved abstract actually "
    "says. Flag any NOT FOUND verdict whose search log is too thin to "
    "support it."
)

results = deep_research(
    task,
    max_rounds_planning=30,
    max_rounds_control=100,
    max_plan_steps=4,
    n_plan_reviews=1,
    plan_instructions=(
        "Use exactly four steps. Step 1 must be inspirehep_context executing "
        "task item (1): at most five topics, live queries, a logged query "
        "string and hit count for every search. Step 2 must be "
        "inspirehep_context executing task item (2) under the same limits. "
        "Step 3 must be researcher executing task item (3), using ONLY papers "
        "retrieved in Steps 1-2. Step 4 must be derivation_checker executing "
        "task item (4): verifying citations against retrieved records and "
        "verdicts against retrieved abstracts, and flagging overclaimed "
        "novelty. Do not assign derivation_checker to originate any search "
        "or verdict itself. No step may attempt the physics computations "
        "behind claims (A)-(D)."
    ),
    work_dir=work_dir,
    api_keys=get_api_keys_from_env(),
    # Recorders / terminator / controller fall back to default_llm_model and
    # use forced tool_choice - keep them on a model that accepts it.
    default_llm_model="claude-sonnet-5",
    default_formatter_model="claude-haiku-4-5-20251001",
    planner_model="claude-fable-5-1",
    plan_reviewer_model="claude-opus-5-5",
    engineer_model="claude-sonnet-5-5",
    researcher_model="claude-opus-5-5",
    idea_maker_model="claude-opus-5-5",
    idea_hater_model="claude-opus-5-5",
    camb_context_model="claude-sonnet-5-5",
    inspirehep_context_model="claude-sonnet-5-5",
    cadabra_context_model="claude-sonnet-5-5",
    derivation_checker_model="claude-opus-5-5",
)

print("\n\n=== DONE ===")
print("work_dir:", work_dir)
print("Cost lines should now be non-zero (price added in get_model_config).")
print(f"    python extract_report.py {work_dir}")
