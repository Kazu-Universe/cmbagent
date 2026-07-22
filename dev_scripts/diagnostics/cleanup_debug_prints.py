"""
One-time cleanup: removes DIAGNOSTIC and GUARD-ID debug prints added during
this session's investigation, now that the underlying bugs are confirmed
fixed. Handles plan_recorder.py's multi-line f-string prints explicitly
(a naive line-filter would leave orphaned continuation-string syntax errors
behind), and conversable_agent.py's single-line GUARD-ID prints via simple
filtering (safe, since those are genuinely single lines).

Safe to re-run; skips anything already cleaned.

Run once from the repo root:
    python cleanup_debug_prints.py
"""

import autogen.agentchat.conversable_agent as ca_module

# --- 1. plan_recorder.py: remove known multi-line/single-line DIAGNOSTIC prints ---

pr_path = "cmbagent/agents/planning/plan_recorder/plan_recorder.py"

with open(pr_path, "r") as f:
    content = f.read()

pr_blocks_to_remove = [
    '        print(f">>> DIAGNOSTIC plan_recorder: last_message keys = {list(last_message.keys())}")\n'
    '        print(f">>> DIAGNOSTIC plan_recorder: content repr (first 200 chars) = {repr(last_message.get(\'content\', \'\'))[:200]}")\n'
    '        print(f">>> DIAGNOSTIC plan_recorder: message count = {len(messages)}, "\n'
    '              f"sender names in last 5 = {[m.get(\'name\') for m in messages[-5:]]}")\n',

    '        print(f">>> DIAGNOSTIC plan_recorder: resolved content length = {len(content)}, "\n'
    '              f"repr (first 150 chars) = {repr(content)[:150]}")\n',

    '        print(f">>> DIAGNOSTIC plan_recorder: feedback_left = {feedback_left!r} (type {type(feedback_left)})")\n',

    '            print(">>> DIAGNOSTIC plan_recorder: set final_plan (feedback_left==0 branch)")\n',

    '            print(">>> DIAGNOSTIC plan_recorder: NOT setting final_plan (else branch)")\n',

    '        print(">>> DIAGNOSTIC plan_recorder: _record_plan_reply ENTERED, "\n'
    '              f"messages count = {len(messages) if messages else 0}")\n',
]

pr_removed = 0
for block in pr_blocks_to_remove:
    if block in content:
        content = content.replace(block, "")
        pr_removed += 1

with open(pr_path, "w") as f:
    f.write(content)

print(f"plan_recorder.py: removed {pr_removed}/{len(pr_blocks_to_remove)} known diagnostic block(s)")

# --- 2. conversable_agent.py: remove single-line GUARD-ID prints (safe filter) ---

ca_path = ca_module.__file__

with open(ca_path, "r") as f:
    lines = f.readlines()

new_lines = [line for line in lines if not ("GUARD-ID" in line and "print(" in line)]
ca_removed = len(lines) - len(new_lines)

with open(ca_path, "w") as f:
    f.writelines(new_lines)

print(f"conversable_agent.py: removed {ca_removed} GUARD-ID print line(s)")

print("\nDone. Re-run your test script to confirm nothing broke (e.g. python -c \"import ast; ast.parse(open('"
      + pr_path + "').read())\" and same for conversable_agent.py, or just run diagnose_final_plan.py).")
