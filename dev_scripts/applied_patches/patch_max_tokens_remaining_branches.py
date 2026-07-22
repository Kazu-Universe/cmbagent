"""
One-time patch: adds max_tokens to get_model_config's remaining branches
(o3/o1 reasoning models, gemini, generic openai fallback) for completeness,
matching the fix already applied to the 'claude' branch. Not currently in
active use in this fork (all agents route through Claude), but closes the
gap for any future use (e.g. revisiting OpenRouter models, which fall
through to the generic 'else' openai-compatible branch) - autogen's default
of 4096 would otherwise silently apply there too.

Note: o3/o1 reasoning models consume tokens for both internal reasoning and
final output from the same budget, so they may need a higher ceiling than
16000 if ever actually used - flagged in the comment below rather than
guessed at a specific higher value, since this branch is untested in this
fork.

Run once from the repo root:
    python patch_max_tokens_remaining_branches.py
"""

path = "cmbagent/utils/utils.py"
marker = "hep-theory fork: max_tokens for remaining branches"

with open(path, "r") as f:
    content = f.read()

if marker in content:
    print(f"Already patched: {path}")
    raise SystemExit(0)

old = '''    if 'o3' in model or 'o1' in model:
        config.update({
            "reasoning_effort": "medium",
            "api_key": api_keys["OPENAI"],
            "api_type": "openai"
        })
    elif "gemini" in model:
        config.update({
            "api_key": api_keys["GEMINI"],
            "api_type": "google"
        })'''

new = '''    # hep-theory fork: max_tokens for remaining branches (not actively used
    # in this fork - all agents route through Claude - but closes the gap
    # for any future use, matching the fix on the 'claude' branch below).
    if 'o3' in model or 'o1' in model:
        # Note: reasoning models spend tokens on internal reasoning AND final
        # output from the same budget - 16000 may be too low if this branch
        # is ever actually exercised; untested in this fork, raise if needed.
        config.update({
            "reasoning_effort": "medium",
            "api_key": api_keys["OPENAI"],
            "api_type": "openai",
            "max_tokens": 16000,
        })
    elif "gemini" in model:
        config.update({
            "api_key": api_keys["GEMINI"],
            "api_type": "google",
            "max_tokens": 16000,
        })'''

count = content.count(old)
if count != 1:
    raise SystemExit(
        f"Expected exactly 1 occurrence, found {count}. Paste the actual "
        "content so this can be adjusted."
    )
content = content.replace(old, new, 1)

old_else = '''    else:
        config.update({
            "api_key": api_keys["OPENAI"],
            "api_type": "openai"
        })
    return config'''

new_else = '''    else:
        config.update({
            "api_key": api_keys["OPENAI"],
            "api_type": "openai",
            "max_tokens": 16000,
        })
    return config'''

count_else = content.count(old_else)
if count_else != 1:
    raise SystemExit(
        f"Expected exactly 1 occurrence of the else/fallback block, found "
        f"{count_else}. Paste the actual content so this can be adjusted."
    )
content = content.replace(old_else, new_else, 1)

with open(path, "w") as f:
    f.write(content)

print(f"Patched: {path}")
