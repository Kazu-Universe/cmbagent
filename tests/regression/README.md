# Regression test plan: hep-theory fork

Offline pytest suite for `tests/regression/`. No API calls: the LLM client is
mocked or bypassed, so the suite is free to run on every change and after
every `.venv` rebuild. Because several fixes live in patched dependency code,
the same suite also detects when a venv rebuild has silently dropped a patch.

Each test is accepted only after it has been shown to **fail with its fix
reverted** and pass with it restored.

Status: **fixed** = the bug was fixed, the test guards it; **invariant** =
a configuration rule to enforce; **open** = a known risk not yet fixed (mark
`xfail` until it is).

## Tier 1: affects every run

| ID | Bug class | Where | Test | Status |
|---|---|---|---|---|
| R1 | Provider schemas (1) | ag2 `oai/anthropic.py` | OpenAI-schema forced `tool_choice` is translated to `{"type": "tool", "name": X}` | fixed |
| R2 | Sampling params (2) | ag2 `oai/anthropic.py`, `utils.py` | Request params built for each routed Claude 5 model carry no non-default `temperature` or `top_p` | invariant (document current behaviour first) |
| R3 | Key presence (3) | ag2 `group_tool_executor.py` | A reply with `tool_calls: []` returns "no tool call" instead of raising `UnboundLocalError` | fixed |
| R4 | Empty histories (4) | ag2 `conversable_agent.py` (five sites), `oai/anthropic.py` | Each guarded reply function with `messages=[]` returns `(False, None)`; `oai_messages_to_anthropic_messages([])` does not raise | fixed |
| R5 | History resend (10) | `hand_offs.py` | `ToolSafeMessageHistoryLimiter` on synthetic histories: window respected; first kept message is never a tool result; tool-use/tool-result pairs never split. The five heavy agents are registered with windows 20 / 70 | fixed except the burst case (open, `xfail`) |
| R6 | Model routing (1, 11) | `utils.py` | Every agent that forces tool calls maps to a model accepting forced tool choice; Claude configs have `max_tokens` ≥ 32000 and a price entry | invariant |
| R7 | Thinking blocks (12) | ag2 `oai/anthropic.py` `_extract_json` | A mocked response whose first block is `thinking` still yields the JSON text | open (`xfail`) |

## Tier 2: planning and control correctness

| ID | Bug class | Where | Test | Status |
|---|---|---|---|---|
| R8 | Reply-order shadowing (5) | `plan_recorder`, `plan_router` | With a mocked plan message, `final_plan`, `proposed_plan` and `number_of_steps_in_plan` are set in context, and control passes to `plan_router` | fixed |
| R9 | Per-step state (6) | `workflows/deep_research.py` | For a three-step `final_plan.json`, step 2's `current_sub_task` and agent come from plan step 2, not step 1 (may need the loader factored into a function) | fixed |
| R10 | Agent allowlists (7) | `planner_response_formatter.py`, `status.py`, `planning.py` | Introspect each `Literal` and the four `agent_transfer_map` copies: every agent directory under `cmbagent/agents/` that can be planned appears in all of them | fixed (generalised) |
| R11 | Unknown agent names (7) | `planning.py` | `create_record_plan_constraints` with an unregistered name warns and continues; no `SystemExit` | fixed |
| R12 | Template placeholders (8) | ag2 `oai/client.py` | Formatting a system message with a missing key yields an empty string, not `KeyError` | fixed |
| R13 | Hidden naming contracts (9) | `workflows/deep_research.py` | A synthetic chat history containing `inspirehep_context` output (no formatter) appears in `previous_steps_execution_summary` | fixed |
| R14 | Interactive pauses (14) | `base_agent.py` | The five heavy agents are created with `human_input_mode="NEVER"` | fixed |

## Tier 3: configuration and tooling

| ID | Bug class | Where | Test | Status |
|---|---|---|---|---|
| R15 | Config sanitizers (13) | `utils.py` `clean_llm_config` | A registered OpenRouter slug keeps its `base_url` | fixed |
| R16 | YAML block scalars (16) | `cmbagent/agents/*/*.yaml` | Every agent YAML parses, and every `{placeholder}` in a prompt is a known context key or explicitly allowlisted | fixed + lint |
| R17 | Patch hygiene | `patch_*.py` | On a temporary copy of the target file: running a patch twice is a no-op, and a mismatched target aborts without writing | invariant |
| R18 | Simulated actions (15) | `researcher_executor` | After a mocked "save report" step, the file exists on disk | open (`xfail`) |

## How to build it

1. **Use Claude Code.** This is one of its three agreed use cases: it reads
   the real `ag2` and `cmbagent` source and writes coordinated files. Work
   on a branch, in plan mode until the test list is agreed.
2. **Order.** Tier 1 first (R1, R3, R4, R5 are self-contained), then R10,
   since it also protects every future agent addition.
