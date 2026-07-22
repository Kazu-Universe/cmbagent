"""
One-time patch (v2, regex-based): replaces the OpenAI-hardcoded
default_agents_llm_model dict in cmbagent/utils/utils.py with an all-Anthropic
version, adding entries for the three new hep-theory agents.

This edits your own repo's source file directly (not a .venv dependency) —
a normal, permanent, git-trackable change.

Run once:
    python patch_default_agents_llm_model.py
"""

import re

path = "cmbagent/utils/utils.py"
marker = "hep-theory fork: all-Anthropic defaults"

with open(path, "r") as f:
    content = f.read()

if marker in content:
    print(f"Already patched: {path}")
    raise SystemExit(0)

# Match the dict assignment regardless of internal whitespace/formatting.
pattern = re.compile(
    r"default_agents_llm_model\s*=\s*\{[^}]*\}",
    re.DOTALL,
)

matches = pattern.findall(content)

if len(matches) != 1:
    print(f"Expected exactly 1 match, found {len(matches)}.")
    for m in matches:
        print("---")
        print(m)
    raise SystemExit(
        "Aborting - paste the output above so the patch can be adjusted."
    )

print("Found existing block:")
print(matches[0])
print("---")

new_block = '''# hep-theory fork: all-Anthropic defaults (was hardcoded to OpenAI models).
# Fable 5 for planning/idea-generation roles (exploratory, long-context synthesis);
# Sonnet for execution/critique roles; Haiku for mechanical formatting.
default_agents_llm_model = {
    "engineer": "claude-sonnet-5",
    "aas_keyword_finder": "claude-haiku-4-5-20251001",
    "researcher": "claude-sonnet-5",
    "planner": "claude-fable-5",
    "plan_reviewer": "claude-sonnet-5",
    "idea_hater": "claude-fable-5",
    "idea_maker": "claude-fable-5",
    "camb_context": "claude-sonnet-5",
    "summarizer": "claude-haiku-4-5-20251001",
    "summarizer_response_formatter": "claude-haiku-4-5-20251001",
    "inspirehep_context": "claude-sonnet-5",
    "cadabra_context": "claude-sonnet-5",
    "derivation_checker": "claude-sonnet-5",
}'''

new_content = pattern.sub(lambda m: new_block, content, count=1)

with open(path, "w") as f:
    f.write(new_content)

print(f"Patched: {path}")
