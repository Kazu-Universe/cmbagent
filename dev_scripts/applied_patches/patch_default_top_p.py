"""
One-time patch: sets default_top_p = None at its source in cmbagent/utils/utils.py.

Some Claude models (e.g. claude-fable-5) reject top_p entirely via the Anthropic
API ("top_p is deprecated for this model"). autogen's Anthropic client wrapper
drops the key from the request when it's None (confirmed in
autogen/oai/anthropic.py), so this is safe across all Claude models rather
than a per-call workaround. Fixing it here (not just at individual CMBAgent()
call sites) means deep_research() and any other caller that doesn't explicitly
pass top_p= is covered automatically.

Run once:
    python patch_default_top_p.py
"""

import re

path = "cmbagent/utils/utils.py"
marker = "hep-theory fork: top_p disabled"

with open(path, "r") as f:
    content = f.read()

if marker in content:
    print(f"Already patched: {path}")
    raise SystemExit(0)

pattern = re.compile(r"default_top_p\s*=\s*[^\n]+")
matches = pattern.findall(content)

if len(matches) != 1:
    print(f"Expected exactly 1 match, found {len(matches)}: {matches}")
    raise SystemExit("Aborting - paste the output above so the patch can be adjusted.")

print(f"Found: {matches[0]}")

new_line = (
    "default_top_p = None  # hep-theory fork: top_p disabled - some Claude models "
    "(e.g. claude-fable-5) reject top_p entirely via the Anthropic API"
)

new_content = pattern.sub(new_line, content, count=1)

with open(path, "w") as f:
    f.write(new_content)

print(f"Patched: {path}")
