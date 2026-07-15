"""
Narrow follow-up completing output/2026-07-15_0959_inspire_agent_validation,
which ended one message short of a clean final PASS - purely a
max_rounds_control=40 budget cap in the original script, not an
infrastructure bug (confirmed: message 39/40 was derivation_checker's
"PASS WITH CAVEATS" verdict itself; the transcript just ended before
controller could route the single required fix back to inspirehep_context
and get final sign-off).

The required fix is tiny and fully specified by derivation_checker's own
review - not a re-search, just a wording correction: the report claimed
"essentially the full result set" was screened across three sort orders,
but derivation_checker independently computed the actual union is ~58/74
records (~78%), not "essentially complete." This task supplies that exact,
already-computed correction directly, so nothing needs to be redone or
reconstructed from memory - all 37+ live queries and the full source list
from the original run are treated as established, verified context.

Run from the repo root, with .venv activated:
    python fix_inspire_validation_coverage_claim.py
"""

import datetime
from cmbagent.workflows.deep_research import deep_research
from cmbagent.utils.utils import get_api_keys_from_env

timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H%M")
work_dir = f"output/{timestamp}_inspire_validation_coverage_fix"

task = (
    "CONTEXT (verified, established - do not redo any searching): a live "
    "INSPIRE-HEP literature search (37+ distinct query phrasings across "
    "multiple rounds, three sort orders - mostrecent/mostcited/bestmatch - "
    "applied to the single most on-topic 74-hit query) was already "
    "performed and reviewed, addressing whether any 2020+ paper proves "
    "cross-matter-content universality of the logarithmic-in-area black "
    "hole entropy correction via heat-kernel/one-loop methods. The "
    "substantive negative-existence conclusion (no such paper found; two "
    "newly-found 2020 papers 2012.12227 and 2007.11497 correctly assessed "
    "as reinforcing, not resolving, matter-content dependence; "
    "Iliesiu-Turiaci 2003.02860 correctly excluded; Wald/anomaly-sense and "
    "string-compactification-sense uses of 'universal' correctly "
    "distinguished from cross-matter-content universality; date-filter "
    "no-op and non-functional refersto:/citedby: tooling correctly "
    "disclosed as residual gaps) was independently reviewed and confirmed "
    "sound by derivation_checker.\n\n"
    "The ONLY remaining issue, per derivation_checker's own explicit "
    "review, is a single inaccurate coverage-completeness claim. The "
    "report stated the three sort-order top-25 views 'surface essentially "
    "the full result set' with only 'a small residual' unscreened. "
    "derivation_checker independently computed the actual union of unique "
    "arXiv IDs across the three lists: mostrecent contributes 25, mostcited "
    "adds 21 new, bestmatch adds 12 new, for a union of approximately 58 of "
    "74 unique records (~78% coverage) - leaving approximately 16 records "
    "(~22%) never viewed under any of the three sort orders. This is "
    "meaningfully different from 'essentially the full result set' / 'a "
    "small residual.'\n\n"
    "TASK: reissue the final literature search report, unchanged in every "
    "respect EXCEPT this single correction. Specifically:\n"
    "1. Replace any 'essentially the full result set' / 'small residual' "
    "framing of the 74-hit screening coverage with the accurate, already-"
    "computed figures: approximately 58 of 74 unique records screened "
    "(~78% coverage), approximately 16 records (~22%) never viewed under "
    "any of the three sort orders.\n"
    "2. Retain the qualitative judgment that the marginal risk of a missed "
    "universality-proof paper in that unscreened residual is low, given "
    "the composition of what was screened (overwhelmingly unrelated "
    "modified-gravity/LQG/GUP papers with only a handful of Sen-line "
    "entries) - but pair this judgment with the corrected percentage "
    "rather than the original overstated framing.\n"
    "3. Do not change anything else: Search Mode remains LIVE, all query "
    "strings remain reported for auditability, the source list, the "
    "established-vs-contested breakdown, the two newly-found papers' "
    "characterization, and all other disclosed gaps (date-filter no-op, "
    "non-functional citation-graph tooling, no pagination parameter) stay "
    "exactly as they were - only the coverage-percentage claim changes."
)

results = deep_research(
    task,
    max_rounds_planning=20,
    max_rounds_control=30,
    max_plan_steps=2,
    n_plan_reviews=0,
    plan_instructions=(
        "Exactly two steps. Step 1: inspirehep_context applies the single, "
        "fully-specified correction described in the task - reissuing the "
        "report with only the coverage-percentage claim changed, nothing "
        "else. Step 2: derivation_checker verifies ONLY that (a) the "
        "coverage claim now matches the corrected ~58/74 (~78%) figure, "
        "and (b) nothing else was altered, added, or dropped in the "
        "process - a word-level diff mindset, not a full re-review of the "
        "underlying search. Render a final Verdict line explicitly."
    ),
    work_dir=work_dir,
    api_keys=get_api_keys_from_env(),
    default_llm_model="claude-sonnet-5",
    default_formatter_model="claude-haiku-4-5-20251001",
    planner_model="claude-haiku-4-5-20251001",
    plan_reviewer_model="claude-haiku-4-5-20251001",
    engineer_model="claude-sonnet-5",
    researcher_model="claude-haiku-4-5-20251001",
    idea_maker_model="claude-haiku-4-5-20251001",
    idea_hater_model="claude-haiku-4-5-20251001",
    camb_context_model="claude-haiku-4-5-20251001",
    inspirehep_context_model="claude-sonnet-5",
    cadabra_context_model="claude-haiku-4-5-20251001",
    derivation_checker_model="claude-sonnet-5",
)

print("\n\n=== DONE ===")
print("work_dir:", work_dir)
print("Run extract_report.py against this work_dir to get a readable compiled report:")
print(f"    python extract_report.py {work_dir}")
