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

## [Unreleased] - continued (hep-theory agent routing validation)

### Upstream fixes (cmbagent — routing gaps preventing custom agents from ever being selected)

Confirmed via a real test task (replica-trick heat-kernel derivation +
literature search, designed to need all three hep-theory agents) that ran to
completion with none of them invoked. Root-caused to three separate,
independent `Literal` type constraints that gate which agent names an LLM is
even allowed to select — none of them included `inspirehep_context`,
`cadabra_context`, or `derivation_checker`, so no amount of prompt tuning
could have worked around this; the schemas rejected the names outright.

- `cmbagent/agents/planning/planner_response_formatter/planner_response_formatter.py`:
  `sub_task_agent: Literal[...]` — the actual root gate. The planner's own
  structured-output schema restricted which agent a plan step could be
  assigned to; even with everything else fixed, the plan itself could never
  name our three agents. Added them to the Literal. See
  `patch_planner_sub_task_agent.py`.
- `cmbagent/functions/status.py`: `record_status`'s `agent_for_sub_task:
  Literal[...]` (one occurrence) and `agent_transfer_map` (four identical
  copies across `_initialize_transfer_flags`,
  `_determine_next_agent_human_in_loop`, `_determine_next_agent_default`, and
  one more nested in a formatting/reset method) — even with a plan step
  correctly assigned to one of our agents, `controller`'s own routing
  mechanism had no schema slot or transfer-flag mapping for them. Fixed all
  five locations. See `patch_status_agent_routing.py`.
- `cmbagent/functions/planning.py`: `create_record_plan_constraints`'s
  `needed_agents: List[Literal[...]]` (plan_setter's own tool function) — same
  gap, one level earlier in the pipeline (plan_setter declares which agents
  are "allowed" for the whole plan before the planner even runs). Also
  contained a **separate, genuine pre-existing fragility unrelated to our
  agents**: the function calls `get_agent_from_name()` unconditionally on
  every LLM-selected agent name with no check that it's actually registered
  in the session's `agent_list`; `get_agent_from_name()` calls `sys.exit()`
  on a miss. Confirmed via a real crash: `plan_setter` selected
  `"classy_context"` (a legitimate Literal option, present in the schema
  since the original cosmology-focused version of cmbagent, but never added
  to our `agent_list`) for a black-hole-entropy task where it's irrelevant,
  killing the entire process. Fixed both: added our three agents to the
  Literal, and made the lookup skip (with a printed warning) any selected
  name that isn't actually registered, rather than crashing. This second fix
  is a general robustness improvement, not hep-theory-specific — any task
  where `plan_setter` guesses an unregistered agent would previously have
  hard-crashed the whole run. See `patch_plan_setter_agent_lookup.py`.

### Upstream fixes (cmbagent — unpopulated template placeholders)

- `cmbagent/agents/inspirehep_context/inspirehep_context.yaml`,
  `cadabra_context/cadabra_context.yaml`, `derivation_checker/
  derivation_checker.yaml`: all three prompts contained self-referencing
  template placeholders (`{inspirehep_context}`, `{cadabra_context}`, and
  `derivation_checker.yaml` additionally referenced both `{inspirehep_context}`
  and `{current_code_output}`) intended for actual RAG-retrieved content or
  executed-code output that nothing in this workflow populates — flagged as a
  known gap in the original README (`apis/inspirehep_search.py` was never
  implemented). AG2's system-message templating calls
  `template.format(**context)`, which raises `KeyError` the instant any
  agent referencing an unpopulated key is actually invoked. Confirmed via
  real crashes on each agent's first genuine invocation. Removed the
  unpopulated placeholder blocks from the YAML files directly. See
  `patch_remove_unpopulated_placeholders.py` (note: the first attempt at this
  patch introduced its own bug — an unindented marker comment broke YAML
  block-scalar parsing; fixed separately via
  `patch_fix_yaml_marker_indentation.py`).

### Upstream fix (cmbagent_autogen — durable fix for the whole placeholder-crash class)

- `autogen/oai/client.py`: `OpenAIWrapper.instantiate` used
  `template.format(**context)`, raising `KeyError` on any missing key.
  Rather than continuing to find and remove unpopulated placeholders one
  crash at a time (four found and fixed above, with no guarantee that's all
  of them), patched the actual chokepoint: missing context keys now resolve
  to an empty string via `template.format_map()` with a dict subclass
  overriding `__missing__`, rather than raising. This is a durable fix for
  the entire class of bug, not specific to our three agents — any future
  agent prompt referencing a not-yet-populated context variable will now
  degrade gracefully instead of crashing the whole run. See
  `patch_safe_template_format.py`.

### Validation — confirmed working end-to-end

Task: "Derive the leading-order correction to the Bekenstein-Hawking entropy
from a single free scalar field via the replica trick, and identify which
recent (2020 or later) papers established the universality of this log-area
correction coefficient across different matter content." (deliberately
designed to require literature search, symbolic tensor/heat-kernel
derivation, and a verification step — the three specialties of our new
agents.)

Result: all three agents ran, each doing genuinely specialized work matching
their design intent:
- `inspirehep_context` performed an honest literature search and explicitly
  reported that it could **not** confirm a specific 2020+ paper establishing
  cross-matter-content numerical universality — flagging this as an open gap
  rather than fabricating a citation, exactly the behavior the prompt's
  "established vs. contested" framing was designed to produce.
- `cadabra_context` produced a substantive Fursaev–Solodukhin conical-defect
  heat-kernel derivation (Seeley–DeWitt coefficient, distributional curvature
  identities, Weyl/Ricci decomposition) — real, non-trivial physics content.
  Note: this step was very token-heavy (~420K tokens in one step, across
  several truncation/continuation cycles) — worth revisiting for cost control
  in a future session (e.g. splitting the derivation across multiple smaller
  steps, or a stricter output-length instruction).
- `derivation_checker` was invoked by `controller`'s own discretionary
  routing (`OnCondition`) even though the final plan only explicitly assigned
  `researcher` to the verification/synthesis step — confirming both the
  plan-level and controller-discretion pathways into these agents work
  independently. It issued a genuine **FAIL** verdict, correctly catching
  that the final synthesis vaguely gestured at "2020+ literature" without any
  actual arXiv IDs, directly contradicting `inspirehep_context`'s own honest
  Step 1 finding that no such paper could be confirmed — precisely the
  silent-overconfidence failure mode (cf. arXiv:2604.25345, "Plausible but
  Wrong") the `derivation_checker` prompt was hardened against.

This is the first fully successful end-to-end validation of the hep-theory
extension on a task that genuinely exercises all three custom agents.

## [Unreleased] - continued (OpenRouter/DeepSeek experiment)

### Upstream fix (cmbagent)

- `cmbagent/utils/utils.py`: `clean_llm_config` strips `base_url` from any
  per-agent config with `api_type == 'openai'` unless the model name is
  registered in `local_llm_urls` — a safety check meant to prevent stale
  `base_url` settings from leaking in, that didn't account for OpenRouter (a
  legitimate custom-endpoint cloud provider, not "local"). Confirmed via a
  real failure: a DeepSeek-V4-Pro config with a correct OpenRouter API key
  and `base_url` got silently stripped of `base_url`, causing the request to
  fall through to OpenAI's default endpoint and fail with an auth error
  against the (invalid, for OpenAI) OpenRouter key. Fixed by registering the
  DeepSeek model slugs in `local_llm_urls` (the only thing
  `clean_llm_config` actually checks — works regardless of whether the model
  config was built via `get_model_config`'s dict pass-through or the
  `local_llm_urls` string-lookup path). See
  `patch_register_openrouter_models.py`. To add further OpenRouter models
  later, register them the same way: `local_llm_urls["provider/model-slug"]
  = "https://openrouter.ai/api/v1"`.

### Extension — OpenRouter integration path (confirmed working, no code changes needed)

`get_model_config` already supports a full config-dict pass-through (checked
first, before any string-based provider-detection logic), so **any**
`*_model` parameter accepted by `deep_research()` — `planner_model`,
`engineer_model`, `researcher_model`, `cadabra_context_model`, etc. — can take
a raw dict instead of a model-name string:

```python
def _openrouter_config(model_slug):
    return {
        "model": model_slug,
        "api_key": os.getenv("OPENROUTER_API_KEY"),
        "base_url": "https://openrouter.ai/api/v1",
        "api_type": "openai",
    }
