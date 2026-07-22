"""
One-time patch: raises the default max_tokens for all Claude-routed agent
configs from autogen's built-in default (4096) to a much more generous value.

Root cause of yesterday's cost blowup: 4096 tokens/turn is autogen's own
hardcoded default (autogen/oai/anthropic.py Field(default=4096)), not a
Claude API limit - Claude Sonnet 5 supports up to 128K output tokens on the
synchronous Messages API. Every Claude-backed agent in this pipeline was
silently capped at 4096/turn, causing:
  - cadabra_context's heat-kernel derivation to truncate repeatedly, each
    "complete the derivation" retry regenerating large parts from scratch
    (~420K tokens in one run, mostly redundant restatement)
  - earlier "Failed to parse response as valid JSON... Unterminated string"
    formatter errors, where a long code block/derivation got cut off
    mid-JSON-string during structured-output formatting

Fixed at the actual source (get_model_config's 'claude' branch) so it
applies to every Claude-routed agent uniformly - engineer, cadabra_context,
derivation_checker, formatters, everything - rather than raising max_tokens
per-agent one role at a time.

Run once after any fresh install/venv rebuild:
    python patch_raise_max_tokens.py
"""

path = "cmbagent/utils/utils.py"
marker = "hep-theory fork: raised default max_tokens"

with open(path, "r") as f:
    content = f.read()

if marker in content:
    print(f"Already patched: {path}")
    raise SystemExit(0)

old = '''    elif "claude" in model:
        config.update({
            "api_key": api_keys["ANTHROPIC"],
            "api_type": "anthropic"
        })'''

new = '''    elif "claude" in model:
        # hep-theory fork: raised default max_tokens - autogen's own default
        # (4096) is far below what Claude Sonnet 5 actually supports (128K),
        # and was causing repeated truncation -> costly "complete this" retry
        # cycles across long-derivation and code-heavy agents.
        config.update({
            "api_key": api_keys["ANTHROPIC"],
            "api_type": "anthropic",
            "max_tokens": 16000,
        })'''

count = content.count(old)
if count != 1:
    raise SystemExit(
        f"Expected exactly 1 occurrence, found {count}. Paste the actual "
        "'claude' branch content so this can be adjusted."
    )

content = content.replace(old, new, 1)

with open(path, "w") as f:
    f.write(content)

print(f"Patched: {path}")