3. **Bite check, per test.** Revert the fix (for venv patches, run the test
   against an unpatched copy of the file), confirm failure, restore, confirm
   pass. Record "bites: yes" in the commit message. Tier 1 automates this -
   see "Tier 1: implemented" below - rather than hand-reverting files.
4. **Run** `pytest tests/regression -q` - always scoped to this directory,
   never a bare `pytest`. See the warning below.
5. **Later.** A GitHub Actions workflow running the suite on each push
   (free for a public repository), and `/code-review` on each PR.

## Always invoke scoped: `pytest tests/regression -q`

`pyproject.toml` sets `testpaths = ["tests"]`, so a bare `pytest` (or
anything that doesn't scope to this directory) collects every file under
`tests/`, including `test_deep_research.py`, `test_one_shot_engineer.py` and
their siblings - pytest-shaped functions that make **real, paid API calls**.
Several of them read API keys / cloud credentials (`ANTHROPIC_API_KEY`,
`OPENAI_API_KEY`, `AWS_REGION`, ...) at **collection time**, not just when
actually run, so a bare `pytest --collect-only` with no credentials set
already errors out on five of them (confirmed: `PermissionError`,
`ValueError: API key or AWS credentials...`, `openai.OpenAIError`) before a
single real test body executes. That's a safe failure mode with no keys
present, but with keys present a bare `pytest` can reach real test *bodies*
that place real API calls. Always run `pytest tests/regression -q`
explicitly.

## Tier 1: implemented (`tests/regression/`)

R1, R3, R4, R5, plus the `ToolSafeMessageHistoryLimiter` burst case, are
implemented across `conftest.py`, `_checks.py`, `_baseline.py`,
`test_r1_anthropic_tool_choice.py`, `test_r3_empty_tool_calls.py`,
`test_r4_empty_histories.py`, and `test_r5_history_window.py`. Two things
found during implementation did not get silently swept into "fixed":

- **R3's sibling site is still open.** The same function
  (`_generate_group_tool_reply`) that R3 guards against an empty-but-present
  `tool_calls` list has a second, unguarded site: `messages=[]` still raises
  `IndexError` (same bug class as R4, but no patch script covers this one).
  Shipped as `test_empty_history_sibling_site_is_still_unguarded`, an
  `xfail(strict=True, raises=IndexError)` - it will flip to a loud failure
  the day this gets fixed, forcing the test to be updated rather than
  quietly starting to pass.
- **R4's fifth guarded site doesn't bite.** `check_termination_and_human_reply`
  has the fork's guard *and* a pre-existing upstream guard a few lines below
  it; reverting just the fork's copy still returns `(False, None)` because
  upstream's own guard catches it. The behavioural test still exists (it's
  real behaviour worth pinning), but the actual regression protection for
  that one site is a source-marker count
  (`test_five_fork_guards_and_six_total_present`), not a bite check.
- **R5's burst case is still open.** A run of tool messages longer than the
  window (e.g. one assistant turn issuing many tool calls at once) isn't
  handled by the agreed fix: `ToolSafeMessageHistoryLimiter` only trims
  forward, so it returns a first-message-only (or, without
  `keep_first_message`, empty) history instead of extending the window
  backwards - see `docs/prompt_caching_plan.md` Phase 3 ("cache-friendly
  history window"), which is expected to fix this. Shipped as
  `test_burst_should_extend_window_backwards`, an
  `xfail(strict=True, raises=AssertionError)` - it will flip to a loud
  failure once Phase 3 lands, forcing the test (and the characterization
  tests next to it) to be updated together, not silently start passing.

### `bite_check.py`

Not collected by pytest (no `test_` prefix). Run it directly:

```bash
python tests/regression/bite_check.py
```

It loads pre-fix module/source snapshots straight from git history
(`_baseline.py`: ag2 commit `385340d4` for R1/R3/R4, this repo's own commit
`5502d23^` for R5's registration check) and re-runs the *exact same*
assertions the live tests use against them, confirming each guarded fix
actually fails without it - rather than a hand-reverted file and a manual
pytest run. Paste its output into the commit message as the "bites: yes"
evidence.

Exit codes:

| Code | Meaning |
|---|---|
| `0` | Every row matched its expected outcome, nothing skipped. Evidence is complete - safe to cite as "bites: yes". |
| `1` | At least one row's outcome didn't match what it was declared to expect - either a fix stopped biting, an expected non-bite started biting, or a check raised an exception type it didn't declare (reported as `ERROR (unexpected exception type)`, which usually means a bug in the check itself, not in the code under test). |
| `2` | No failures, but at least one row was `SKIP`ped - usually because the sibling `ag2` checkout (`$AG2_FORK_DIR`, default `../ag2`) isn't present. Evidence is **incomplete**, not confirmed; do not cite it as "bites: yes" until it's re-run clean. |

## Separate from this suite: evaluations

Prompt and model changes are checked by re-running a small fixed evaluation
set (replica-trick log coefficient, BGMS −¼ log N, INSPIRE validation),
with success rates over repeated runs. These need real API calls, so they
cost money; they are the natural use of programme credits.
