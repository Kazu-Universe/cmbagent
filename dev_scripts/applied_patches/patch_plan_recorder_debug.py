"""
One-time patch: adds diagnostic print statements to plan_recorder.py's
_record_plan_reply, to reveal the actual feedback_left value and whether
final_plan gets set, right at the decision point.

Run once from the repo root:
    python patch_plan_recorder_debug.py
"""

path = "cmbagent/agents/planning/plan_recorder/plan_recorder.py"
marker = "DIAGNOSTIC plan_recorder"

with open(path, "r") as f:
    content = f.read()

if marker in content:
    print(f"Already patched: {path}")
    raise SystemExit(0)

old = '''        feedback_left = ctx.get("feedback_left", 1)
        if feedback_left == 0:
            ctx["final_plan"] = plan_suggestion
            return True, "Plan recorded as final. Planning stage complete."
        else:
            return True, "Plan has been logged."'''

new = '''        feedback_left = ctx.get("feedback_left", 1)
        print(f">>> DIAGNOSTIC plan_recorder: feedback_left = {feedback_left!r} (type {type(feedback_left)})")
        if feedback_left == 0:
            ctx["final_plan"] = plan_suggestion
            print(">>> DIAGNOSTIC plan_recorder: set final_plan (feedback_left==0 branch)")
            return True, "Plan recorded as final. Planning stage complete."
        else:
            print(">>> DIAGNOSTIC plan_recorder: NOT setting final_plan (else branch)")
            return True, "Plan has been logged."'''

if old not in content:
    raise SystemExit(
        f"Expected exact block not found in {path} - file may differ from "
        "what this patch expects. Paste the file content so it can be adjusted."
    )

content = content.replace(old, new)

with open(path, "w") as f:
    f.write(content)

print(f"Patched: {path}")
