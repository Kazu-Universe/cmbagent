"""
One-time patch: adds inspirehep_context, cadabra_context, and derivation_checker
to deep_research.py's control-phase setup — new function parameters (mirroring
camb_context_model), model config lines, and entries in the agent_llm_configs
dict passed to CMBAgent() during the control/execution phase.

Run once:
    python patch_deep_research.py
"""

import re

path = "cmbagent/workflows/deep_research.py"
marker = "hep-theory fork: added inspirehep_context"

with open(path, "r") as f:
    content = f.read()

if marker in content:
    print(f"Already patched: {path}")
    raise SystemExit(0)

# --- 1. Add function parameters, right after camb_context_model= line ---
param_old = "    camb_context_model=default_agents_llm_model['camb_context'],\n"
param_new = (
    "    camb_context_model=default_agents_llm_model['camb_context'],\n"
    "    # hep-theory fork: added inspirehep_context, cadabra_context, derivation_checker\n"
    "    inspirehep_context_model=default_agents_llm_model['inspirehep_context'],\n"
    "    cadabra_context_model=default_agents_llm_model['cadabra_context'],\n"
    "    derivation_checker_model=default_agents_llm_model['derivation_checker'],\n"
)

if content.count(param_old) != 1:
    raise SystemExit(
        f"Expected exactly 1 occurrence of the camb_context_model parameter line, "
        f"found {content.count(param_old)}. Aborting rather than guessing."
    )
content = content.replace(param_old, param_new, 1)

# --- 2. Add model config lines, right after camb_context_config= line ---
config_old = "    camb_context_config = get_model_config(camb_context_model, api_keys)\n"
config_new = (
    "    camb_context_config = get_model_config(camb_context_model, api_keys)\n"
    "    inspirehep_context_config = get_model_config(inspirehep_context_model, api_keys)\n"
    "    cadabra_context_config = get_model_config(cadabra_context_model, api_keys)\n"
    "    derivation_checker_config = get_model_config(derivation_checker_model, api_keys)\n"
)

if content.count(config_old) != 1:
    raise SystemExit(
        f"Expected exactly 1 occurrence of the camb_context_config line, "
        f"found {content.count(config_old)}. Aborting rather than guessing."
    )
content = content.replace(config_old, config_new, 1)

# --- 3. Add entries to the agent_llm_configs dict passed to CMBAgent() ---
dict_old = "                'camb_context': camb_context_config,\n"
dict_new = (
    "                'camb_context': camb_context_config,\n"
    "                'inspirehep_context': inspirehep_context_config,\n"
    "                'cadabra_context': cadabra_context_config,\n"
    "                'derivation_checker': derivation_checker_config,\n"
)

if content.count(dict_old) != 1:
    raise SystemExit(
        f"Expected exactly 1 occurrence of the camb_context dict entry line, "
        f"found {content.count(dict_old)}. Aborting rather than guessing."
    )
content = content.replace(dict_old, dict_new, 1)

with open(path, "w") as f:
    f.write(content)

print(f"Patched: {path}")
print("Added: inspirehep_context_model, cadabra_context_model, derivation_checker_model params")
print("Added: corresponding *_config lines")
print("Added: corresponding agent_llm_configs dict entries")
