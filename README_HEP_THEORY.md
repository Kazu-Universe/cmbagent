# CMBAgent → HEP-Theory Extension: Sketch

Confirmed against the actual `cmbagent` PyPI package (v0.0.1.post63) rather than
assumed. Each domain plugin (`camb`, `classy_sz`, `cobaya`, `planck`, ...) is a
folder under `cmbagent/agents/<name>/` containing a `<name>.py` (thin `BaseAgent`
subclass) and a `<name>.yaml` (the actual prompt, with template variables like
`{current_plan_step_number}` interpolated at runtime by the Planning & Control
loop). Anthropic models are already supported per-agent via `agent_llm_configs`
(see `cmbagent/utils.py`, `get_model_config`) — no fork needed just to use Claude
or Fable models, only to add new *agents*.

## What's in this sketch

- `pyproject_hep_theory_extra.toml` — new `[hep-theory]` install extra
  (sympy, einsteinpy, cadabra2, INSPIRE/arXiv API clients).
- `agents/inspirehep_context/` — literature retrieval agent, tuned to INSPIRE-HEP
  and arXiv hep-th/gr-qc, that explicitly separates settled vs. contested claims
  (important given how much of the information-paradox literature is disputed) and
  cites arXiv/INSPIRE IDs rather than paraphrasing loosely.
- `agents/cadabra_context/` — symbolic tensor algebra context agent (Cadabra2 /
  SymPy / EinsteinPy), analogous to `camb_context` but for GR/string tensor
  calculus. Explicitly defers to your existing xAct/Mathematica + Wolfram Engine
  setup for heavy compactification computations rather than forcing a weak
  pure-Python translation.
- `agents/derivation_checker/` — critique agent standing in for the numerical
  goodness-of-fit check CMBAgent normally gets from data-fitting tasks. Runs a
  fixed checklist (dimensional consistency, correct limits, symmetry/consistency,
  sign conventions, citation grounding) and returns PASS/FAIL/CAVEATS.
- `run_hep_theory_example.py` — wiring example with a concrete benchmark task
  (Page curve derivation) that has a known answer, so you can tell whether the
  system is doing correct physics before trusting it on open problems.

## What this sketch does *not* do

- It doesn't touch `cmbagent.py`'s `init_agents()` / `hand_offs.py` — you'll need
  to register the three new agent names there (and in whatever glob/discovery
  logic picks up `agents/*` folders) so the planner knows they exist and when to
  route to them. I haven't verified the exact discovery mechanism beyond seeing
  that `agent_classes` gets built from `self.agent_list`.
- It doesn't implement the actual INSPIRE-HEP fetch (`apis/inspirehep_search.py`)
  — that's a plain REST call to `https://inspirehep.net/api/literature`, but I'd
  rather build it against the real response schema than guess at one.
- It doesn't wire Claude Code as a *replacement* execution backend (vs. just
  setting `engineer`'s model to a Claude model within AG2's existing executor).
  That's a bigger change — worth doing once the smaller extension is working, but
  probably not the first thing to build.

## Suggested order of operations

1. Fork `cmbagent`, add the `[hep-theory]` extra, get it installing cleanly.
2. Drop in `inspirehep_context` first (pure literature retrieval, lowest risk) and
   confirm the planner routes to it correctly.
3. Add `cadabra_context` + let `engineer` attempt the Page curve benchmark task.
4. Add `derivation_checker` last, once you have something for it to critique.
5. Only then consider swapping the execution backend for Claude Code.

Happy to build out any one of these pieces for real — the INSPIRE-HEP fetch
function or the `hand_offs.py` routing changes are probably the highest-value
next step since everything else depends on them actually being reachable.
