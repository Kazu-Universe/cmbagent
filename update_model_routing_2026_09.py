"""
Repo-source edit (not a venv patch): move cmbagent/utils/utils.py to the
September 2026 Claude lineup. Run once from the repo root, then review with
`git diff cmbagent/utils/utils.py` before committing:

    python update_model_routing_2026_09.py

What it changes:
 1. default_agents_llm_model: heavy agents -> Fable 5.1 / Opus 5.5 / Sonnet 5.5,
    replacing the TEMP cheap-model debug swap (planner/idea_* on Haiku).
 2. default_llm_model stays claude-sonnet-5 ON PURPOSE. Agents that are not in
    the dict (terminator, plan_recorder, review_recorder, controller, ...) fall
    back to it, and they use FORCED tool_choice - which Opus 5.5, Fable 5.1 and
    Sonnet 5.5 reject with a 400. Formatters stay on Haiku 4.5 for the same
    reason, and because AG2's _extract_json reads response.content[0].text,
    which is a thinking block on always-thinking models.
 3. get_model_config's claude branch: max_tokens 16000 -> 32000 (thinking is
    always on for Opus 5.5 / Fable 5.1 and shares the output budget), and a
    per-model `price` so AG2 cost tracking stops reporting $0 (its built-in
    table predates Claude 4).

Aborts without writing if the file doesn't look as expected.
"""
import re, sys
path = "cmbagent/utils/utils.py"
marker = "hep-theory fork: 2026-09 model routing"
src = open(path).read()
if marker in src:
    sys.exit(f"Already applied: {path}")

new_dict = f'''# {marker} (see update_model_routing_2026_09.py).
# Heavy agents are not known to use forced tool_choice (CHANGELOG_ADDENDUM names
# terminator / plan_recorder / review_recorder); confirm with a short dry run.
# Anything that uses forced tool_choice or response_format must stay on
# claude-sonnet-5 / claude-haiku-4-5 until AG2's forced tool_choice is replaced
# by auto + strict tool use (Opus 5.5 / Fable 5.1 / Sonnet 5.5 reject forcing).
default_agents_llm_model = {{
    "engineer": "claude-sonnet-5-5",
    "aas_keyword_finder": "claude-haiku-4-5-20251001",
    "researcher": "claude-opus-5-5",
    "planner": "claude-fable-5-1",
    "plan_reviewer": "claude-opus-5-5",
    "idea_hater": "claude-opus-5-5",
    "idea_maker": "claude-opus-5-5",
    "camb_context": "claude-sonnet-5-5",
    "summarizer": "claude-haiku-4-5-20251001",
    "summarizer_response_formatter": "claude-haiku-4-5-20251001",
    "inspirehep_context": "claude-sonnet-5-5",
    "cadabra_context": "claude-sonnet-5-5",
    "derivation_checker": "claude-opus-5-5",
}}'''
pat = re.compile(r"default_agents_llm_model = \{.*?\n\}", re.S)
if len(pat.findall(src)) != 1:
    sys.exit("Expected exactly one default_agents_llm_model dict - aborting, nothing written.")
src = pat.sub(lambda m: new_dict, src, count=1)
# drop the now-obsolete TEMP debug-swap comment, if present
src = src.replace("# hep-theory fork: TEMP cheap-model debug swap - fable-5 -> haiku for now,\n"
                  "# swap back once the pipeline is confirmed working end-to-end.\n", "")

old_claude = '''            "api_type": "anthropic",
            "max_tokens": 16000,
        })'''
if src.count(old_claude) != 1:
    sys.exit("Claude branch of get_model_config not found as expected - aborting, nothing written.")
new_claude = '''            "api_type": "anthropic",
            # hep-theory fork 2026-09: thinking is always on for Opus 5.5 /
            # Fable 5.1 and draws on the same budget as the reply.
            "max_tokens": 32000,
        })
        # USD per 1K tokens (input, output), platform.claude.com, 2026-09-30.
        if model in claude_price_per_1k:
            config["price"] = list(claude_price_per_1k[model])'''
src = src.replace(old_claude, new_claude)

anchor = "def get_model_config(model, api_keys):"
prices = '''# hep-theory fork 2026-09: AG2's ANTHROPIC_PRICING_1k predates Claude 4, so
# cost tracking silently reported $0 for every Claude 5 model. Passing `price`
# in the config entry overrides it.
claude_price_per_1k = {
    "claude-fable-5-1": (0.010, 0.050),
    "claude-opus-5-5": (0.004, 0.020),
    "claude-sonnet-5-5": (0.002, 0.010),
    "claude-sonnet-5": (0.002, 0.010),
    "claude-haiku-4-5-20251001": (0.001, 0.005),
}

'''
src = src.replace(anchor, prices + anchor, 1)
open(path, "w").write(src)
print(f"Updated {path}. Review: git diff {path}")
