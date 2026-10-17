
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

## [Unreleased] - continued (prompt-caching Phase 0: per-call usage log)

Phase 0 of `docs/prompt_caching_plan.md`: measure before caching anything. No
behaviour change: nothing is cached, and with the switch off every code path is
inert.

### Upstream change (ag2 fork, branch `cmbagent-real-base`, commit `552f5cb9`)
- `autogen/oai/anthropic.py`, `autogen/oai/client.py`: when the environment
  variable `CMBAGENT_CALL_LOG` is set to a file path, every Anthropic call
  appends one JSON line: `ts`, `pid`, `agent`, `step` (plan step, read
  defensively from `agent.context_variables["current_plan_step_number"]`, `None`
  if unavailable), `model`, `input_tokens`, `cache_creation_input_tokens`,
  `cache_read_input_tokens`, `output_tokens`, sha256 prefixes of the system
  block, the tools list, the first message and the `thinking` / `tool_choice`
  options, `system_chars`, `n_messages` and `stop_reason`. Token counts are
  recorded only if they are real ints. A read-only observer: with logging on,
  the request sent to the API and the completion returned to ag2 are identical
  to those with it off.
- `anthropic.py` has a single SDK call site (`self._client.messages.create`;
  streaming is forced off, there is no `beta`, `parse` or async path), so one
  hook covers every API path. A test pins that.
- The writer is called from a `finally:` around `client.create(params)`, so a
  call that was billed and then raised while handling the response is still
  logged, and it sits above `@lru_cache` so `log_cache_seed_value` keeps its
  cache (placing it between the decorator and the `def` would memoise it and log
  only the first call per client/agent pair). It never raises: a write failure
  only warns.
- Applied to the venv by `patch_call_usage_log.py`, which reproduces exactly the
  fork commit (idempotent via marker `hep-theory fork: per-call usage log`;
  exits 1 without writing if an anchor is missing or only one file is patched;
  restores the first file if the second write fails; explicit UTF-8). Re-run it
  after any `.venv` rebuild; `test_patch_markers_present` fails if the patch was
  dropped.

### cmbagent side
- `dev_scripts/summarize_call_log.py`: per-agent summary of a log and the
  Phase 3 / 4 / 5 verdict lines. Pairs of calls are formed within one
  `(agent, pid)`, so several processes can append to one file. System churn
  (Phase 4) counts changes only between consecutive calls with the same `pid`
  and the same known `step`; where both steps are `None` only flip-flops
  count (a return to a system hash already seen for that agent in that pid);
  pairs with one unknown step are not compared. Window slides (Phase 3) need
  the same known step (or both unknown). Gaps (Phase 5) are counted between
  same-`pid`, same-system-hash calls only, since otherwise no cache hit was
  possible. The output reports the share of records with `step` `None`, so the
  first real run shows whether the step field works.
  Robust to odd logs: a line that is not valid or too deeply nested JSON, has a
  non-finite or bool `ts`, or an `agent` / `pid` / `model` of the wrong type is
  skipped and counted; bad bytes are replaced (a partly written log still
  summarises); a record without a system hash is unknown (not compared, not a
  distinct system); a record with no usable token counts is reported
  separately and not counted as a "short" call.
- Tests: `tests/regression/test_c0_call_log.py` (row C0 in
  `tests/regression/README.md`); `bite_check.py` gains C0 rows against the
  pre-change baseline (ag2 `dc191dd5`) and against deliberately broken variants.

### Known limitations (documented, not fixed)
- **One run per process, or one log file per run.** `pid` is the only run
  discriminator: a process that runs several `one_shot` calls restarts step
  numbers at 1, so the last call of one run can pair with the first of the next
  (a spurious gap or step-1 change).
- **Always set `CMBAGENT_CALL_LOG` to an absolute path.** A relative path is
  resolved at write time, so a `chdir` between calls would split the log.
- **Logging assumes calls go through `OpenAIWrapper`.** The record is left on
  the client and only the wrapper writes it out; a direct `client.create` call
  would leave a record that a later wrapper call could log under the wrong
  agent. No such caller exists today.
- **One call at a time per client.** One pending record is kept per client;
  overlapping calls on one shared client could swap records. cmbagent runs its
  agents sequentially, each normally with its own client.
- **A reused `pid` merges runs in the summary.** The log has no run id, and
  `pid` is the only discriminator, so runs that share a pid (for example every
  container run is pid 1) are read as one: the idle time between them can show
  up as a same-system gap above the TTL (a false "Phase 5 needed?"), and pairs
  are formed across the run boundary. Same remedy as above: one log file per
  run. A run id (or a `--run-gap` split) would need an ag2 change, or a
  summarizer option; not done.
- **The flip-flop fallback over-counts a legitimate A, B, A pattern when the
  step is unknown.** If the step field is unset, an agent reused at steps 1, 2,
  3 with system blocks A, B, A reports a "return to a seen hash". The fallback
  also counts a return to a hash first seen at a known step (the `seen` set is
  shared). Check the "records have step None" line first, and read the Phase 4
  verdict with that in mind.
- Gaps are differences between logged response timestamps, so each is accurate
  to about one call's latency. `--min-cacheable` defaults to 512 tokens (plan
  §2); check the current figures for Sonnet 5 and Haiku 4.5 (open item in the
  plan).
- `step` is read from each agent's own `context_variables`; whether that holds
  the current step in every group-chat configuration is not verifiable offline.
  The first real run should show a low "records have step None" share.

### Verification
- `pytest tests/regression -q`: 74 passed, 2 expected xfails, identical with
  `CMBAGENT_CALL_LOG` unset and set; the suite itself writes nothing to the log.
- `python tests/regression/bite_check.py`, run in commit mode against ag2
  `552f5cb9`: exit 0, 32 rows BITE (each fix on the baseline, and each
  deliberately broken variant), none unexpected, none skipped. Its "script
  reproduces the ag2 fork" row holds, i.e. the patched `.venv` equals the commit.
