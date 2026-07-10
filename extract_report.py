"""
Reusable report extractor for cmbagent deep_research() runs.

Reads planning/final_plan.json and control/chats/chat_history_step_*.json
directly (bypassing researcher_executor's save mechanism, which does not
appear to actually write files to disk), and compiles a single markdown
report with one section per plan step, showing each content-bearing agent's
final message for that step.

Usage:
    python extract_report.py <work_dir>

Example:
    python extract_report.py output/replica_trick_test

Output:
    <work_dir>/report/compiled_report.md
"""

import sys
import os
import json


CONTENT_AGENTS = {
    "engineer",
    "researcher",
    "cadabra_context",
    "inspirehep_context",
    "derivation_checker",
}


def load_json(path):
    with open(path) as f:
        return json.load(f)


def main(work_dir):
    work_dir = os.path.expanduser(work_dir)
    planning_path = os.path.join(work_dir, "planning", "final_plan.json")

    if not os.path.exists(planning_path):
        print(f"No final_plan.json found at {planning_path} - is this a valid work_dir?")
        sys.exit(1)

    plan = load_json(planning_path)
    sub_tasks = plan["sub_tasks"]

    chats_dir = os.path.join(work_dir, "control", "chats")
    report_dir = os.path.join(work_dir, "report")
    os.makedirs(report_dir, exist_ok=True)

    sections = []
    run_name = os.path.basename(work_dir.rstrip("/"))
    sections.append(f"# Compiled Report: {run_name}\n")
    sections.append(
        f"Auto-extracted from saved `chat_history_step_*.json` transcripts "
        f"(work_dir: `{work_dir}`). Not from the built-in save step, which does "
        f"not appear to actually write files to disk.\n"
    )
    sections.append("## Plan\n")
    for i, s in enumerate(sub_tasks, start=1):
        sections.append(f"- **Step {i}** (`{s['sub_task_agent']}`): {s['sub_task']}")
    sections.append("")

    for i, s in enumerate(sub_tasks, start=1):
        step_file = os.path.join(chats_dir, f"chat_history_step_{i}.json")
        sections.append(f"## Step {i}: {s['sub_task']}\n")
        sections.append(f"*Assigned agent: `{s['sub_task_agent']}`*\n")

        if not os.path.exists(step_file):
            sections.append("*(no chat history found for this step - may not have run yet)*\n")
            continue

        history = load_json(step_file)

        # Collect messages from every content-bearing agent that spoke this
        # step, keeping them in first-seen order but only the LAST message per
        # agent (most complete, in case of truncation/continuation retries).
        agent_msgs = {}
        for m in history:
            name = m.get("name")
            content = (m.get("content") or "").strip()
            if name in CONTENT_AGENTS and content:
                agent_msgs.setdefault(name, []).append(content)

        if not agent_msgs:
            sections.append(
                "*(no substantive content found from any known content-bearing "
                "agent this step)*\n"
            )
            continue

        for name, msgs in agent_msgs.items():
            final_msg = msgs[-1]
            sections.append(f"### Output from `{name}`\n")
            sections.append(final_msg)
            sections.append("")

    report_text = "\n".join(sections)
    out_path = os.path.join(report_dir, "compiled_report.md")
    with open(out_path, "w") as f:
        f.write(report_text)

    print(f"Report written to: {out_path}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python extract_report.py <work_dir>")
        sys.exit(1)
    main(sys.argv[1])
