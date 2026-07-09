# Changelog — CMBAgentForHEPTH_wClaude

This fork extends CMBAgent (https://github.com/CMBAgents/cmbagent) for
high-energy theory / string theory / black hole information paradox research.
Entries are split into **Upstream fixes** (bugs in the base repo, unrelated to
this extension — candidates for upstream PRs, pending confirmation against
true `CMBAgents/cmbagent main`) and **Extension** (this fork's actual purpose).

## [Unreleased]

### Upstream fixes
- `mistralai` 2.x removed the flat top-level `from mistralai import Mistral,
  DocumentURLChunk` that `cmbagent/utils/ocr.py` depends on (package
  restructured under `mistralai/client/` around the 2.0 line). Pinned to
  `mistralai==1.9.2`, the last version with both the flat import and
  `DocumentURLChunk` support.
- `hand_offs.py`: `agents['plan_recorder'].agent.handoffs.add_after_works(...)`
  — no such method on the installed `Handoffs` class (`cmbagent_autogen`
  0.0.91.post11). Renamed to `add_context_conditions`, matching the pattern
  already used for `controller.agent.handoffs.add_llm_conditions(...)`
  elsewhere in the same file.
- `hand_offs.py`: `OnContextCondition(condition=None, # Default fallback)` —
  `condition` no longer accepts `None` as a "match anything else" default in
  the installed pydantic model. Replaced with the explicit logical complement
  (`${feedback_left} != 0`) of the sibling condition, preserving identical
  control flow.
- `pyproject.toml`: unrelated to CMBAgent's own code — self-inflicted during
  the hep-theory extra merge (duplicate `[project.optional-dependencies]`
  table). Noted here since it blocked every `pip install` until fixed.

### Extension — hep-theory agents
- Added `inspirehep_context`: literature retrieval agent for INSPIRE-HEP /
  arXiv hep-th, explicitly separating established vs. contested claims.
- Added `cadabra_context`: symbolic tensor/index algebra context agent
  (Cadabra2 / SymPy / EinsteinPy), defers to existing xAct/Mathematica setup
  for heavy compactification work.
- Added `derivation_checker`: critique agent running a fixed checklist
  (dimensional consistency, limiting behavior, symmetry, sign conventions,
  citation grounding, degeneracy/under-determination, silent scope
  narrowing) — the last two added specifically in response to failure modes
  documented in arXiv:2604.25345 ("Plausible but Wrong").
- Registered all three in `hand_offs.py`'s `core_agent_names`,
  `simple_handoffs` (routed to `controller`), and `controller_conditions`.
- Added `[hep-theory]` extra to `pyproject.toml` (sympy, einsteinpy,
  requests, arxiv, networkx — cadabra2 excluded, install separately via
  conda-forge if needed).
- Model assignment (`agent_llm_configs`): Fable 5 for planner/idea-generation
  roles, Claude Sonnet for engineer/critique roles, Claude Haiku for
  mechanical formatters. Ten agents in `default_agent_llm_configs` are
  hardcoded to OpenAI models regardless of `default_llm_model` and needed
  individual overrides — see `run_hep_theory_example.py` for the full dict.

## Environment notes
- Python 3.12, `.venv` at repo root (`pip install -e ".[hep-theory]"`).
- Requires `ANTHROPIC_API_KEY`. `OPENAI_API_KEY` not set in this environment
  by design — every OpenAI-defaulting agent above has an explicit override.

## [Unreleased] - continued (deep_research end-to-end debugging session)

### Upstream fixes (cmbagent_autogen / autogen dependency)
- `autogen/oai/anthropic.py`: `tool_choice` translation. `cmbagent_autogen`'s swarm
  handoff mechanism builds forced tool_choice in OpenAI's schema
  (`{"type": "function", "function": {"name": X}}`) unconditionally; Anthropic's
  actual schema is `{"type": "tool", "name": X}`. Without translation, any agent
  using a forced tool_choice (terminator, plan_recorder, review_recorder, etc.)
  gets a 400 from the Anthropic API. Patched via `patch_anthropic_tool_choice.py`.
- `autogen/oai/anthropic.py`: `top_p` rejected outright by some Claude models
  (e.g. claude-fable-5). Fixed by setting `default_top_p = None` at source
  (`cmbagent/utils/utils.py`) — the Anthropic wrapper already drops the key
  from the request when `None`. Patched via `patch_default_top_p.py`.
- `autogen/agentchat/group/group_tool_executor.py`: `_generate_group_tool_reply`
  checked `if "tool_calls" in message:` (key presence) instead of truthiness.
  Anthropic-backed replies with no actual tool call still get `tool_calls: []`
  (present but empty), causing `UnboundLocalError` on `tool_message` (assigned
  only inside a `for` loop that never runs for an empty list). Fixed via
  `message.get("tool_calls")` truthiness check.
- `autogen/agentchat/conversable_agent.py`: five separate unguarded
  `message = messages[-1]` occurrences (`generate_tool_calls_reply`,
  `generate_function_call_reply`, and others) crash with `IndexError` when an
  agent's per-sender message history is empty — reliably triggered whenever
  `max_rounds` is hit and the framework forces a termination handoff to an
  agent it has no prior history with. Patched with an early
  `if not messages: return False, None` guard at each location, via
  `patch_all_empty_messages_guards.py` (instrumented with unique GUARD-ID
  prints during debugging via `patch_identify_guard_locations.py` — safe to
  remove once stable).
- `autogen/oai/anthropic.py`: `oai_messages_to_anthropic_messages` crashed with
  `IndexError` on `processed_messages[-1]["role"]` when the list was empty
  (same root cause as above, different code path). Fixed by treating an empty
  list as trivially not ending in `"user"`, appending the continue message
  instead of crashing. Patched via `patch_anthropic_empty_messages.py`.

### Upstream fixes (cmbagent itself)
- `cmbagent/agents/planning/plan_recorder/plan_recorder.py`: **root cause of a
  major bug.** `plan_recorder`'s custom `_record_plan_reply` (a non-LLM Python
  reply function) was registered via `register_reply(..., position=0)`
  alongside an `OnContextCondition`-based routing block on the *same* agent.
  AG2's swarm framework runs `OnContextCondition` checks "before any other
  reply function" for whichever agent owns them — confirmed via
  `autogen/agentchat/group/group_utils.py`. Since our earlier fix for the
  `condition=None` crash (see below) made the two routing branches mutually
  exhaustive, the context-condition check *always* produced an immediate
  routing decision and *never* fell through to let `_record_plan_reply`
  actually run — meaning `final_plan`, `proposed_plan`, and
  `number_of_steps_in_plan` were never set, despite the routing itself
  appearing to work correctly (it was actually being driven by
  `review_recorder`'s own context updates as a side effect).
  **Fix:** created a new pass-through agent, `plan_router`
  (`cmbagent/agents/planning/plan_router/`), to host the
  `OnContextCondition` routing instead. `plan_recorder` now hands off to it
  unconditionally (`set_after_work`), so its own Python logic actually
  executes, and `plan_router` — which has no competing custom reply logic of
  its own — makes the terminator-vs-plan_reviewer decision using the
  now-updated context. See `patch_plan_recorder_routing.py`.
- `cmbagent/hand_offs.py`: two pre-existing bugs, present in upstream `main`
  (confirmed against `CMBAgents/cmbagent` origin, not a private fork) —
  `add_after_works` (nonexistent method; correct name is
  `add_context_conditions`) and `OnContextCondition(condition=None, ...)` (no
  longer valid in the installed pydantic model; replaced with the explicit
  logical complement of the sibling condition). Both fixed earlier in this
  session, documented above under the original CHANGELOG entries.
- `cmbagent/workflows/deep_research.py`: **second major root cause.** The
  per-step loop only loaded the plan file's actual `sub_task`/`bullet_points`/
  `sub_task_agent` for `step == 1`; for every subsequent step, it only set
  `agent_for_sub_task` (inherited stale from the previous step's context) and
  never set `current_sub_task`/`current_instructions` from the plan file at
  all. Framework-level step advancement (via `record_status`'s
  `_determine_next_agent_default`) only handles *routing* (which agent goes
  next), never re-derives the next step's task text from the plan — that
  responsibility apparently was expected to happen elsewhere but didn't. Net
  effect: every step after the first showed frozen Step-1 task text, verbatim,
  regardless of what the actual plan said. Fixed by explicitly loading
  `plan_input[step - 1]` for every step and setting `agent_for_sub_task`,
  `current_sub_task` (from `sub_task`), and `current_instructions` (built from
  `bullet_points`, since no separate `instructions` key exists in
  `final_plan.json`). See `patch_deep_research_step_advance.py`. Confirmed
  fixed: Step 2 and Step 3 now correctly show their real, distinct
  sub-tasks/agents instead of Step 1's repeated verbatim.

### Extension — model configuration
- `cmbagent/utils/utils.py`: `default_agents_llm_model` replaced with
  all-Anthropic defaults (was hardcoded to OpenAI models for 10 agents,
  silently ignoring `default_llm_model`); added `inspirehep_context`,
  `cadabra_context`, `derivation_checker` entries. See
  `patch_default_agents_llm_model.py`.
- `cmbagent/workflows/deep_research.py`: added `inspirehep_context_model`,
  `cadabra_context_model`, `derivation_checker_model` parameters, mirroring
  the existing `camb_context_model` pattern, so the hep-theory agents get
  proper model configs in the control phase. See `patch_deep_research.py`.
- Temporary debug-cost measure: `claude-fable-5` swapped to
  `claude-haiku-4-5-20251001` for `planner`/`idea_maker`/`idea_hater` during
  active debugging (`patch_debug_cheap_models.py`) — swap back once stable.

### Known remaining items
- Diagnostic print statements (`>>> DIAGNOSTIC plan_recorder: ...`,
  `>>> GUARD-ID: ...`) are still present in the patched dependency and
  `plan_recorder.py`. Harmless but noisy; remove or gate behind
  `cmbagent_debug` once confirmed stable across a few more runs.
- End-to-end pipeline has not yet been validated on a task that exercises
  `inspirehep_context`, `cadabra_context`, or `derivation_checker` — the
  Bekenstein-Hawking dimensional-analysis test task was fully served by
  `engineer`/`researcher` alone. Next validation step.
