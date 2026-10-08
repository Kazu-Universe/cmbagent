"""R3 (CLAUDE.md bug class 3): key presence is not truthiness.

``GroupToolExecutor._generate_group_tool_reply`` checked
``if "tool_calls" in message:`` (key presence) and only ever assigns
``tool_message`` inside the loop over ``range(tool_call_count)``. An
Anthropic-backed reply with no actual tool call can still carry
``tool_calls: []`` (present but empty), so the loop runs zero times and the
later ``if tool_message is None:`` raises ``UnboundLocalError``.

The fork's fix (``autogen/agentchat/group/group_tool_executor.py``, "hep-theory
fork: defensive guard") keeps the ``in`` check but adds an explicit
``tool_call_count == 0`` early return - functionally equivalent to a
``.get(...)`` truthiness check, so this test asserts behaviour, not the
literal source pattern.

Bite check: ``bite_check.py`` runs the same call against the pre-fix baseline
(ag2 commit ``385340d4``) and confirms it raises ``UnboundLocalError``.
"""

from __future__ import annotations

import inspect

import pytest

from tests.regression._checks import (
    DEFENSIVE_GUARD_MARKER,
    call_empty_tool_calls_reply,
    call_tool_reply_with_empty_history,
)


def test_empty_but_present_tool_calls_declines_instead_of_crashing(live_group_tool_executor_module):
    with pytest.warns(UserWarning, match="hep-theory fork diagnostic"):
        result = call_empty_tool_calls_reply(live_group_tool_executor_module)
    assert result == (False, None)


def test_fix_marker_present_venv_rebuild_detector(live_group_tool_executor_module):
    """No patch script restores this fix if a venv rebuild drops it (unlike
    R1/R4, it exists only as fork commit ``dc191dd5``) - so pin the marker
    directly as a second line of defence."""
    source = inspect.getsource(live_group_tool_executor_module.GroupToolExecutor)
    assert DEFENSIVE_GUARD_MARKER in source


@pytest.mark.xfail(
    strict=True,
    raises=IndexError,
    reason="unguarded sibling site: no patch script covers an empty `messages` list here",
)
def test_empty_history_sibling_site_is_still_unguarded(live_group_tool_executor_module):
    """Found during exploration, not fixed by this change: the same function
    has no guard at all for ``messages=[]`` (as opposed to a present-but-empty
    ``tool_calls`` list) - it raises ``IndexError`` at ``message =
    messages[-1]`` before ever reaching the ``tool_calls`` check. Same bug
    class 4 as R4, a site the five-guard patch never covered.

    ``raises=IndexError`` narrows the xfail to exactly this bug: if the call
    instead returned a value, this assertion (not just the bare call) is what
    would surface that as a real failure rather than a silently-matching
    xfail, and any *other* exception type would also fail loudly instead of
    being swallowed. Kept as a strict xfail so a real fix - the call
    returning ``(False, None)`` and raising nothing - flips this to an
    unexpected pass (forcing the test to be updated) rather than being
    hidden."""
    result = call_tool_reply_with_empty_history(live_group_tool_executor_module)
    assert result == (False, None)
