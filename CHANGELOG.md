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
