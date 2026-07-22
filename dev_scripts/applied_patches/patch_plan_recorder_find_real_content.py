"""
One-time patch: fixes plan_recorder receiving an empty message.

Root cause (confirmed via diagnostic): plan_recorder's own per-sender message
view (messages[-1], i.e. agent._oai_messages[sender]) only contains ONE
message, attributed to _Group_Tool_Executor, with EMPTY content. The actual
formatted plan text from planner_response_formatter lives in the broader group
chat history, not in this narrow per-sender view - AG2 routes real content
through group chat bookkeeping differently when the previous agent didn't make
an actual tool call (planner_response_formatter uses structured Pydantic
response_format, not a tool call).

Fix: search across ALL of recipient._oai_messages (every conversation partner,
not just the current sender) for the most recent message actually from
planner_response_formatter with non-empty content, and use that as the source
text instead of blindly trusting messages[-1].

Run once from the repo root:
    python patch_plan_recorder_find_real_content.py
"""

path = "cmbagent/agents/planning/plan_recorder/plan_recorder.py"
marker = "hep-theory fork: search full history for real plan content"

with open(path, "r") as f:
    content = f.read()

if marker in content:
    print(f"Already patched: {path}")
    raise SystemExit(0)

old = '''        last_message = messages[-1]
        print(f">>> DIAGNOSTIC plan_recorder: last_message keys = {list(last_message.keys())}")
        print(f">>> DIAGNOSTIC plan_recorder: content repr (first 200 chars) = {repr(last_message.get('content', ''))[:200]}")
        print(f">>> DIAGNOSTIC plan_recorder: message count = {len(messages)}, "
              f"sender names in last 5 = {[m.get('name') for m in messages[-5:]]}")
        content = last_message.get("content", "")'''

new = '''        # hep-theory fork: search full history for real plan content.
        # messages[-1] (this agent's narrow per-sender view) is often an empty
        # placeholder attributed to _Group_Tool_Executor rather than the real
        # formatted plan text - search across ALL conversation partners for the
        # most recent substantive message from planner_response_formatter.
        content = ""
        try:
            all_partners = recipient._oai_messages
            candidates = []
            for partner, msg_list in all_partners.items():
                for m in msg_list:
                    if m.get("name") == "planner_response_formatter" and m.get("content"):
                        candidates.append(m)
            if candidates:
                content = candidates[-1].get("content", "")
        except Exception as e:
            print(f">>> DIAGNOSTIC plan_recorder: full-history search failed: {e}")

        if not content:
            # fall back to the original narrow view, in case the search above
            # legitimately found nothing (e.g. different agent name/flow)
            last_message = messages[-1] if messages else {}
            content = last_message.get("content", "")

        print(f">>> DIAGNOSTIC plan_recorder: resolved content length = {len(content)}, "
              f"repr (first 150 chars) = {repr(content)[:150]}")'''

if old not in content:
    raise SystemExit(
        f"Expected exact block not found in {path} - paste the file content "
        "so it can be adjusted."
    )

content = content.replace(old, new)

with open(path, "w") as f:
    f.write(content)

print(f"Patched: {path}")
