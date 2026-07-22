"""
One-time patch: adds a unique identifying print to each of the four
empty-messages guards added earlier, so we can see exactly which one fires
during the Step 1->2 transition (suspected of silently suppressing
controller's legitimate step-advancement message).

Run once from the repo root:
    python patch_identify_guard_locations.py
"""

import autogen.agentchat.conversable_agent as ca_module

path = ca_module.__file__
marker = "hep-theory fork: empty messages guard"
id_marker = "GUARD-ID:"

with open(path, "r") as f:
    lines = f.readlines()

if any(id_marker in line for line in lines):
    print("Already patched with identifiers.")
    raise SystemExit(0)

# Find each guard block by its "if not messages:" line, preceded by our marker
# within the last few lines.
new_lines = []
guard_count = 0
i = 0
while i < len(lines):
    line = lines[i]
    if line.strip() == "if not messages:" and any(
        marker in lines[j] for j in range(max(0, i - 4), i)
    ):
        guard_count += 1
        # Find the enclosing function name by scanning upward.
        func_name = "unknown"
        for j in range(i, max(0, i - 60), -1):
            stripped = lines[j].lstrip()
            if stripped.startswith("def "):
                func_name = stripped.split("(")[0].replace("def ", "").strip()
                break
        new_lines.append(line)  # "if not messages:"
        i += 1
        # next line should be "return False, None" - insert print before it
        new_lines.append(
            f'            print(">>> GUARD-ID: #{guard_count} in {func_name} '
            f'(line ~{i+1}) - declining reply, messages empty")\n'
        )
        continue
    new_lines.append(line)
    i += 1

with open(path, "w") as f:
    f.writelines(new_lines)

print(f"Patched: {path}")
print(f"Instrumented {guard_count} guard location(s) with identifying prints.")
