"""C0 (docs/prompt_caching_plan.md, Phase 0): per-call usage log.

When ``CMBAGENT_CALL_LOG`` is set, every Anthropic call appends one JSON line
(agent, model, input / cache-write / cache-read / output tokens, hashes of the
system block, tools list and first message). It must be a pure observer:
off by default, and with it on the request sent to the API and the completion
returned to ag2 are identical to the ones with it off.

The checks live in ``_checks.py`` so ``bite_check.py`` runs the same code
against the pre-patch baseline and against deliberately broken mutants (a
logger that mutates the request, one that raises, a writer that is memoised
by ``@lru_cache``, a switch that is always on...). The no-behaviour-change
tests cannot fail on the baseline, since the baseline has no logger at all, so
their bite evidence comes from those mutants.

Everything here is offline: the SDK client is a mock and nothing needs the
``ag2`` checkout or git. The patch script's own hygiene checks (idempotence,
non-zero exit on a missing anchor or partial patch) need the pre-patch source
and so live in ``bite_check.py``.
"""

from __future__ import annotations

import importlib.util
import inspect
import json
from pathlib import Path

import pytest

from tests.regression import _checks

_SUMMARIZER_PATH = Path(__file__).resolve().parents[2] / "dev_scripts" / "summarize_call_log.py"


