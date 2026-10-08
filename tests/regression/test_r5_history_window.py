"""R5 (CLAUDE.md bug class 10): history resend / tool-safe truncation window.

AG2's ``GroupChat`` broadcasts every message to every agent; without a
bounding transform, an agent dynamically routed into an already-long
conversation re-pays for the entire accumulated history on every turn. The
stock ``MessageHistoryLimiter`` cuts strictly by count, which can land the
window boundary between an assistant message's ``tool_calls`` and its
matching ``tool_result`` - the Anthropic API rejects a ``"tool"``-role
message not immediately preceded by the assistant turn that issued it.
``ToolSafeMessageHistoryLimiter`` (``cmbagent/hand_offs.py``) walks the
window forward past any such orphan.

Bite check, both halves automatic:

- The limiter's own properties (checks 1-4 below): the class didn't exist
  before commit ``5502d23``, so there's no pre-fix variant of *it* to load -
  the stock ``MessageHistoryLimiter`` control (check 5) is what demonstrates
  why the subclass exists, and bites on its own, no baseline import needed.
- Registration (check 6): ``bite_check.py`` loads ``cmbagent/hand_offs.py``
  from ``5502d23^`` (the commit immediately before the class was introduced)
  and confirms the five heavy agents come back with *no* transform at all.
"""

from __future__ import annotations

import inspect

import pytest
from autogen.agentchat.contrib.capabilities.transforms import MessageHistoryLimiter

from tests.regression._checks import (
    alternating_tool_history,
    assert_pairs_intact,
    extract_dict_literal,
    multi_call_tool_history,
    registered_transforms,
    run_register_all_hand_offs,
    strip_kept_first,
)

HEAVY_WORKER_WINDOWS = {
    "engineer": 20,
    "researcher": 20,
    "inspirehep_context": 70,
    "cadabra_context": 20,
    "derivation_checker": 20,
}


def _make_limiter(live_hand_offs_module, max_messages, keep_first_message=True):
    return live_hand_offs_module.ToolSafeMessageHistoryLimiter(
        max_messages=max_messages, keep_first_message=keep_first_message
    )


# ---------------------------------------------------------------------------
# Limiter properties
# ---------------------------------------------------------------------------


def test_below_window_is_a_no_op(live_hand_offs_module):
    limiter = _make_limiter(live_hand_offs_module, max_messages=20)
    history = alternating_tool_history(n_pairs=3)  # 7 messages, well under 20
    assert limiter.apply_transform(history) == history


@pytest.mark.parametrize("max_messages", [5, 10, 20])
@pytest.mark.parametrize("keep_first_message", [True, False])
def test_window_size_is_respected(live_hand_offs_module, max_messages, keep_first_message):
    limiter = _make_limiter(live_hand_offs_module, max_messages, keep_first_message)
    history = alternating_tool_history(n_pairs=30)  # 61 messages, well over any window above
    out = limiter.apply_transform(history)
    assert len(out) <= max_messages


@pytest.mark.parametrize("cut_offset", range(6))
def test_no_orphaned_leading_tool_result(live_hand_offs_module, cut_offset):
    """Sweep the cut point across every parity (even/odd message count,
    different window sizes) so the boundary actually lands on a tool result
    at least once - which is exactly the case the plain limiter mishandles."""
    max_messages = 10 + cut_offset
    limiter = _make_limiter(live_hand_offs_module, max_messages, keep_first_message=True)
    history = alternating_tool_history(n_pairs=20)
    out = limiter.apply_transform(history)
    non_kept = strip_kept_first(out, history)
    if non_kept:
        assert non_kept[0].get("role") != "tool"


