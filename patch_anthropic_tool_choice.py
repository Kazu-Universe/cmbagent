"""
One-time patch (v2, single-line match): translates cmbagent_autogen's OpenAI-style
forced tool_choice ({"type": "function", "function": {"name": X}}) into Anthropic's
actual schema ({"type": "tool", "name": X}) at the point it reaches the client.

Run once after any fresh `pip install`/venv rebuild:
    python patch_anthropic_tool_choice.py
"""

import autogen.oai.anthropic as anthropic_module

path = anthropic_module.__file__
marker = "hep-theory fork fix"

with open(path, "r") as f:
    lines = f.readlines()

if any(marker in line for line in lines):
    print(f"Already patched: {path}")
    raise SystemExit(0)

target_substr = 'anthropic_params["tool_choice"] = validate_parameter(params, "tool_choice", dict'

matches = [i for i, line in enumerate(lines) if target_substr in line]

if len(matches) != 1:
    print(f"Expected exactly 1 match for the assignment line, found {len(matches)}.")
    print("Matching line(s):")
    for i in matches:
        print(f"  line {i+1}: {lines[i]!r}")
    raise SystemExit(
        "Aborting - file structure differs from what this patch expects. "
        "Paste the output above so the patch can be adjusted."
    )

idx = matches[0]
indent = lines[idx][: len(lines[idx]) - len(lines[idx].lstrip())]

insertion = [
    f'{indent}# hep-theory fork fix: cmbagent_autogen builds tool_choice in OpenAI\'s\n',
    f'{indent}# schema unconditionally: {{"type": "function", "function": {{"name": X}}}}.\n',
    f'{indent}# Anthropic\'s forced-single-tool schema was never implemented here.\n',
    f'{indent}# Without this translation, any agent using a forced tool_choice\n',
    f'{indent}# (terminator, plan_recorder, review_recorder, etc.) gets a 400 from\n',
    f'{indent}# the Anthropic API when backed by a Claude/Fable model.\n',
    f'{indent}tc = anthropic_params.get("tool_choice")\n',
    f'{indent}if isinstance(tc, dict) and tc.get("type") == "function":\n',
    f'{indent}    fn = tc.get("function", {{}})\n',
    f'{indent}    name = fn.get("name") if isinstance(fn, dict) else None\n',
    f'{indent}    if name:\n',
    f'{indent}        anthropic_params["tool_choice"] = {{"type": "tool", "name": name}}\n',
]

new_lines = lines[: idx + 1] + insertion + lines[idx + 1 :]

with open(path, "w") as f:
    f.writelines(new_lines)

print(f"Patched: {path} (inserted after line {idx + 1})")
