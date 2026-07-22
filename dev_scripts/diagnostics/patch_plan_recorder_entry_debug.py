"""
One-time patch: adds a diagnostic print at the very first line of
_record_plan_reply, to confirm definitively whether this function is ever
entered during a run.

Run once from the repo root:
    python patch_plan_recorder_entry_debug.py
"""

path = "cmbagent/agents/planning/plan_recorder/plan_recorder.py"
marker = "_record_plan_reply ENTERED"

with open(path, "r") as f:
    content = f.read()

if marker in content:
    print(f"Already patched: {path}")
    raise SystemExit(0)

old = '''        """
        Parse the plan from the last message and record it in context_variables.
        Returns:
            Tuple of (True, message) indicating the reply was generated.
        """
        if not messages:
            return True, "No message to process."'''

new = '''        """
        Parse the plan from the last message and record it in context_variables.
        Returns:
            Tuple of (True, message) indicating the reply was generated.
        """
        print(">>> DIAGNOSTIC plan_recorder: _record_plan_reply ENTERED, "
              f"messages count = {len(messages) if messages else 0}")
        if not messages:
            return True, "No message to process."'''

if old not in content:
    raise SystemExit(
        f"Expected exact block not found in {path} - paste the file content "
        "so it can be adjusted."
    )

content = content.replace(old, new)

with open(path, "w") as f:
    f.write(content)

print(f"Patched: {path}")