@pytest.fixture(scope="module")
def summarizer():
    spec = importlib.util.spec_from_file_location("summarize_call_log", _SUMMARIZER_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# ---------------------------------------------------------------------------
# The logger: inert when off, a pure observer when on
# ---------------------------------------------------------------------------


def test_off_is_inert(live_anthropic_module):
    _checks.check_off_is_inert(live_anthropic_module)


def test_wrapper_off_writes_nothing(live_client_module, live_anthropic_module, tmp_path):
    _checks.check_wrapper_off_writes_nothing(live_client_module, live_anthropic_module, tmp_path / "calls.jsonl")


def test_on_sends_identical_request(live_anthropic_module):
    _checks.check_on_sends_identical_request(live_anthropic_module)


def test_on_returns_identical_response(live_anthropic_module):
    _checks.check_on_returns_identical_response(live_anthropic_module)


def test_logged_when_create_raises(live_client_module, live_anthropic_module, tmp_path):
    # Finding 1 of the review: the SDK call was billed, then create() raised.
    _checks.check_logged_when_create_raises(live_client_module, live_anthropic_module, tmp_path / "calls.jsonl")


def test_unwritable_path_never_raises(live_client_module, live_anthropic_module, tmp_path):
    # A directory can't be opened for append: the call must still succeed.
    _checks.check_unwritable_path_never_raises(live_client_module, live_anthropic_module, tmp_path)


# ---------------------------------------------------------------------------
# The records
# ---------------------------------------------------------------------------


def test_record_fields(live_anthropic_module):
    _checks.check_record_fields(live_anthropic_module)


def test_magicmock_usage_not_coerced(live_anthropic_module):
    _checks.check_magicmock_usage_not_coerced(live_anthropic_module)


def test_record_builder_never_raises(live_anthropic_module):
    _checks.check_record_builder_never_raises(live_anthropic_module)


def test_wrapper_writes_agent_name(live_client_module, live_anthropic_module, tmp_path):
    _checks.check_wrapper_writes_agent_name(live_client_module, live_anthropic_module, tmp_path / "calls.jsonl")


def test_helper_not_lru_wrapped(live_client_module):
    _checks.check_helper_not_lru_wrapped(live_client_module)


# ---------------------------------------------------------------------------
# Coverage and venv-rebuild guards
# ---------------------------------------------------------------------------


def test_patch_markers_present(live_anthropic_module, live_client_module):
    # Fails if a venv rebuild dropped the patch (re-run patch_call_usage_log.py).
    _checks.check_patch_markers(inspect.getsource(live_anthropic_module), inspect.getsource(live_client_module))


def test_single_sdk_call_site(live_anthropic_module):
    # One hook only covers every API path while there is one call site. A
    # second path (beta, parse, stream) must get its own logging, not slip by.
    _checks.check_single_sdk_call_site(inspect.getsource(live_anthropic_module))


def test_single_sdk_call_site_checker_precision():
    # The matcher must not trip on `params.messages.append(...)` etc., and
    # must still catch a second SDK path (stream, beta, another client).
    _checks.check_single_sdk_call_site_precision()


# ---------------------------------------------------------------------------
# dev_scripts/summarize_call_log.py
# ---------------------------------------------------------------------------


def _rec(agent, ts, system="s1", first="f1", pid=1, step=None, **extra):
    rec = {
        "ts": ts,
        "pid": pid,
        "step": step,
        "agent": agent,
        "model": "claude-sonnet-5",
        "input_tokens": 1000,
        "cache_creation_input_tokens": None,
        "cache_read_input_tokens": None,
        "output_tokens": 10,
        "system_sha256": system,
        "first_msg_sha256": first,
    }
    rec.update(extra)
    return rec


def test_summarize_system_churn(summarizer):
    records = [
        _rec("engineer", 0, system="a", step=1),
        _rec("engineer", 10, system="a", step=1),
        _rec("engineer", 20, system="b", step=1),
        _rec("engineer", 30, system="b", step=1),
        _rec("researcher", 0, step=1),
        _rec("researcher", 10, step=1),
    ]
    summary = summarizer.summarize(records)
    assert summary["agents"]["engineer"]["system_changes"] == 1
    assert summary["agents"]["engineer"]["distinct_system"] == 2
    assert summary["agents"]["researcher"]["system_changes"] == 0
    churn = summary["verdict"]["phase4_system_churn"]
    assert (churn["changes"], churn["pairs"]) == (1, 4)
    assert churn["needed"] is True  # 25% >= the 10% default
    assert summarizer.summarize(records, churn_threshold=0.5)["verdict"]["phase4_system_churn"]["needed"] is False


def test_summarize_gaps(summarizer):
    # Out of order on purpose: gaps are between an agent's calls in time order.
    records = [_rec("a", 560), _rec("a", 0), _rec("a", 500), _rec("a", 100)]
    agent = summarizer.summarize(records)["agents"]["a"]
    assert agent["median_gap_s"] == 100 and agent["max_gap_s"] == 400
    assert agent["gaps_over"] == 1  # only the 400 s gap exceeds 300 s
    verdict = summarizer.summarize(records)["verdict"]["phase5_long_gaps"]
    assert (verdict["gaps_over"], verdict["gaps"]) == (1, 3) and verdict["needed"] is True
    assert summarizer.summarize(records, gap_s=1000)["agents"]["a"]["gaps_over"] == 0


def test_summarize_window_slide(summarizer):
    records = [
        _rec("a", 0, first="f1", step=1),
        _rec("a", 1, first="f2", step=1),  # window slid, system unchanged
        _rec("a", 2, first="f3", system="other", step=1),  # system changed: a change, not a slide
    ]
    agent = summarizer.summarize(records)["agents"]["a"]
    assert (agent["window_slides"], agent["system_changes"]) == (1, 1)
    assert summarizer.summarize(records)["verdict"]["phase3_window_sliding"]["observed"] is True
    steady = summarizer.summarize([_rec("a", 0), _rec("a", 1)])
    assert steady["verdict"]["phase3_window_sliding"]["observed"] is False


def test_summarize_skips_bad_lines(summarizer):
    lines = [
        json.dumps(_rec("a", 0)),
        "",
        "not json",
        json.dumps({"ts": 1, "error": "RuntimeError()"}),
        json.dumps([1, 2]),
        json.dumps({"agent": "a"}),  # no timestamp
    ]
    records, skipped = summarizer.load_records(lines)
    assert len(records) == 1 and skipped == 4


def test_summarize_tokens_and_short_calls(summarizer):
    records = [
        _rec("a", 0, input_tokens=100, cache_creation_input_tokens=300, cache_read_input_tokens=None),
        _rec("a", 1, input_tokens=20, cache_creation_input_tokens=0, cache_read_input_tokens=600),
        _rec("a", 2, input_tokens=5, cache_creation_input_tokens=None, cache_read_input_tokens=None),
    ]
    agent = summarizer.summarize(records)["agents"]["a"]
    assert (agent["input_tokens"], agent["cache_read_tokens"], agent["cache_write_tokens"]) == (125, 600, 300)
    # Whole-prompt totals: 400, 620, 5. Two are under 512, and with a
    # 1000-token minimum all three are short.
    assert agent["short_calls"] == 2
    assert summarizer.summarize(records, min_cacheable=1000)["agents"]["a"]["short_calls"] == 3


def test_summarize_cli(summarizer, tmp_path, capsys):
    log = tmp_path / "calls.jsonl"
    records = [_rec("a", 0, step=1), _rec("a", 400, step=1), _rec("a", 410, system="b", step=1)]
    log.write_text("\n".join(json.dumps(r) for r in records) + "\ngarbage\n")
    assert summarizer.main([str(log)]) == 0
    out = capsys.readouterr().out
    assert "Phase 4 needed? YES" in out and "Phase 5 needed? YES" in out  # 1/2 changes; the 400 s gap is a same-system gap
    assert "Window sliding observed? no" in out
    assert "0/3 records have step None" in out
    assert "1 line(s) skipped" in out
    assert summarizer.main([str(tmp_path / "missing.jsonl")]) == 1


def test_summarize_churn_counts_same_pid_and_step_only(summarizer):
    records = [
        _rec("engineer", 0, system="a", step=1),
        _rec("engineer", 1, system="a", step=1),
        _rec("engineer", 2, system="b", step=2),  # new step: a legitimate change, not churn
        _rec("engineer", 3, system="b", step=2),
        _rec("engineer", 4, system="c", step=2),  # a change inside a step: churn
        _rec("engineer", 100, system="z", step=2, pid=2),  # another run: not comparable
    ]
    summary = summarizer.summarize(records)
    churn = summary["verdict"]["phase4_system_churn"]
    assert (churn["changes"], churn["pairs"], churn["fallback_pairs"]) == (1, 3, 0)
    assert summary["agents"]["engineer"]["system_changes"] == 1


def test_summarize_flip_flops_when_step_is_unknown(summarizer):
    # Both steps None: a change could be a legitimate step boundary, so only
    # a return to a hash already seen for that agent in that pid counts.
    flip = [_rec("engineer", t, system=s) for t, s in enumerate(["s1", "s2", "s1", "s3"])]
    churn = summarizer.summarize(flip)["verdict"]["phase4_system_churn"]
    assert (churn["changes"], churn["pairs"], churn["fallback_pairs"]) == (1, 3, 3)  # only s2 -> s1

    monotonic = [_rec("engineer", t, system=s) for t, s in enumerate(["s1", "s2", "s3"])]
    assert summarizer.summarize(monotonic)["verdict"]["phase4_system_churn"]["changes"] == 0

    # "Already seen" is per agent and per pid: s1 was only seen in pid 1.
    other_pid = [
        _rec("engineer", 0, system="s1", pid=1),
        _rec("engineer", 1, system="s2", pid=2),
        _rec("engineer", 2, system="s1", pid=2),
    ]
    assert summarizer.summarize(other_pid)["verdict"]["phase4_system_churn"]["changes"] == 0


def test_summarize_mixed_step_pairs_are_not_compared(summarizer):
    records = [_rec("engineer", 0, system="a", step=1), _rec("engineer", 1, system="b", step=None)]
    churn = summarizer.summarize(records)["verdict"]["phase4_system_churn"]
    assert (churn["changes"], churn["pairs"]) == (0, 0)


def test_summarize_gaps_only_count_where_a_cache_hit_was_possible(summarizer):
    records = [
        _rec("a", 0, system="s1"),
        _rec("a", 500, system="s1"),  # same system: the 500 s gap counts
        _rec("a", 1500, system="s2"),  # prefix changed: no hit possible either way
        _rec("a", 1600, system="s2", pid=2),  # another run
    ]
    verdict = summarizer.summarize(records)["verdict"]["phase5_long_gaps"]
    assert (verdict["gaps_over"], verdict["gaps"]) == (1, 1)


def test_summarize_reports_share_of_records_with_step_none(summarizer):
    records = [_rec("a", 0, step=1), _rec("a", 1), _rec("a", 2), _rec("b", 3)]
    summary = summarizer.summarize(records)
    assert summary["step"] == {"none": 3, "total": 4, "share": 0.75}
    assert "3/4 records have step None (75%)" in summarizer.render(summary)
    assert "step field appears unset" in summarizer.render(summarizer.summarize([_rec("a", 0), _rec("a", 1)]))
    assert "step field appears unset" not in summarizer.render(summary)


def test_summarize_interleaved_runs_are_compared_per_pid(summarizer):
    # Two processes appending to one log interleave in time. Pairs must be
    # formed within one (agent, pid), not across the interleaving.
    pid1 = [_rec("engineer", t, system=s, pid=1, step=1) for t, s in [(0, "a"), (2, "b"), (4, "b")]]
    pid2 = [_rec("engineer", t, system="x", pid=2, step=1) for t in (1, 3, 5)]

    def churn(records):
        v = summarizer.summarize(records)["verdict"]
        return v["phase4_system_churn"]["changes"], v["phase4_system_churn"]["pairs"], v["phase5_long_gaps"]["gaps"]

    assert churn(pid1) == (1, 2, 1)
    assert churn(pid2) == (0, 2, 2)
    assert churn(pid1 + pid2) == (1, 4, 3), "interleaving changed the result"
    assert churn(pid2 + pid1) == (1, 4, 3)
    assert summarizer.summarize(pid1 + pid2)["agents"]["engineer"]["system_changes"] == 1
    assert summarizer.summarize(pid1 + pid2)["agents"]["engineer"]["calls"] == 6


def test_summarize_window_slides_need_the_same_known_step(summarizer):
    # A first-message change at a step boundary is not a sliding window.
    records = [
        _rec("a", 0, first="f1", step=1),
        _rec("a", 1, first="f2", step=1),  # same known step: a slide
        _rec("a", 2, first="f3", step=2),  # step boundary: not a slide
        _rec("a", 3, first="f4", step=None),  # one step unknown: not comparable
        _rec("a", 4, first="f5", step=None),  # both unknown: the old rule applies, a slide
    ]
    summary = summarizer.summarize(records)
    slides = summary["verdict"]["phase3_window_sliding"]
    assert (slides["slides"], slides["pairs"]) == (2, 2)
    assert summary["agents"]["a"]["window_slides"] == 2
    # Gaps are unaffected: every pair is same-pid, same-system.
    assert summary["verdict"]["phase5_long_gaps"]["gaps"] == 4


# ---------------------------------------------------------------------------
# Robustness of the summarizer on odd logs (third /code-review round)
# ---------------------------------------------------------------------------


def test_load_records_skips_non_finite_and_bool_timestamps(summarizer):
    lines = [
        '{"ts": NaN, "agent": "a"}',
        '{"ts": Infinity, "agent": "a"}',
        '{"ts": true, "agent": "a"}',
        json.dumps(_rec("a", 0)),
    ]
    records, skipped = summarizer.load_records(lines)
    assert len(records) == 1 and skipped == 3


def test_load_records_skips_odd_field_types(summarizer):
    # One malformed line must be counted as skipped, not abort the summary.
    lines = [
        json.dumps({"ts": 1, "agent": "a", "pid": [1]}),  # unhashable pid
        json.dumps({"ts": 2, "agent": 5, "pid": 1}),  # agent not a string
        json.dumps({"ts": 3, "agent": "a", "pid": 1, "model": 7}),  # model not a string
        json.dumps(_rec("a", 4)),
    ]
    records, skipped = summarizer.load_records(lines)
    assert len(records) == 1 and skipped == 3
    summarizer.summarize(records)  # must not raise


def test_summarize_cli_survives_undecodable_and_deeply_nested_lines(summarizer, tmp_path, capsys):
    log = tmp_path / "calls.jsonl"
    log.write_bytes(b"\xff\xfe\n" + json.dumps(_rec("a", 0)).encode() + b"\n" + b"[" * 100000 + b"\n")
    assert summarizer.main([str(log)]) == 0
    out = capsys.readouterr().out
    assert "1 call(s) summarised, 2 line(s) skipped" in out


def test_summarize_no_usage_records_are_not_short(summarizer):
    # The logger writes None when usage is absent: that is missing data, not a short prompt.
    blank = {"input_tokens": None, "cache_creation_input_tokens": None, "cache_read_input_tokens": None}
    records = [_rec("a", 0, **blank), _rec("a", 1, input_tokens=5)]
    summary = summarizer.summarize(records)
    assert summary["agents"]["a"]["short_calls"] == 1  # only the call that really had 5 tokens
    assert summary["no_usage"] == 1
    assert "1 call(s) had no usable token counts" in summarizer.render(summary)
    assert "had no usable token counts" not in summarizer.render(summarizer.summarize([_rec("a", 0)]))


def test_summarize_missing_system_hash_is_unknown_not_a_system(summarizer):
    no_system = {"system_sha256": None}
    records = [
        _rec("a", 0, step=1, **no_system),
        _rec("a", 1, step=1),  # a real hash after an unknown one: not comparable
        _rec("a", 2, step=1, **no_system),
    ]
    summary = summarizer.summarize(records)
    assert summary["agents"]["a"]["distinct_system"] == 1
    churn = summary["verdict"]["phase4_system_churn"]
    assert (churn["changes"], churn["pairs"]) == (0, 0)
    assert summary["verdict"]["phase5_long_gaps"]["gaps"] == 0  # no known cache hit between them


def test_summarize_empty_log_and_nameless_agent(summarizer, tmp_path, capsys):
    empty = summarizer.summarize([])
    assert empty["calls"] == 0 and empty["step"]["share"] == 0.0
    assert not empty["verdict"]["phase4_system_churn"]["needed"]
    assert "0 call(s) summarised" in summarizer.render(empty)
    log = tmp_path / "empty.jsonl"
    log.write_text("")
    assert summarizer.main([str(log)]) == 0
    # A record with no agent is reported under "(none)", not dropped.
    nameless = summarizer.summarize([_rec(None, 0), _rec("", 1)])
    assert nameless["agents"]["(none)"]["calls"] == 2


def test_summarize_threshold_boundaries(summarizer):
    # Churn: needed at exactly the threshold (>=). 1 change in 10 pairs, threshold 10%.
    records = [_rec("a", t, system="s1", step=1) for t in range(10)] + [_rec("a", 10, system="s2", step=1)]
    churn = summarizer.summarize(records, churn_threshold=0.10)["verdict"]["phase4_system_churn"]
    assert (churn["changes"], churn["pairs"], churn["needed"]) == (1, 10, True)
    assert summarizer.summarize(records, churn_threshold=0.11)["verdict"]["phase4_system_churn"]["needed"] is False
    # Gaps: over the TTL only if strictly greater than it.
    exact = [_rec("a", 0), _rec("a", 300)]
    assert summarizer.summarize(exact, gap_s=300)["agents"]["a"]["gaps_over"] == 0
    assert summarizer.summarize([_rec("a", 0), _rec("a", 300.5)], gap_s=300)["agents"]["a"]["gaps_over"] == 1
