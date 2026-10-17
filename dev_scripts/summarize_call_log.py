#!/usr/bin/env python
"""Summarise a per-call usage log written with CMBAGENT_CALL_LOG (Phase 0 of
docs/prompt_caching_plan.md).

    python dev_scripts/summarize_call_log.py calls.jsonl [--gap 300]
        [--churn-threshold 0.10] [--gap-threshold 0.25] [--min-cacheable 512]

It answers the questions that gate the later phases:

- Obstacle 2 (system prompt changes within a step -> Phase 4). Only
  consecutive calls of one agent in the same process (`pid`) and the same plan
  step (`step`) are compared, so a legitimate change at a step boundary is not
  counted. Where both steps are unknown (`step` None, e.g. the agent had no
  context variables) the pair could be a step boundary, so only "flip-flops"
  are counted: a change back to a system hash already seen for that agent in
  that pid. A pair with one known and one unknown step is not compared. The
  summary reports the share of records with `step` None: if it is high the
  step field is not working and the verdict rests on the fallback.
- Obstacle 1 (sliding history window -> Phase 3): how often does
  `first_msg_sha256` change while the system block did not, between calls of
  one pid in the same known step (or with both steps unknown)? A change at a
  step boundary is the next step's input, not a sliding window.
- Obstacle 3 (long gaps -> Phase 5): gaps between an agent's consecutive calls
  with the same pid and the same system hash (a cache hit was possible), and
  how many exceed `--gap` seconds (the 5-minute cache TTL).

Pairs are always formed within one (agent, pid), so several processes can
append to one log file; the per-agent table merges them.

Gaps are differences between the logged response timestamps, so each is
approximate to within one call's latency.

The three verdict lines print the numbers and thresholds they used. They are
a prompt for a decision, not a substitute for it. Standard library only.
"""

from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
from collections import defaultdict

DEFAULT_GAP_S = 300.0
DEFAULT_CHURN_THRESHOLD = 0.10
DEFAULT_GAP_THRESHOLD = 0.25
DEFAULT_MIN_CACHEABLE = 512


def load_records(lines):
    """Parse JSONL lines. Returns (records, skipped). Blank lines are ignored;
    a line is skipped (and counted) if it is not valid JSON (or too deeply
    nested to parse), not a JSON object, has an "error" key (the logger's own
    failure marker), has no finite numeric "ts" (a bool or NaN does not count),
    or has an "agent", "pid" or "model" of the wrong type - one malformed line
    must not abort the summary."""
    records, skipped = [], 0
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
        except (ValueError, RecursionError):
            skipped += 1
            continue
        if not isinstance(rec, dict) or "error" in rec or not _well_formed(rec):
            skipped += 1
            continue
        records.append(rec)
    return records, skipped


