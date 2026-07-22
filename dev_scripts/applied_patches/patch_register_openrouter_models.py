"""
One-time patch: registers DeepSeek/OpenRouter model slugs in local_llm_urls,
fixing clean_llm_config silently stripping base_url for any api_type='openai'
config whose model name isn't in this dict (a safety check meant to prevent
stale base_url settings, that doesn't know OpenRouter is a legitimate
custom-endpoint provider rather than "local").

This works regardless of whether the model was set via get_model_config's
dict pass-through or the local_llm_urls string-lookup path - clean_llm_config
only checks dict membership by model name.

Run once from the repo root:
    python patch_register_openrouter_models.py
"""

path = "cmbagent/utils/utils.py"
marker = "hep-theory fork: registered OpenRouter/DeepSeek models"

with open(path, "r") as f:
    content = f.read()

if marker in content:
    print(f"Already patched: {path}")
    raise SystemExit(0)

old = '''local_llm_urls = {
    "gpt-oss-120b": os.getenv("GPT_OSS_120B_URL"),
    # "gpt-oss-20b": os.getenv("GPT_OSS_20B_URL"),
}'''

new = '''local_llm_urls = {
    "gpt-oss-120b": os.getenv("GPT_OSS_120B_URL"),
    # "gpt-oss-20b": os.getenv("GPT_OSS_20B_URL"),
    # hep-theory fork: registered OpenRouter/DeepSeek models. This dict is
    # really "model name -> trusted base_url", not strictly "local" - it's
    # also what clean_llm_config() checks before stripping base_url from any
    # api_type='openai' config, so OpenRouter models need to be here even
    # though they're not local.
    "deepseek/deepseek-v4-pro": "https://openrouter.ai/api/v1",
    "deepseek/deepseek-v4-flash": "https://openrouter.ai/api/v1",
}'''

count = content.count(old)
if count != 1:
    raise SystemExit(
        f"Expected exactly 1 occurrence, found {count}. Paste the actual "
        "local_llm_urls block so this can be adjusted."
    )

content = content.replace(old, new, 1)

with open(path, "w") as f:
    f.write(content)

print(f"Patched: {path}")
