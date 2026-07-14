"""
Reusable report extractor for cmbagent deep_research() runs.

Reads planning/final_plan.json and control/chats/chat_history_step_*.json
directly (bypassing researcher_executor's save mechanism, which does not
appear to actually write files to disk), and compiles a single markdown
report with one section per plan step, showing each content-bearing agent's
final message for that step. Also appends an index of every executed code
file saved under control/codebase/.

Usage:
    python extract_report.py <work_dir>

Example:
    python extract_report.py output/replica_trick_test

Output:
    <work_dir>/report/compiled_report.md
"""

import sys
import os
import re
import json


CONTENT_AGENTS = {
    "engineer",
    "researcher",
    "cadabra_context",
    "inspirehep_context",
    "derivation_checker",
}

DOCSTRING_RE = re.compile(r'("""|\'\'\')(.*?)(\1)', re.DOTALL)


def load_json(path):
    with open(path) as f:
        return json.load(f)


def extract_preview(py_path, max_chars=200):
    """
    Best-effort one-line preview for a saved code file, pulled from the
    first triple-quoted string found anywhere in the file (module or
    function docstring - these files consistently define a single function
    with a docstring, not a module-level one, so a whole-file search is
    used rather than assuming line 1).
    Returns an empty string if no docstring-like block is found.
    """
    try:
        with open(py_path, "r", errors="replace") as f:
            text = f.read()
    except OSError:
        return ""

    m = DOCSTRING_RE.search(text)
    if not m:
        return ""

    for line in m.group(2).splitlines():
        line = line.strip()
        if line:
            return line[:max_chars]
    return ""


def collect_codebase_index(work_dir):
    """
    List every .py file under control/codebase/, sorted chronologically by
    modification time (execution order). This is a GLOBAL counter across
    the entire control phase, not tied to plan-step numbers - a file named
    step_1.py is not necessarily the code executed during plan Step 1, and
    a single plan step's retries each get their own new file rather than
    overwriting one another. Don't assume a step_N.py <-> plan-Step-N
    correspondence; use each file's own docstring/content to identify it.
    """
    codebase_dir = os.path.join(work_dir, "control", "codebase")
    if not os.path.isdir(codebase_dir):
        return []

    entries = []
    for fname in os.listdir(codebase_dir):
        if not fname.endswith(".py"):
            continue
        fpath = os.path.join(codebase_dir, fname)
        try:
            mtime = os.path.getmtime(fpath)
            size = os.path.getsize(fpath)
        except OSError:
            continue
        entries.append((mtime, fname, fpath, size))

    entries.sort(key=lambda e: e[0])
    return entries


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

    codebase_index = collect_codebase_index(work_dir)
    if codebase_index:
        sections.append("## Executed Code\n")
        sections.append(
            "Every code file actually executed during this run's control "
            "phase, in chronological order. **Numbering is a global counter "
            "across the whole run, not a plan-step index** - a single plan "
            "step's retries each produce a new file rather than overwriting "
            "one another, so consult each file's own docstring (previewed "
            "below) to identify what it does, not its filename.\n"
        )
        for mtime, fname, fpath, size in codebase_index:
            rel_path = os.path.relpath(fpath, work_dir)
            preview = extract_preview(fpath)
            preview_text = f" — {preview}" if preview else ""
            sections.append(f"- `{rel_path}` ({size} bytes){preview_text}")
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
