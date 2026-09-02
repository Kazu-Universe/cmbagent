
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
