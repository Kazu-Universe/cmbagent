# Prompt caching for the hep-th CMBAgent: patch plan

Status: plan for review (6 October 2026). No code written yet.

## 1. Why

Run folders through 1 October: about 308M input tokens against 8M output, an
estimated $693 in total. 97% of the cost is input, mostly context re-sent on
every agent turn. Three long, tool-heavy runs are 77% of the cost (literature
scan $269, AdS localization match $135, crossed product $125).

Prompt caching bills repeated prefixes at a fraction of the input price:

| | Multiplier on base input price |
|---|---|
| Cache read | 0.1× (0.05× Opus 5.5; 0.025× Fable 5.1) |
| Cache write, 5-minute TTL | 1.25× |
| Cache write, 1-hour TTL | 2× |

Rough effect: if 80% of input becomes cache reads at 0.1×, input cost falls
to about 0.3 of today's, write overhead included. That is an estimate to be
measured, not a promise.

## 2. How Anthropic caching works (facts the design relies on)

- The cache covers the full **prefix** in order: tools, system, then
  messages, up to the block marked with `cache_control`.
- **Automatic caching**: one top-level `cache_control` field; the API places
  the breakpoint on the last cacheable block and moves it as the conversation
  grows.
- **Explicit breakpoints**: `cache_control` on individual blocks, up to 4 per
  request; combinable with automatic caching.
- **Minimum cacheable length**: 512 tokens for Fable 5.1, Opus 5.5, Opus 5,
  Sonnet 5.5 and Fable 5. Shorter prefixes are processed without caching,
  with no error. (Check the current figures for Sonnet 5 and Haiku 4.5; older
  docs gave 4,096 for Haiku 4.5, so the formatters may not benefit.)
- A 20-block lookback window applies when matching earlier breakpoints.
- Responses report `cache_creation_input_tokens` and
  `cache_read_input_tokens` alongside `input_tokens`.

## 3. Obstacles specific to this pipeline

1. **The sliding history window breaks the prefix.** `ToolSafeMessageHistoryLimiter`
   keeps the last 20 messages (70 for `inspirehep_context`). Once a
   conversation exceeds the window, every new message shifts the start of
   the window, so the message prefix changes on every turn and nothing after
   the system prompt can be read from cache.
2. **System messages may change within a step.** Agent prompts are formatted
   with context variables (`{current_status}` and others). If any of these
   change between turns inside a step, the system block changes and the whole
   cache is invalidated.
3. **Time between calls.** An agent's next call may come more than 5 minutes
   later (for example after a long code execution), so its 5-minute cache
   entry may have expired.
4. **Cost accounting.** The ag2 client prices `input_tokens` at the full rate
   and ignores cache fields, and CMBAgent's cost reports record only prompt
   and completion tokens. Without fixing both, caching savings would be
   invisible (or mispriced) in `summarize_runs.py`.

## 4. Phases

**Phase 0: measure (no behaviour change).** Log per call: agent, model,
`input_tokens`, `cache_creation_input_tokens`, `cache_read_input_tokens`,
output tokens, and a hash of the system block. Run one cheap known task. This
tells us how often system prompts change within a step (obstacle 2) and how
long the gaps between an agent's calls are (obstacle 3).

**Phase 1: automatic caching.** In the ag2 Anthropic client, add top-level
`cache_control={"type": "ephemeral"}` to every Claude request, behind a
config switch (`prompt_caching: true` by default for Claude models, off for
others). If the installed SDK does not accept the top-level field, pass it
via `extra_body`. Alone, this caches tools and system prompts, and full
conversations until they exceed the history window.

**Phase 2: correct cost accounting.** Price cache reads and writes in the ag2
client's cost calculation (per-model multipliers above), and add
cache-read and cache-write token columns to CMBAgent's cost reports and to
`summarize_runs.py`. After this, the logged "Cost ($)" is trustworthy.

**Phase 3: cache-friendly history window (the main gain).** Replace the
sliding window with truncation in jumps: let the history grow to `W_max`,
then cut back to `W_min` (for example 30 → 15, and 90 → 50 for
`inspirehep_context`), always on a tool-safe boundary. Between cuts the prefix
only grows, so almost every turn reads from cache; each cut costs one cache
write. Average context is somewhat larger than with a fixed window, but at
0.1× for cached input it is far cheaper. The burst case (a run of tool
messages longer than the window) must keep the agreed fix: extend the window
backwards rather than return an empty or first-message-only history.

**Phase 4: stable system prompts (only if Phase 0 shows churn).** Move
fields that change within a step out of the system message into a short
trailing message, so the system block stays identical across turns.

**Phase 5: TTL tuning (only if Phase 0 shows long gaps).** Use the 1-hour TTL
for heavy agents whose calls are more than 5 minutes apart. A 1-hour write
costs 2× and pays off after two reads.

## 5. Where the code lives

| Phase | File | Notes |
|---|---|---|
| 0, 1, 2 | ag2 fork: `autogen/oai/anthropic.py` | Request params, usage logging, cost calculation; as a commit in the fork or a `patch_*.py` script |
| 2 | `cmbagent/cmbagent.py` (cost report), `summarize_runs.py` | New token columns |
| 3 | `cmbagent/hand_offs.py` (`ToolSafeMessageHistoryLimiter`) | Hysteresis window |
| 4 | agent YAMLs, `deep_research.py` | Only if needed |

A Claude Code task (multi-file, real source), done on a branch in plan mode.

## 6. Tests (offline, tests/regression/)

- **C1**: with caching on, the request sent to a mocked Anthropic client
  carries `cache_control`; with the switch off, or for a non-Claude model, it
  does not.
- **C2**: cost calculation from a mocked usage object with cache reads and
  writes matches a hand computation for each routed model.
- **C3**: hysteresis limiter. Between cuts the kept history is a strict
  prefix-extension of the previous turn's; after a cut it is ≤ `W_min` and
  starts on a tool-safe boundary; tool-use/tool-result pairs are never split;
  the burst case returns a non-empty, extended window.
- **C4**: the existing R5 limiter test still passes (or is updated together
  with C3, with the reason recorded).
- Bite check for each, as for the rest of the suite.

## 7. Evaluation (small, real API calls)

1. **Cheap A/B**: re-run the Susskind–Uglum check (about $3 last time) with
   caching off and on. Compare input, cache-read and cache-write tokens, cost,
   and the checker's verdict (should be unchanged).
2. **Heavy check**: re-run only step 1 of the fuzzy dP literature scan (the
   costliest kind of step) with caching on, and compare with its share of the
   1 October run.
3. **Pass condition**: cache-read share of input above 70% on the heavy step,
   cost per step down by at least half, no change in verdict quality.

Expected cost of the whole evaluation: tens of dollars.

## 8. Risks

- **Silent misses**: caching never errors, it just doesn't hit. Phase 0
  logging and the cache-read share are the guard.
- **Behaviour**: caching does not change model outputs; the history-window
  change in Phase 3 does change what agents see, so the A/B verdict check
  matters.
- **SDK support** for the top-level field: check the installed `anthropic`
  version first.
- **Non-Claude paths** (OpenRouter, DeepSeek) are unaffected: the switch is
  per model.
