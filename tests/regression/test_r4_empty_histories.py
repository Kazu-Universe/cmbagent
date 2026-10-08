"""R4 (CLAUDE.md bug class 4): empty histories.

Forced-termination hand-offs (hitting ``max_rounds``) can route to an agent
with no prior message history for that sender. Five separate unguarded
``message = messages[-1]`` occurrences in ``autogen/agentchat/conversable_agent.py``
used to crash with ``IndexError``; a sixth code path,
``oai_messages_to_anthropic_messages`` in ``autogen/oai/anthropic.py``, had
the same root cause via ``processed_messages[-1]["role"]``.

Bite check: ``bite_check.py`` runs the same calls against the pre-fix
baseline (ag2 commit ``385340d4``) and confirms four of them raise
``IndexError``; the fifth (``check_termination_and_human_reply``) does not
bite there either - see below.
"""

from __future__ import annotations

import inspect

import pytest

from tests.regression._checks import (
    GUARD_MARKER,
    call_empty_history_async,
    call_empty_history_sync,
    convert_empty_messages,
    guard_marker_count,
    not_messages_count,
)

SYNC_METHODS = ["generate_function_call_reply", "generate_tool_calls_reply"]
ASYNC_METHODS = ["a_generate_function_call_reply", "a_generate_tool_calls_reply"]


@pytest.mark.parametrize("method_name", SYNC_METHODS)
def test_sync_empty_history_declines_instead_of_crashing(live_conversable_agent_module, method_name):
    assert call_empty_history_sync(live_conversable_agent_module, method_name) == (False, None)


@pytest.mark.parametrize("method_name", ASYNC_METHODS)
def test_async_empty_history_declines_instead_of_crashing(live_conversable_agent_module, method_name):
    assert call_empty_history_async(live_conversable_agent_module, method_name) == (False, None)


def test_check_termination_empty_history_does_not_crash(live_conversable_agent_module):
    """This fifth guarded site does NOT bite on its own: upstream ag2 already
    has its own ``if not messages: return False, None`` guard a few lines
    below the fork's (dead code today, since the fork's guard returns
    first). Reverting just the fork's copy here still passes. The marker
    count below is what actually catches this site regressing."""
    result = call_empty_history_sync(live_conversable_agent_module, "check_termination_and_human_reply")
    assert result == (False, None)


def test_five_fork_guards_and_six_total_present(live_conversable_agent_module):
    """Venv-rebuild detector for the one site (above) that can't bite
    behaviourally: exactly 5 fork-added guards (marker-commented), 6 total
    ``if not messages:`` occurrences once upstream's own pre-existing guard
    in ``check_termination_and_human_reply`` is counted too."""
    source = inspect.getsource(live_conversable_agent_module)
    assert guard_marker_count(source) == 5, f"expected 5 occurrences of {GUARD_MARKER!r}"
    assert not_messages_count(source) == 6


def test_empty_messages_to_anthropic_conversion_does_not_crash(live_anthropic_module):
    result = convert_empty_messages(live_anthropic_module)
    assert result == [{"content": "Please continue.", "role": "user"}]
