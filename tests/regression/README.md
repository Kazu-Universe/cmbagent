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
| R5 | History resend (10) | `hand_offs.py` | `ToolSafeMessageHistoryLimiter` on synthetic histories: window respected; first kept message is never a tool result; tool-use/tool-result pairs never split. The five heavy agents are registered with windows 20 / 70 | fixed |
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
   pass. Record "bites: yes" in the commit message.
4. **Run** `pytest tests/regression -q` after every change and after every
   `.venv` rebuild.
5. **Later.** A GitHub Actions workflow running the suite on each push
   (free for a public repository), and `/code-review` on each PR.

## Separate from this suite: evaluations

Prompt and model changes are checked by re-running a small fixed evaluation
set (replica-trick log coefficient, BGMS −¼ log N, INSPIRE validation),
with success rates over repeated runs. These need real API calls, so they
cost money; they are the natural use of programme credits.
