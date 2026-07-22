"""
Temporary patch: swaps claude-fable-5 -> claude-haiku-4-5-20251001 in
default_agents_llm_model, for cheap debugging runs while the pipeline is still
being fixed. Easily reversible - see revert_fable5_debug_swap.py (or just
re-run the original default_agents_llm_model patch once debugging is done).

Run once from the repo root:
    python patch_debug_cheap_models.py
"""

import re

path = "cmbagent/utils/utils.py"
marker = "hep-theory fork: TEMP cheap-model debug swap"

with open(path, "r") as f:
    content = f.read()

if marker in content:
    print(f"Already patched: {path}")
    raise SystemExit(0)

if "claude-fable-5" not in content:
    raise SystemExit("No 'claude-fable-5' found in file - nothing to swap.")

count = content.count("claude-fable-5")
content = content.replace("claude-fable-5", "claude-haiku-4-5-20251001")

# Add a marker comment near the top of default_agents_llm_model so this is
# easy to find and revert later.
content = content.replace(
    "default_agents_llm_model =",
    "# hep-theory fork: TEMP cheap-model debug swap - fable-5 -> haiku for now,\n"
    "# swap back once the pipeline is confirmed working end-to-end.\n"
    "default_agents_llm_model =",
    1,
)

with open(path, "w") as f:
    f.write(content)

print(f"Patched: {path}")
print(f"Replaced {count} occurrence(s) of claude-fable-5 with claude-haiku-4-5-20251001")
