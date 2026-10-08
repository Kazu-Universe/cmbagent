#!/usr/bin/env python
"""Bite check for the Tier 1 regression suite.

Not named ``test_*`` - pytest never collects this. Run directly:

    python tests/regression/bite_check.py

For every fix the suite in ``test_r*.py`` guards, this loads the pre-fix
baseline (see ``_baseline.py``: ag2 commit ``385340d4``, or for R5's
registration check, this repo's own commit ``5502d23^``) and re-runs the
*exact same* assertion the live test makes, confirming it fails without the
fix. Paste the printed table into the commit message as the "bites: yes"
evidence CLAUDE.md requires.

A row marked "bite" is expected to fail against the baseline (BITES); one
row (R4's fifth guarded site) is expected to hold even against the baseline,
because a *different*, upstream guard already covers it there - that is
declared as "no_bite", not silently tolerated.

Each "bite" row also declares the specific exception type the *historical
bug* is expected to raise (``UnboundLocalError``, ``IndexError``, or
``AssertionError`` when the bite is the check's own comparison failing, not
a raw crash). If the baseline raises something else instead, that is reported
as ``ERROR (unexpected exception type)`` rather than ``BITES`` - a mismatch
there means a bug in this harness itself (a typo, a signature change) is
masquerading as confirmation of the historical bug, and must not be read as
one.

Exit codes: ``0`` every row matched its expected outcome and none were
skipped; ``1`` some row's outcome didn't match (a real failure, including
``ERROR``); ``2`` no failures, but at least one row was SKIPPED (baseline
unavailable) - evidence is incomplete, not confirmed, and should not be
pasted into a commit message as "bites: yes" until it's re-run clean.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Allow `python tests/regression/bite_check.py` to work directly, not just
# `python -m tests.regression.bite_check` - put the repo root (two levels up
# from this file) on sys.path so `tests.regression` is importable either way.
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from tests.regression import _baseline, _checks  # noqa: E402

# Each row loads its own baseline module fresh. A tiny cache avoids repeated
# `git show` + tempfile round-trips for the ag2 baselines, which several
# R4 rows share.
_module_cache: dict[str, object] = {}


def _cached(key: str, loader):
    if key not in _module_cache:
        _module_cache[key] = loader()
    return _module_cache[key]


def _anthropic_baseline():
    return _cached("anthropic", _baseline.load_ag2_baseline_anthropic)


def _conversable_agent_baseline():
    return _cached("conversable_agent", _baseline.load_ag2_baseline_conversable_agent)


def _group_tool_executor_baseline():
    return _cached("group_tool_executor", _baseline.load_ag2_baseline_group_tool_executor)


def _hand_offs_baseline():
    return _cached("hand_offs", _baseline.load_cmbagent_baseline_hand_offs)


# ---------------------------------------------------------------------------
# One zero-arg "action" per row: perform the same assertion the live test
# makes, against the baseline. kind="bite" means we expect it to raise;
# kind="no_bite" means we expect it to hold even against the baseline.
# `expect_raises` (only meaningful for kind="bite") names the specific
# exception type the historical bug itself raises - AssertionError when the
# bite is the check's own comparison failing, a narrower type when the bug
# raises before any assertion in the check body even runs. A "no_bite" row
# always accepts any Exception, since any exception there is itself the
# finding (an unexpected bite), regardless of type.
# ---------------------------------------------------------------------------

CHECKS: list[tuple[str, str, object, type]] = []


def add(name: str, kind: str, action, expect_raises: type = AssertionError):
    CHECKS.append((name, kind, action, expect_raises))


def _check_r1_tool_choice_translation():
    mod = _anthropic_baseline()
    sent = _checks.sent_tool_choice(mod, {"type": "function", "function": {"name": "record_plan"}})
    assert sent == {"type": "tool", "name": "record_plan"}, f"expected translation, got {sent!r}"


add("R1 tool_choice translation", "bite", _check_r1_tool_choice_translation, AssertionError)


def _check_r3_empty_tool_calls():
    mod = _group_tool_executor_baseline()
    # The bug is the raw UnboundLocalError raised inside the call itself;
    # the trailing assert is only reached on the fixed code path.
    result = _checks.call_empty_tool_calls_reply(mod)
    assert result == (False, None)


add("R3 empty-but-present tool_calls", "bite", _check_r3_empty_tool_calls, UnboundLocalError)


def _check_r4(method_name: str, is_async: bool):
    def action():
        mod = _conversable_agent_baseline()
        # Likewise: IndexError is raised by `messages[-1]` inside the
        # library method before the assert below is ever reached.
        if is_async:
            result = _checks.call_empty_history_async(mod, method_name)
        else:
            result = _checks.call_empty_history_sync(mod, method_name)
        assert result == (False, None)

    return action


add("R4 generate_tool_calls_reply([])", "bite", _check_r4("generate_tool_calls_reply", is_async=False), IndexError)
add(
    "R4 generate_function_call_reply([])", "bite", _check_r4("generate_function_call_reply", is_async=False), IndexError
)
add(
    "R4 a_generate_tool_calls_reply([])", "bite", _check_r4("a_generate_tool_calls_reply", is_async=True), IndexError
)
add(
    "R4 a_generate_function_call_reply([])",
    "bite",
    _check_r4("a_generate_function_call_reply", is_async=True),
    IndexError,
)
add(
    "R4 check_termination_and_human_reply([])",
    "no_bite",
    _check_r4("check_termination_and_human_reply", is_async=False),
)


def _check_r4_markers():
    # Reuses the source already fetched to build the cached baseline module
    # (stashed as `__regression_baseline_source__`) instead of a second
    # `git show` round-trip for identical content.
    mod = _conversable_agent_baseline()
    source = mod.__regression_baseline_source__
    marker_count = _checks.guard_marker_count(source)
    guard_count = _checks.not_messages_count(source)
    assert (marker_count, guard_count) == (5, 6), f"baseline has ({marker_count}, {guard_count}), expected (5, 6)"


add("R4 guard marker count (venv-rebuild detector)", "bite", _check_r4_markers, AssertionError)


def _check_r4_empty_messages_conversion():
    mod = _anthropic_baseline()
    # IndexError is raised inside oai_messages_to_anthropic_messages itself
    # (processed_messages[-1] on an empty list) before the assert below.
    result = _checks.convert_empty_messages(mod)
    assert result == [{"content": "Please continue.", "role": "user"}]


add("R4 oai_messages_to_anthropic_messages([])", "bite", _check_r4_empty_messages_conversion, IndexError)


def _check_r5_stock_limiter_orphan():
    # No baseline needed: the stock MessageHistoryLimiter this class replaces
    # ships in the same venv and already mishandles the orphan case - the
    # negative control bites on its own. Needs a multi-tool-call-per-turn
    # history (not strict 1:1 alternation) - see test_r5_history_window.py's
    # docstring on why.
    from autogen.agentchat.contrib.capabilities.transforms import MessageHistoryLimiter

    history = _checks.multi_call_tool_history(n_turns=15, calls_per_turn=2)
    limiter = MessageHistoryLimiter(max_messages=12, keep_first_message=True)
    out = limiter.apply_transform(history)
    _checks.assert_pairs_intact(out)  # raises AssertionError on the orphan it finds


add("R5 stock MessageHistoryLimiter orphan (no baseline needed)", "bite", _check_r5_stock_limiter_orphan, AssertionError)


def _check_r5_heavy_worker_registration():
    from tests.regression.test_r5_history_window import HEAVY_WORKER_WINDOWS

    mod = _hand_offs_baseline()
    stub = _checks.run_register_all_hand_offs(mod)
    for agent_name, expected_window in HEAVY_WORKER_WINDOWS.items():
        agent = stub.get_agent_object_from_name(agent_name).agent
        transforms = _checks.registered_transforms(agent)
        assert len(transforms) == 1, f"{agent_name}: expected exactly one registered transform, got {transforms!r}"
        (transform,) = transforms
        assert type(transform).__name__ == "ToolSafeMessageHistoryLimiter"
        assert transform._max_messages == expected_window


add("R5 heavy-worker registration (cmbagent@5502d23^)", "bite", _check_r5_heavy_worker_registration, AssertionError)


def _check_r5_controller_negative_control():
    # Sanity check that the stub genuinely exercises the baseline function at
    # all: controller's own stock limiter predates this fix and should still
    # be there, unaffected.
    mod = _hand_offs_baseline()
    stub = _checks.run_register_all_hand_offs(mod)
    agent = stub.get_agent_object_from_name("controller").agent
    transforms = _checks.registered_transforms(agent)
    assert len(transforms) == 1
    (transform,) = transforms
    assert type(transform).__name__ == "MessageHistoryLimiter"
    assert transform._max_messages == 5


add("R5 controller negative control (sanity, not a bite)", "no_bite", _check_r5_controller_negative_control)


# ---------------------------------------------------------------------------
# Known open items: reproduced by the live suite as strict xfails, not
# guarded fixes - nothing to bite-check against a baseline.
# ---------------------------------------------------------------------------

OPEN_ITEMS = [
    "R3 sibling: _generate_group_tool_reply(messages=[]) still raises IndexError (xfail, test_r3)",
    "R5 burst case: all-tool-tail window still returns first-message-only / empty (xfail, test_r5)",
]


def main() -> int:
    rows = []
    for name, kind, action, expect_raises in CHECKS:
        # no_bite rows always accept any Exception as "it bit" - the type
        # doesn't matter there, any exception at all is the finding. bite
        # rows are narrowed to the specific historical-bug exception type, so
        # a harness bug raising something else is reported distinctly rather
        # than misread as confirmation.
        caught_type = expect_raises if kind == "bite" else Exception
        try:
            action()
        except _baseline.BaselineUnavailable as exc:
            rows.append((name, "SKIP", str(exc)))
            continue
        except caught_type as exc:
            outcome_raised, detail = True, f"{type(exc).__name__}: {exc}"
        except Exception as exc:
            rows.append(
                (
                    name,
                    "ERROR (unexpected exception type)",
                    f"{type(exc).__name__}: {exc} (expected {caught_type.__name__})",
                )
            )
            continue
        else:
            outcome_raised, detail = False, "assertion held"

        if kind == "bite":
            status = "BITES" if outcome_raised else "NO BITE (unexpected!)"
        else:
            status = "NO BITE (expected)" if not outcome_raised else "UNEXPECTED BITE"
        rows.append((name, status, detail))

    name_width = max(len(name) for name, _, _ in rows)
    for name, status, detail in rows:
        print(f"{name.ljust(name_width)} {status:<34} {detail}")

    print()
    print("Known open items (not bite-checked - no fix exists yet):")
    for item in OPEN_ITEMS:
        print(f"  - {item}")

    failed = [
        name
        for name, status, _ in rows
        if status in ("NO BITE (unexpected!)", "UNEXPECTED BITE") or status.startswith("ERROR")
    ]
    if failed:
        print()
        print(f"FAILED: {len(failed)} row(s) did not match their expected outcome: {', '.join(failed)}")
        return 1

    skipped = [name for name, status, _ in rows if status == "SKIP"]
    if skipped:
        print()
        print(
            f"INCOMPLETE: {len(skipped)} row(s) were SKIPPED (baseline unavailable), not confirmed: "
            f"{', '.join(skipped)}. This does NOT satisfy CLAUDE.md's bite-check requirement for those "
            "rows - fix the ag2 checkout / AG2_FORK_DIR and re-run before citing this output as evidence."
        )
        return 2

    return 0


if __name__ == "__main__":
    sys.exit(main())
