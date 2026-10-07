# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

CMBAgent is a multi-agent system powered by AG2 (formerly AutoGen) for scientific discovery across scientific domains. The system follows a planning and control strategy with specialized agents for different research workflows.

The system uses a two-phase approach:
- **Planning**: A planner and plan reviewer design task execution strategies
- **Control**: Step-by-step execution where sub-tasks are handed to specialized agents

## Key Components

### Core Python Package (`cmbagent/`)
- **Main API**: `cmbagent.one_shot()` - primary function for task execution
- **Agent system**: Specialized agents in `agents/` directory, each with `.py` and `.yaml` configuration
- **Agent types**: Planning, control, coding (engineer, executor), research (researcher, summarizer), hypothesis generation, keyword extraction, and domain-specific templates
- **Context management**: Sophisticated context handling via `context.py` and `hand_offs.py`
- **Remote execution**: `execution/remote_executor.py` - delegates code execution to client

## Common Development Commands

### Python Package
```bash
# Install core only (lightweight)
pip install -e .

# Install with development tools
pip install -e ".[dev]"

# Install with local execution support (if not using remote execution)
pip install -e ".[local]"

# Install everything (all scientific packages)
pip install -e ".[all]"

# Run tests (individual Python scripts in tests/)
python tests/test_one_shot.py
python tests/test_engineer.py
```

## Architecture Details

### Agent System
- Each agent has a Python implementation and YAML configuration
- Agents are specialized for different workflows: engineering, research, planning, execution, hypothesis generation, keyword extraction
- Response formatters handle output formatting for specific use cases
- Controller manages workflow orchestration
- Domain-specific agents in `specialized/` serve as templates for users to add their own

### Multi-Modal Capabilities
- Plot generation capabilities
- File browser with inline image viewing

### Research Capabilities
- Domain-agnostic architecture supporting any scientific field
- Literature search and keyword extraction (`literature.py`, `aas_keyword_finder`)
- Example domain packages provided: materials science, biochemistry, astronomy, data science
- Users can easily add their own domain-specific dependencies in `pyproject.toml`

### Work Directory Structure
Tasks create organized output directories:
```
project_dir/
├── chats/          # Conversation history
├── codebase/       # Generated code
├── cost/           # Cost analysis
├── data/           # Generated data and plots
├── time/           # Timing reports
└── context/        # Context files (.pkl)
```

## Testing
- Tests are individual Python scripts in `tests/` directory
- Run specific test files directly: `python tests/test_<name>.py`
- Tests cover various agents and use cases (engineering, research, plotting, etc.)
- No centralized test runner - tests are designed as standalone demonstrations

## Configuration
- API keys required: `OPENAI_API_KEY`, optionally `ANTHROPIC_API_KEY`, `GEMINI_API_KEY`
- Model configurations in `cmbagent/apis/` (JSON files for different providers)
- Agent configurations in individual `.yaml` files alongside Python implementations

## Key APIs
- `cmbagent.one_shot(task, agent='engineer', model='gpt-4o', work_dir=...)` - Main execution API
- Planning and control via specialized agent orchestration
- WebSocket streaming for real-time UI updates

## hep-theory fork: rules for every change

This fork adds three agents (`inspirehep_context`, `cadabra_context`,
`derivation_checker`), Anthropic-only model routing, and patches to the
`ag2` fork (branch `cmbagent-real-base`) applied inside `.venv` by the
`patch_*.py` scripts. The authoritative history of every fix is in
`CHANGELOG_ADDENDUM*.md`; current state is in `PROJECT_STATUS.md`.

### Working rules
- Sessions start in plan mode (read-only). Do not edit files until asked.
  The PI runs git, pip and pipeline commands himself.
- Every bug fix ships with an offline regression test in
  `tests/regression/` (pytest, no network, LLM client mocked).
- Show the test bites: it must fail with the fix reverted and pass with it.
- Never delete, skip or weaken a test to make it pass.
- Before proposing a commit, run `/code-review` on the diff. Report a
  finding only with a failing test or a concrete reproduction.
- Dependency patches: make the script idempotent (marker string), abort
  without writing if the target text is not found, and record the fix in
  the changelog.

### Known bug classes: check new code against each
1. **Provider schemas differ.** Anthropic forced tool choice is
   `{"type": "tool", "name": X}`, not OpenAI's `{"type": "function", ...}`.
   Opus 5.5, Fable 5.1 and Sonnet 5.5 reject forced tool choice entirely:
   agents that force tool calls (recorders, terminator, controller,
   formatters) must stay on `claude-sonnet-5` / `claude-haiku-4-5`.
2. **Sampling parameters.** Claude 5-generation models reject non-default
   `temperature` / `top_p`. Never send them.
3. **Key presence is not truthiness.** Replies can carry `tool_calls: []`.
   Use `msg.get("tool_calls")`, never `"tool_calls" in msg`.
4. **Empty histories.** Forced termination hand-offs reach agents with no
   history. Guard every `messages[-1]` and `processed[-1]`.
5. **Reply-order shadowing.** `OnContextCondition` runs before custom reply
   functions on the same agent. Host context routing on a separate
   pass-through agent (the `plan_router` pattern).
6. **Per-step state.** Each plan step loads its own `sub_task`, agent and
   instructions from `final_plan.json`; nothing is inherited from the
   previous step's context.
7. **Agent-name allowlists.** A new agent must be added to every
   `Literal[...]`: `planner_response_formatter.sub_task_agent`,
   `status.py` (`agent_for_sub_task` and four `agent_transfer_map`
   copies), `planning.py` (`needed_agents`). Unknown names must warn,
   never `sys.exit`.
8. **Template placeholders.** System messages are `format`ted with the
   context; missing keys now render as empty strings. Do not add
   placeholders that nothing populates.
9. **Naming conventions are hidden contracts.** Step-summary extraction
   used to assume a `<name>_response_formatter` companion. Agents without
   one must be found by their unstripped name.
10. **History resend.** Heavy workers use `ToolSafeMessageHistoryLimiter`
    (window 20; `inspirehep_context` 70). Truncation must never leave a
    tool result at the start of the window.
11. **Output budget.** Claude configs use `max_tokens` 32000 because
    thinking shares the output budget. Treat truncation warnings as bugs.
12. **Thinking blocks first.** Never read `response.content[0].text`;
    select content blocks by type.
13. **Config sanitizers.** `clean_llm_config` strips `base_url` unless the
    model is registered in `local_llm_urls` (needed for OpenRouter).
14. **Interactive pauses.** Worker agents need `human_input_mode="NEVER"`.
15. **Simulated actions.** An agent saying it saved a file proves nothing;
    check the file exists (`researcher_executor` save is unconfirmed).
16. **YAML block scalars.** Inserted marker comments must keep the
    block's indentation.
