
## [Unreleased] - continued (previous_steps_execution_summary root-cause fix)

### Upstream fix (cmbagent) — the actual root cause of derivation_checker's empty context

Yesterday's fix (adding `{previous_steps_execution_summary}` to
`derivation_checker.yaml`) was necessary but not sufficient — the variable itself was
never being populated in the first place for `inspirehep_context`/`cadabra_context`.

- `cmbagent/workflows/deep_research.py`: the cross-step summary-extraction loop
  strips `_context`/`_agent` from the current step's assigned agent name before
  searching backward through chat history for a matching message — a convention
  built for `camb_context` (which has a `camb_response_formatter` companion, so the
  stripped name + `_response_formatter` correctly resolves). Our `inspirehep_context`
  and `cadabra_context` deliberately have no `_response_formatter` companion (they
  hand off directly to `controller`), so the stripped-name lookup (`inspirehep`,
  `cadabra`) never matched anything, and their real output silently never got
  threaded into `previous_steps_execution_summary` — confirmed via a real run where
  `derivation_checker` correctly reported the field as empty even with the prompt
  fix in place. Fixed by also checking the **original, unstripped** agent name
  before falling back to the stripped-name variants (computed once before the
  search loop, rather than re-derived on every message as the original code did).
  See `patch_fix_step_summary_extraction.py`.

### Validation — confirmed fully working end-to-end, with all fixes compounding correctly

Re-ran the replica-trick task (log-area entropy correction, literature +
derivation + verification) after today's two fixes (`max_tokens` raise from
yesterday, `previous_steps_execution_summary` fix today). Result:

- All three custom agents ran in their intended plan-assigned roles:
  `inspirehep_context` (Step 1), `cadabra_context` (Step 2), `derivation_checker`
  (Step 3) — no `researcher` fallback this run.
- Total cost for the full run: ~41K tokens for Step 3 alone (vs. hundreds of
  thousands in earlier truncation-storm runs) — the `max_tokens` fix held.
- `derivation_checker` finally received the real Step 1/2 content and produced a
  genuinely substantive **UNRESOLVED-DEGENERATE** verdict, catching:
  - A concrete computational bug: a dropped π factor between the hand-derivation
    (−π/90) and the printed SymPy result (−1/90), with an unverified "the π cancels"
    claim never actually demonstrated in code.
  - A **tautological cross-check**: the spin-weighting ratio test
    (ratio_fermion=0, ratio_vector=0) is algebraically guaranteed to pass regardless
    of whether the derivation's own coefficient κ was computed correctly, since κ
    cancels out of the ratio — correctly identified as validating nothing about the
    actual derivation performed.
  - Silent scope narrowing: the derivation's spherical-surface assumption means it
    can only ever probe a-type (Euler-density) universality, never c-type (Weyl²)
    universality, which the original question's framing did not exclude.
  - Correctly refused to let Step 1's hedged/unconfirmed literature candidates be
    reported as established cross-matter-content universality in any final synthesis.

This is the clearest demonstration yet that the full pipeline — literature retrieval
with honest confidence-flagging, symbolic derivation with explicit convention
logging, and adversarial verification catching both a real bug and a subtler
tautological-check failure — works as designed on a genuinely hard, open-ended
research task, not just a toy dimensional-analysis check.

### Known remaining gap (not yet investigated)

`researcher_executor`'s "save report to disk" step does not appear to actually write
a file anywhere in the output tree (`work_dir` or elsewhere) — confirmed via a
targeted filesystem search after a run showed a "Saving report..." step and printed
a `<!-- filename: ... -->`-tagged markdown block. `researcher_executor` has no
custom `.py` implementation (plain YAML-only `BaseAgent`), so its "save" action may
only be a simulated/described action in conversation rather than genuine code
execution. Worked around for now by extracting final report content directly from
the saved `chat_history_step_*.json` transcripts rather than relying on the
built-in save step. Worth root-causing properly in a future session.
