
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
