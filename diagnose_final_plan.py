"""
Diagnostic run: monkeypatches save_final_plan to print the actual type and
content of final_context["final_plan"] before calling the real function, so we
can see exactly what shape it's in when the TypeError fires.
"""

import sys
import cmbagent.workflows.deep_research  # ensures it's loaded into sys.modules
dr_module = sys.modules["cmbagent.workflows.deep_research"]

_original = dr_module.save_final_plan

def _patched(final_context, work_dir):
    plan_obj = final_context.get("final_plan", "<MISSING>")
    print("\n>>> DIAGNOSTIC: save_final_plan called")
    print(f">>> type(final_plan) = {type(plan_obj)}")
    print(f">>> repr(final_plan) (truncated) = {repr(plan_obj)[:500]}")
    return _original(final_context, work_dir)

dr_module.save_final_plan = _patched

# ---- rest is identical to test_deep_research_bh_entropy.py ----

from cmbagent.workflows.deep_research import deep_research
import re
from datetime import datetime


def make_work_dir(task, base="~/Projects/CMBagentForHEPTH_wClaude/cmbagent/output"):
    """Derive a unique, human-readable work_dir from the current timestamp and
    a short slug of the task text, so runs never collide or silently overwrite
    each other (deep_research() has no built-in auto-naming - work_dir is just
    a plain string parameter you're expected to supply)."""
    slug = re.sub(r'[^a-z0-9]+', '-', task.lower())[:40].strip('-')
    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M")
    return f"{base}/{timestamp}_{slug}"

task = (
    "Derive the leading-order correction to the Bekenstein-Hawking entropy "
    "from a single free scalar field via the replica trick, and identify "
    "which recent (2020 or later) papers established the universality of "
    "this log-area correction coefficient across different matter content."
)

results = deep_research(
    task,
    max_plan_steps=3,
    n_plan_reviews=1,
    max_rounds_planning=20,
    max_rounds_control=100,
    default_llm_model="claude-sonnet-5",
    default_formatter_model="claude-haiku-4-5-20251001",
    work_dir=make_work_dir(task),
    plan_instructions=(
        "In addition to engineer (code/computation) and researcher (writing/"
        "interpretation), three specialized agents are available for this task: "
        "inspirehep_context (searches INSPIRE-HEP/arXiv hep-th literature and "
        "distinguishes established results from contested claims - use for any "
        "sub-task that needs identifying specific papers or checking what's "
        "established in the literature), cadabra_context (provides guidance on "
        "symbolic tensor/index algebra tools like Cadabra2, SymPy, EinsteinPy - "
        "use for sub-tasks involving heat-kernel coefficients, curvature "
        "invariants, or other tensor computations), and derivation_checker "
        "(critiques a completed derivation for dimensional consistency, correct "
        "limits, sign conventions, citation grounding, and degeneracy/"
        "under-determination - use as a dedicated verification step after a "
        "substantive derivation is complete, especially for results that could "
        "be contested or scheme-dependent). Assign these agents to specific plan "
        "steps whenever a sub-task genuinely matches their specialty."
    ),
)
