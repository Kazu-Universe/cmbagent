"""R1 (CLAUDE.md bug class 1): forced ``tool_choice`` schema translation.

ag2's swarm hand-off mechanism builds a forced ``tool_choice`` in OpenAI's
schema unconditionally: ``{"type": "function", "function": {"name": X}}``.
Anthropic's actual schema only accepts ``"type"`` values ``"auto"``,
``"any"``, ``"tool"`` or ``"none"`` - the forced-single-tool form being
``{"type": "tool", "name": X}``.

Two different, conflicting descriptions of "without the fix" exist in this
repo's own history, and this test's bite check resolves which one matches
reality:

- ``CHANGELOG_ADDENDUM.md`` (the original diagnosis): "any agent using a
  forced tool_choice ... gets a 400 from the Anthropic API."
- The inline comment on the fix itself, ``AnthropicClient.create()`` in
  ``autogen/oai/anthropic.py`` (around "hep-theory fork fix"): "params
  ``tool_choice`` was being silently dropped here - never copied into
  ``anthropic_params`` at all ... not even a 400, just silently ignored."

These can't both be right, and the bite check settles it: fork commit
``8318d871`` (introducing this fix) only *adds* the translation block inside
``create()`` - it never touches ``load_config``, which on the pre-fix
baseline (``385340d4``) already does
``anthropic_params["tool_choice"] = validate_parameter(params, "tool_choice", dict, ...)``,
copying the raw OpenAI-schema dict straight through. Confirmed directly:
``sent_tool_choice`` against the baseline returns the dict unchanged, not an
absent key - it reaches ``self._client.messages.create(**anthropic_params)``
untranslated. A real (non-mocked) call with ``"type": "function"`` - outside
Anthropic's documented enum - would be expected to fail request validation
with a 400, matching ``CHANGELOG_ADDENDUM.md``, not the inline comment's
"silently ignored" claim, which does not match what the committed baseline
actually does and appears to be a misdiagnosis written into the fix itself.

Bite check: ``bite_check.py`` runs ``sent_tool_choice`` against the pre-fix
baseline (ag2 commit ``385340d4``) and confirms it forwards the raw
OpenAI-schema dict instead of translating it.
"""

from __future__ import annotations

from tests.regression._checks import ABSENT, sent_tool_choice


def test_openai_schema_forced_choice_is_translated(live_anthropic_module):
    sent = sent_tool_choice(
        live_anthropic_module,
        {"type": "function", "function": {"name": "record_plan"}},
    )
    assert sent == {"type": "tool", "name": "record_plan"}


def test_anthropic_schema_choice_passes_through_unchanged(live_anthropic_module):
    sent = sent_tool_choice(live_anthropic_module, {"type": "tool", "name": "record_plan"})
    assert sent == {"type": "tool", "name": "record_plan"}


def test_string_tool_choice_is_dropped_not_forwarded(live_anthropic_module):
    # validate_parameter(..., dict, ...) nulls a non-dict tool_choice, and
    # create() deletes the key when it ends up None - a string value like
    # "auto"/"required" never reaches the SDK call.
    sent = sent_tool_choice(live_anthropic_module, "auto")
    assert sent is ABSENT


def test_absent_tool_choice_stays_absent(live_anthropic_module):
    sent = sent_tool_choice(live_anthropic_module, ABSENT)
    assert sent is ABSENT


def test_malformed_function_choice_is_a_known_unfixed_hole(live_anthropic_module):
    """Documented current behaviour, not desired behaviour: a
    ``{"type": "function", "function": {}}`` with no ``name`` key falls
    through both translation branches in ``create()`` (neither the
    "function" branch, which requires a name, nor the "tool" pass-through
    branch matches), so the raw OpenAI-schema dict set by ``load_config``
    survives untouched and is sent as-is. Pinned here so a future fix to this
    hole shows up as a deliberate, visible test change rather than a silent
    behaviour change."""
    sent = sent_tool_choice(live_anthropic_module, {"type": "function", "function": {}})
    assert sent == {"type": "function", "function": {}}