@pytest.mark.parametrize("max_messages", [6, 9, 12, 15, 18])
def test_no_orphaned_leading_tool_result_multi_call_turns(live_hand_offs_module, max_messages):
    """The exact history shape (assistant turns issuing several tool calls
    at once) that strands the stock ``MessageHistoryLimiter`` - see
    ``test_stock_limiter_is_the_negative_control_it_bites_on_its_own`` - at
    the same window sizes where it fails. ``ToolSafeMessageHistoryLimiter``
    must not.

    ``max_messages=3`` is deliberately excluded here: with
    ``calls_per_turn=2`` its budget (2, after the kept first message) exactly
    matches the trailing pair of tool results, so the whole tail gets
    stripped and ``non_kept`` is empty - the assertion below would pass
    vacuously without exercising anything. That degenerate case is its own
    explicit test, ``test_fully_collapsed_window_still_safe``, below."""
    limiter = _make_limiter(live_hand_offs_module, max_messages, keep_first_message=True)
    history = multi_call_tool_history(n_turns=15, calls_per_turn=2)
    out = limiter.apply_transform(history)
    non_kept = strip_kept_first(out, history)
    assert non_kept, "expected a non-empty tail at this window size - test parametrization may need revisiting"
    assert non_kept[0].get("role") != "tool"
    assert_pairs_intact(out)


def test_fully_collapsed_window_still_safe(live_hand_offs_module):
    """The degenerate case excluded from the parametrized test above: a
    window so small its entire budget is consumed by a trailing run of tool
    results. The whole tail is correctly dropped rather than stranding an
    orphan - ``assert_pairs_intact`` holds trivially since no tool-role
    message survives into the output at all."""
    limiter = _make_limiter(live_hand_offs_module, max_messages=3, keep_first_message=True)
    history = multi_call_tool_history(n_turns=15, calls_per_turn=2)
    out = limiter.apply_transform(history)
    assert out == [history[0]]
    assert_pairs_intact(out)


def test_tool_call_pairs_never_split(live_hand_offs_module):
    limiter = _make_limiter(live_hand_offs_module, max_messages=13, keep_first_message=True)
    history = alternating_tool_history(n_pairs=20)
    out = limiter.apply_transform(history)
    assert_pairs_intact(out)


def test_stock_limiter_is_the_negative_control_it_bites_on_its_own():
    """The plain ``MessageHistoryLimiter`` this subclass replaces only
    protects a *single* boundary slot (``transforms.py``'s
    ``remaining_count == 1`` special case checks exactly one message's
    role) - it still leaves an orphaned tool result at the front of the
    window whenever a run of two or more consecutive tool results crosses
    that boundary, which happens whenever one assistant turn issues more
    than one tool call at once. Strict 1:1 alternation (one tool call, one
    result, repeat) happens not to expose this - the single checked slot
    always lines up correctly in that case - so this needs
    ``multi_call_tool_history``, not ``alternating_tool_history``, to
    actually demonstrate the gap. This is the bite for checks 1-4 above: no
    baseline import needed, the stock class ships in this same venv."""
    limiter = MessageHistoryLimiter(max_messages=12, keep_first_message=True)
    history = multi_call_tool_history(n_turns=15, calls_per_turn=2)
    out = limiter.apply_transform(history)
    non_kept = strip_kept_first(out, history)
    assert non_kept and non_kept[0].get("role") == "tool", (
        "expected the stock limiter to strand an orphaned tool result here; "
        "if it didn't, this is no longer a valid negative control"
    )


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------


def test_heavy_worker_windows_fixture_matches_source(live_hand_offs_module):
    """Guard this test file's own ``HEAVY_WORKER_WINDOWS`` fixture against
    silently drifting from ``cmbagent/hand_offs.py``'s real
    ``heavy_worker_window_sizes`` dict. Without this, a future change there
    (a renamed, added, or re-windowed agent) would get zero regression
    coverage - ``test_heavy_workers_registered_with_expected_windows`` below
    only ever iterates this file's own hardcoded dict, not the real one."""
    source = inspect.getsource(live_hand_offs_module)
    real_windows = extract_dict_literal(source, "heavy_worker_window_sizes")
    assert real_windows == HEAVY_WORKER_WINDOWS


