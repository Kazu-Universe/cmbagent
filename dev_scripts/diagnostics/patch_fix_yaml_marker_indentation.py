"""
One-time fix: removes the zero-indent marker comment
"# hep-theory fork: placeholder removed" that broke YAML block-scalar parsing
in all three agent prompt files. The instructions: | block requires every
continuation line to maintain the block's indentation; the previous patch's
marker line had none, terminating the block scalar early and causing a
ParserError on every subsequent line.

The marker isn't needed for idempotency - once the actual placeholder text
is gone, re-running the original patch will just report "0 occurrences
found" harmlessly, which is an equally good idempotency check.

Run once from the repo root:
    python patch_fix_yaml_marker_indentation.py
"""

paths = [
    "cmbagent/agents/inspirehep_context/inspirehep_context.yaml",
    "cmbagent/agents/cadabra_context/cadabra_context.yaml",
    "cmbagent/agents/derivation_checker/derivation_checker.yaml",
]

bad_line = "# hep-theory fork: placeholder removed\n"

for path in paths:
    with open(path, "r") as f:
        lines = f.readlines()

    new_lines = [line for line in lines if line != bad_line]
    removed = len(lines) - len(new_lines)

    if removed == 0:
        print(f"Nothing to fix in {path} (marker not found or already fixed)")
        continue

    with open(path, "w") as f:
        f.writelines(new_lines)

    print(f"Fixed {path}: removed {removed} unindented marker line(s)")

print("\nDone. Verifying YAML parses cleanly now...")

import yaml
for path in paths:
    try:
        with open(path) as f:
            yaml.safe_load(f)
        print(f"  OK: {path}")
    except Exception as e:
        print(f"  STILL BROKEN: {path} -> {e}")