def _is_number(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _well_formed(rec):
    ts = rec.get("ts")
    if not _is_number(ts) or not math.isfinite(ts):
        return False
    # Records are grouped and sorted by these, so they must be hashable and comparable.
    if not (rec.get("agent") is None or isinstance(rec.get("agent"), str)):
        return False
    pid = rec.get("pid")
    if not (pid is None or isinstance(pid, str) or (isinstance(pid, int) and not isinstance(pid, bool))):
        return False
    return rec.get("model") is None or isinstance(rec.get("model"), str)


def _n(v):
    return v if isinstance(v, int) and not isinstance(v, bool) else 0


_PROMPT_TOKEN_FIELDS = ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens")


def _has_usage(rec):
    """True if the record carries at least one real prompt-token count."""
    return any(isinstance(rec.get(f), int) and not isinstance(rec.get(f), bool) for f in _PROMPT_TOKEN_FIELDS)


def _pair_kind(prev, cur):
    """How a consecutive pair of one agent's calls is compared for churn:
    "step" (same pid, same known step), "fallback" (same pid, both steps
    unknown) or None (not comparable)."""
    if prev.get("pid") != cur.get("pid"):
        return None
    sp, sc = prev.get("step"), cur.get("step")
    if sp is None and sc is None:
        return "fallback"
    if sp is not None and sp == sc:
        return "step"
    return None


def summarize(
    records,
    gap_s=DEFAULT_GAP_S,
    churn_threshold=DEFAULT_CHURN_THRESHOLD,
    gap_threshold=DEFAULT_GAP_THRESHOLD,
    min_cacheable=DEFAULT_MIN_CACHEABLE,
    skipped=0,
):
    by_agent = defaultdict(list)
    for rec in records:
        by_agent[rec.get("agent") or "(none)"].append(rec)

    agents = {}
    pairs = changes = fallback_pairs = slides = slide_pairs = gap_count = gaps_over = 0
    for name, recs in sorted(by_agent.items()):
        recs = sorted(recs, key=lambda r: r["ts"])
        a_changes = a_slides = 0
        gaps = []
        # Pairs are formed within one (agent, pid): two processes appending to
        # one log interleave in time, and walking the merged sequence would
        # only ever see cross-pid pairs.
        by_pid = defaultdict(list)
        for rec in recs:
            by_pid[rec.get("pid")].append(rec)
        for run in by_pid.values():
            seen = {run[0].get("system_sha256")} - {None}  # system hashes seen so far in this run
            for prev, cur in zip(run, run[1:]):
                sys_prev, sys_cur = prev.get("system_sha256"), cur.get("system_sha256")
                # A record without a system hash is unknown, not a system block of its
                # own: pairs involving one are not compared at all.
                known = sys_prev is not None and sys_cur is not None
                kind = _pair_kind(prev, cur) if known else None
                if kind == "step":
                    pairs += 1
                    if sys_prev != sys_cur:
                        a_changes += 1
                        changes += 1
                elif kind == "fallback":
                    pairs += 1
                    fallback_pairs += 1
                    # Could be a step boundary: count only a return to a hash seen before.
                    if sys_prev != sys_cur and sys_cur in seen:
                        a_changes += 1
                        changes += 1
                if known and sys_prev == sys_cur:
                    # Same system block: a cache hit was possible, so the gap matters.
                    gaps.append(cur["ts"] - prev["ts"])
                    # A first-message change is a window slide only inside one known
                    # step (or when both steps are unknown); at a step boundary it is
                    # just the next step's input.
                    if kind is not None:
                        slide_pairs += 1
                        if prev.get("first_msg_sha256") != cur.get("first_msg_sha256"):
                            a_slides += 1
                if sys_cur is not None:
                    seen.add(sys_cur)
        a_gaps_over = sum(1 for g in gaps if g > gap_s)
        agents[name] = {
            "calls": len(recs),
            "models": sorted({r.get("model") for r in recs if r.get("model")}),
            "input_tokens": sum(_n(r.get("input_tokens")) for r in recs),
            "output_tokens": sum(_n(r.get("output_tokens")) for r in recs),
            "cache_read_tokens": sum(_n(r.get("cache_read_input_tokens")) for r in recs),
            "cache_write_tokens": sum(_n(r.get("cache_creation_input_tokens")) for r in recs),
            "distinct_system": len({r.get("system_sha256") for r in recs} - {None}),
            "system_changes": a_changes,
            "window_slides": a_slides,
            "median_gap_s": statistics.median(gaps) if gaps else None,
            "max_gap_s": max(gaps) if gaps else None,
            "gaps_over": a_gaps_over,
            # Calls whose whole prompt is under the minimum cacheable length
            # get no benefit from caching, whatever else we do. A record with
            # no usable token counts is missing data, not a short prompt.
            "short_calls": sum(
                1
                for r in recs
                if _has_usage(r)
                and _n(r.get("input_tokens"))
                + _n(r.get("cache_read_input_tokens"))
                + _n(r.get("cache_creation_input_tokens"))
                < min_cacheable
            ),
            "no_usage_calls": sum(1 for r in recs if not _has_usage(r)),
        }
        slides += a_slides
        gap_count += len(gaps)
        gaps_over += a_gaps_over

    churn_rate = changes / pairs if pairs else 0.0
    gap_rate = gaps_over / gap_count if gap_count else 0.0
    step_none = sum(1 for r in records if r.get("step") is None)
    verdict = {
        "phase4_system_churn": {
            "needed": churn_rate >= churn_threshold,
            "rate": churn_rate,
            "changes": changes,
            "pairs": pairs,
            "fallback_pairs": fallback_pairs,
            "threshold": churn_threshold,
        },
        "phase5_long_gaps": {
            "needed": gap_rate >= gap_threshold,
            "rate": gap_rate,
            "gaps_over": gaps_over,
            "gaps": gap_count,
            "threshold": gap_threshold,
            "gap_s": gap_s,
        },
        "phase3_window_sliding": {"observed": slides > 0, "slides": slides, "pairs": slide_pairs},
    }
    return {
        "calls": len(records),
        "skipped": skipped,
        "agents": agents,
        "no_usage": sum(a["no_usage_calls"] for a in agents.values()),
        "step": {
            "none": step_none,
            "total": len(records),
            "share": step_none / len(records) if records else 0.0,
        },
        "verdict": verdict,
    }


def _fmt_s(v):
    return "-" if v is None else f"{v:.0f}"


def render(summary):
    lines = []
    cols = (
        "agent calls in_tok out_tok cache_rd cache_wr sys_distinct sys_chg win_slide "
        "med_gap_s max_gap_s gaps>ttl short"
    ).split()
    rows = []
    for name, a in summary["agents"].items():
        rows.append(
            [
                name,
                a["calls"],
                a["input_tokens"],
                a["output_tokens"],
                a["cache_read_tokens"],
                a["cache_write_tokens"],
                a["distinct_system"],
                a["system_changes"],
                a["window_slides"],
                _fmt_s(a["median_gap_s"]),
                _fmt_s(a["max_gap_s"]),
                a["gaps_over"],
                a["short_calls"],
            ]
        )
    widths = [max(len(str(x)) for x in [c] + [r[i] for r in rows]) for i, c in enumerate(cols)]
    lines.append("  ".join(c.ljust(w) for c, w in zip(cols, widths)))
    for r in rows:
        lines.append("  ".join(str(x).ljust(w) for x, w in zip(r, widths)))
    lines.append("")
    lines.append(f"{summary['calls']} call(s) summarised, {summary['skipped']} line(s) skipped (malformed or error records).")
    st = summary["step"]
    step_line = f"{st['none']}/{st['total']} records have step None ({st['share']:.0%})."
    if st["total"] and st["share"] == 1.0:
        step_line += " The step field appears unset: Phase 4 rests on the flip-flop fallback only."
    lines.append(step_line)
    if summary["no_usage"]:
        lines.append(
            f"{summary['no_usage']} call(s) had no usable token counts (excluded from the short-call count)."
        )
    v = summary["verdict"]
    p4, p5, p3 = v["phase4_system_churn"], v["phase5_long_gaps"], v["phase3_window_sliding"]
    lines.append(
        f"Phase 4 needed? {'YES' if p4['needed'] else 'no'} - system block changed within a step in "
        f"{p4['changes']}/{p4['pairs']} comparable consecutive calls ({p4['rate']:.1%}; threshold "
        f"{p4['threshold']:.0%}; {p4['fallback_pairs']} of those pairs used the flip-flop fallback)."
    )
    lines.append(
        f"Phase 5 needed? {'YES' if p5['needed'] else 'no'} - {p5['gaps_over']}/{p5['gaps']} gaps exceed "
        f"{p5['gap_s']:.0f}s ({p5['rate']:.1%}; threshold {p5['threshold']:.0%}; same-system gaps only)."
    )
    lines.append(
        f"Window sliding observed? {'YES' if p3['observed'] else 'no'} - first message changed with the "
        f"system block unchanged in {p3['slides']}/{p3['pairs']} consecutive calls."
    )
    return "\n".join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("log", help="JSONL file written with CMBAGENT_CALL_LOG")
    ap.add_argument("--gap", type=float, default=DEFAULT_GAP_S, help="TTL in seconds (default 300)")
    ap.add_argument("--churn-threshold", type=float, default=DEFAULT_CHURN_THRESHOLD)
    ap.add_argument("--gap-threshold", type=float, default=DEFAULT_GAP_THRESHOLD)
    ap.add_argument("--min-cacheable", type=int, default=DEFAULT_MIN_CACHEABLE)
    args = ap.parse_args(argv)
    try:
        # errors="replace": a partly written or concatenated log with bad bytes
        # gives garbage lines, which are skipped and counted like any other.
        with open(args.log, "r", encoding="utf-8", errors="replace") as f:
            records, skipped = load_records(f)
    except OSError as e:
        print(f"ERROR: cannot read {args.log}: {e}", file=sys.stderr)
        return 1
    print(
        render(
            summarize(
                records,
                gap_s=args.gap,
                churn_threshold=args.churn_threshold,
                gap_threshold=args.gap_threshold,
                min_cacheable=args.min_cacheable,
                skipped=skipped,
            )
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