def test_heavy_workers_registered_with_expected_windows(live_hand_offs_module):
    stub = run_register_all_hand_offs(live_hand_offs_module)
    for agent_name, expected_window in HEAVY_WORKER_WINDOWS.items():
        agent = stub.get_agent_object_from_name(agent_name).agent
        transforms = registered_transforms(agent)
        assert len(transforms) == 1, f"{agent_name}: expected exactly one registered transform"
        (transform,) = transforms
        assert type(transform).__name__ == "ToolSafeMessageHistoryLimiter"
        assert transform._max_messages == expected_window
        assert transform._keep_first_message is True


def test_controller_and_terminator_keep_stock_limiters_negative_control(live_hand_offs_module):
    stub = run_register_all_hand_offs(live_hand_offs_module)

    controller_transforms = registered_transforms(stub.get_agent_object_from_name("controller").agent)
    (controller_transform,) = controller_transforms
    assert isinstance(controller_transform, MessageHistoryLimiter)
    assert controller_transform._max_messages == 5

    terminator_transforms = registered_transforms(stub.get_agent_object_from_name("terminator").agent)
    (terminator_transform,) = terminator_transforms
    assert isinstance(terminator_transform, MessageHistoryLimiter)
    assert terminator_transform._max_messages == 1


# ---------------------------------------------------------------------------
# Burst case: a run of tool messages longer than the window (open bug)
# ---------------------------------------------------------------------------


def _all_tool_tail_history(n_pairs: int) -> list[dict]:
    """A history whose tail (within any plausible window) is entirely tool
    results with no interleaved assistant turn - e.g. several tool calls
    issued in one assistant turn, each with a separate result message."""
    history = [{"role": "user", "content": "task"}]
    history.append(
        {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {"id": f"call_{i}", "type": "function", "function": {"name": "search", "arguments": "{}"}}
                for i in range(n_pairs)
            ],
        }
    )
    history.extend({"role": "tool", "tool_call_id": f"call_{i}", "content": "result"} for i in range(n_pairs))
    return history


def test_burst_today_returns_first_message_only(live_hand_offs_module):
    """Characterization of current behaviour, not desired behaviour. Phase 3
    of docs/prompt_caching_plan.md ("cache-friendly history window") is
    expected to change this - when it does, this test and the xfail below
    must be updated together, with the reason recorded (the plan's C4
    requirement)."""
    limiter = _make_limiter(live_hand_offs_module, max_messages=10, keep_first_message=True)
    history = _all_tool_tail_history(n_pairs=15)
    out = limiter.apply_transform(history)
    assert out == [history[0]]


def test_burst_today_returns_empty_without_keep_first(live_hand_offs_module):
    """The other half of what the caching plan warns about: with
    ``keep_first_message=False`` the burst case returns an empty history."""
    limiter = _make_limiter(live_hand_offs_module, max_messages=10, keep_first_message=False)
    history = _all_tool_tail_history(n_pairs=15)
    assert limiter.apply_transform(history) == []


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="burst case unfixed; see docs/prompt_caching_plan.md Phase 3",
)
def test_burst_should_extend_window_backwards(live_hand_offs_module):
    """The agreed-but-unimplemented fix: extend the window backwards rather
    than return an empty or first-message-only history.

    ``raises=AssertionError`` narrows the xfail to exactly this bug: today
    ``apply_transform`` returns a plain value (``[history[0]]``, see
    ``test_burst_today_returns_first_message_only``), so it's this test's own
    ``assert len(out) > 1`` that fails, not some other, unrelated exception
    from the limiter itself. If a future change made the call raise instead
    of returning a too-short list, that would surface as a loud, unexpected
    failure here rather than being silently absorbed as the same old xfail."""
    limiter = _make_limiter(live_hand_offs_module, max_messages=10, keep_first_message=True)
    history = _all_tool_tail_history(n_pairs=15)
    out = limiter.apply_transform(history)
    assert len(out) > 1
    assert out[1].get("role") != "tool"
    assert_pairs_intact(out)
