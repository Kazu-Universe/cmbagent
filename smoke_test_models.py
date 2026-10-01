"""
Smoke test: which current Claude models accept the request shapes CMBAgent/AG2 sends?

Run from the repo root with .venv activated (needs ANTHROPIC_API_KEY):
    python smoke_test_models.py

Checks, per model:
  basic   - plain request, no sampling params
  temp    - temperature=0.00001 (CMBAgent's default_temperature; Sonnet 5 docs say
            non-default temperature returns 400 - this checks what actually happens)
  forced  - tool_choice={"type":"tool", ...} (what patch_anthropic_tool_choice.py
            produces for terminator / plan_recorder / review_recorder etc.;
            Opus 5.5, Fable 5.1 and Sonnet 5.5 docs say this returns 400)
  blocks  - content block types in a basic response (thinking blocks first would
            break any code that reads response.content[0].text)

Cost: a few thousand tokens per model - well under $1 in total.
"""
import os, anthropic

MODELS = [
    "claude-fable-5-1",
    "claude-opus-5-5",
    "claude-sonnet-5-5",
    "claude-sonnet-5",            # current default_llm_model (legacy)
    "claude-haiku-4-5-20251001",  # current formatter model
]
TOOL = {"name": "record", "description": "Record a one-word status.",
        "input_schema": {"type": "object", "properties": {"status": {"type": "string"}},
                         "required": ["status"]}}
MSG = [{"role": "user", "content": "Reply with the single word: ready."}]
client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

def attempt(**kw):
    try:
        r = client.messages.create(max_tokens=4000, messages=MSG, **kw)
        return "OK", r
    except anthropic.APIStatusError as e:
        return f"{e.status_code}: {str(e.message)[:90]}", None
    except Exception as e:
        return f"ERR: {type(e).__name__}: {str(e)[:80]}", None

print(f"anthropic SDK {anthropic.__version__}\n")
for m in MODELS:
    basic, r = attempt(model=m)
    blocks = [b.type for b in r.content] if r else []
    temp, _ = attempt(model=m, temperature=0.00001)
    forced, _ = attempt(model=m, tools=[TOOL], tool_choice={"type": "tool", "name": "record"})
    print(f"{m}")
    print(f"   basic : {basic}   blocks={blocks}")
    print(f"   temp  : {temp}")
    print(f"   forced: {forced}\n")
