"""
One-time patch: adds diagnostic prints right after last_message is extracted,
to see exactly what content (and message history) plan_recorder actually
receives — investigating why final_plan ended up an empty string despite the
plan text clearly being generated and printed just before.

Run once from the repo root:
    python patch_plan_recorder_content_debug.py
"""

path = "cmbagent/agents/planning/plan_recorder/plan_recorder.py"
marker = "content repr (first 200 chars)"

with open(path, "r") as f:
    content = f.read()

if marker in content:
    print(f"Already patched: {path}")
    raise SystemExit(0)

old = '''        last_message = messages[-1]
        content = last_message.get("content", "")'''

new = '''        last_message = messages[-1]
        print(f">>> DIAGNOSTIC plan_recorder: last_message keys = {list(last_message.keys())}")
        print(f">>> DIAGNOSTIC plan_recorder: content repr (first 200 chars) = {repr(last_message.get('content', ''))[:200]}")
        print(f">>> DIAGNOSTIC plan_recorder: message count = {len(messages)}, "
              f"sender names in last 5 = {[m.get('name') for m in messages[-5:]]}")
        content = last_message.get("content", "")'''

if old not in content:
    raise SystemExit(
        f"Expected exact block not found in {path} - paste the file content "
        "so it can be adjusted."
    )

content = content.replace(old, new)

with open(path, "w") as f:
    f.write(content)

print(f"Patched: {path}")