```

This required zero patches to actually route requests to OpenRouter once the
`local_llm_urls` fix above was in place.

### Findings — DeepSeek V4 Pro / V4 Flash reliability in this pipeline (tried and reverted)

Attempted routing all nine agent roles through DeepSeek V4 Pro (reasoning-
critical roles: engineer, researcher, plan_reviewer, inspirehep_context,
cadabra_context, derivation_checker) and V4 Flash (lighter roles: planner,
idea_maker, idea_hater, camb_context) to reduce cost, motivated by
`cadabra_context`'s ~420K-token Claude run in the prior session. Result:
reverted back to all-Claude after one test run surfaced two problems, both
likely responsible for the run being *more* expensive than the all-Claude
baseline despite lower headline per-token pricing:

1. **`planner` on DeepSeek V4 Flash stopped assigning any of the three custom
   hep-theory agents to plan steps at all**, despite the same explicit
   `plan_instructions` describing them that worked correctly on Claude Haiku
   in every prior run. Reverted to `researcher`/`engineer` for all three
   steps; `inspirehep_context` only appeared in the transcript via
   `controller`'s own discretionary routing, not the plan itself.
2. **`inspirehep_context` on DeepSeek V4 Pro produced malformed/near-empty
   structured output several times in a row** (multiple 4-character
   responses), triggering expensive retry loops — 164,994 prompt tokens
   consumed by that single agent in one step, mostly retry waste rather than
   productive work. This looks like a `response_format`/JSON-schema
   compliance gap between DeepSeek's OpenAI-compatible endpoint and the
   strict Pydantic-based formatters this pipeline relies on throughout, not
   something fixable via prompting.

Net conclusion: model-swapping for cost control is technically fully
supported (see integration path above) and worth revisiting, but should be
done **one role at a time** rather than a full reconfiguration, so a
reliability regression in one role doesn't get conflated with the others —
tonight's all-at-once swap made it hard to isolate exactly which change
caused the problem until the transcripts were inspected directly. Lower-risk
alternatives to try first for cost control without changing providers:
capping `cadabra_context`'s response length or splitting long derivations
across multiple plan steps (its expensive run was mostly repeated
truncation/continuation cycles, not one clean pass), and lowering
`max_rounds_control` for tasks that don't need much back-and-forth.

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
