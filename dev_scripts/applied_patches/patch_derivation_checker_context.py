"""
One-time patch (v2, line-based): adds {previous_steps_execution_summary} to
derivation_checker's prompt, right after the {current_code_output} line -
found by exact line content match rather than a multi-line block match,
avoiding whitespace-mismatch fragility.

Run once from the repo root:
    python patch_derivation_checker_context.py
"""

path = "cmbagent/agents/derivation_checker/derivation_checker.yaml"
marker = "previous_steps_execution_summary"

with open(path, "r") as f:
    lines = f.readlines()

if any(marker in line for line in lines):
    print(f"Already patched: {path}")
    raise SystemExit(0)

target = "  {current_code_output}\n"
matches = [i for i, line in enumerate(lines) if line == target]

if len(matches) != 1:
    print(f"Expected exactly 1 match, found {len(matches)}.")
    for m in matches:
        print(f"  line {m+1}: {lines[m]!r}")
    raise SystemExit("Aborting - paste output so this can be adjusted.")

idx = matches[0]

insertion = [
    "\n",
    "  # hep-theory fork: added previous_steps_execution_summary - covers the\n",
    "  # general case where the prior step's real output came from\n",
    "  # inspirehep_context (literature) or cadabra_context (guidance-based\n",
    "  # derivation), neither of which populates current_code_output.\n",
    "  **Full output from previous plan steps (literature findings, derivations, etc.):**\n",
    "  {previous_steps_execution_summary}\n",
]

new_lines = lines[: idx + 1] + insertion + lines[idx + 1 :]

with open(path, "w") as f:
    f.writelines(new_lines)

print(f"Patched: {path} (inserted after line {idx + 1})")
