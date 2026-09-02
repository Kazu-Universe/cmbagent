# PROJECT_STATUS.md — CMBAgentForHEPTH_wClaude

**Last updated:** 2026-08-28 (migration to Claude Team for Scientists account,
Claude Code introduced as the execution layer)

> Convention: update this file at the end of every work session — what
> changed, what's confirmed, what's open, and the exact next command.
> Read it first thing at the start of every session, then verify it
> against `git log` / `git status` before doing anything else.

---

## 0. Who / what

Kazu — theoretical physics (string theory, KK compactifications, black
hole thermodynamics) + astrophysical data analysis (Cobaya, CMB
likelihoods). India, UTC+5:30. New to git — walk through git ops one
command at a time. Ubuntu machine (Dell Latitude 5420).

`CMBAgentForHEPTH_wClaude` = fork of open-source **CMBAgent**
(AG2/AutoGen-based multi-agent research pipeline), extended with three
custom agents: `inspirehep_context`, `cadabra_context`,
`derivation_checker`.

Repos:
- `https://github.com/Kazu-Universe/cmbagent` (main fork)
- `https://github.com/Kazu-Universe/ag2` — **use branch
  `cmbagent-real-base`** (the old branch is deprecated, see §3)

Local paths:
- `~/Projects/CMBagentForHEPTH_wClaude/cmbagent`
- `~/Projects/CMBagentForHEPTH_wClaude/ag2`
- venv at `cmbagent/.venv`

---

## 1. Working style (as of this migration)

- Moved from full copy-paste relay (Claude chat ↔ Kazu's terminal) to
  **Claude Code in the terminal**, supervised by Kazu, with a Claude
  chat session available for higher-level planning/review.
- Permissions: **start conservative**. First Claude Code session should
  be **read-only** — inspect files and `git log`/`git status`, report
  back, no edits yet. Loosen gradually as trust builds.
- Reason for the switch: several past bugs (token-resend, wrong ag2
  fork base) were only resolved by reading real source directly — the
  old relay style couldn't do that, and files described-but-not-saved
  didn't persist across sessions/accounts.
- Reason to keep it disciplined: Kazu is currently engaging with this
  project sporadically (busy with other work) and has noticed reduced
  recall of "what I was doing" between sessions. This file exists to
  offload that continuity burden from memory onto something durable
  and versioned. Keep commits small, with messages that explain *why*,
  not just *what* — preserves the learning value the old relay style had.

---

## 2. Immediate next action — DO THIS FIRST

**Not yet confirmed whether two dictated commits from the last session
(pre-migration) actually landed.** First thing, read-only:

```bash
cd ~/Projects/CMBagentForHEPTH_wClaude/cmbagent
git log --oneline -5
git log origin/main..HEAD --oneline
```

Look for a commit like *"Tune per-agent history window sizes..."*. The
second command should be empty if already pushed.

- **If the commit is there:** the token-resend fix (§3 below) is live.
  Move to §4 (model routing) then §5 (physics task).
- **If not:** the fix needs to be (re)applied. Full exact content is in
  §3 — read the current `cmbagent/hand_offs.py` first, then apply the
  described change directly (this has already been fully investigated;
  no need to redo the debugging).

---

## 3. Token-resend bug — status: fixed & validated (re-verify it's live)

**Root cause:** AG2's `GroupChat` broadcasts every message to every
agent; without a bounding transform, a heavy agent dynamically routed
into an already-long conversation re-pays for the entire accumulated
history on every turn. `hand_offs.py` had bounding for cheap plumbing
agents but not for the five heavy LLM workers: `engineer`, `researcher`,
`inspirehep_context`, `cadabra_context`, `derivation_checker`.

**Fix:** a custom transform, `ToolSafeMessageHistoryLimiter` (like AG2's
`MessageHistoryLimiter` but never leaves an orphaned tool-result message
at the front of the truncated window, which the Anthropic API would
reject), registered per-agent in `register_all_hand_offs()` in
`hand_offs.py`:

```python
class ToolSafeMessageHistoryLimiter:
    def __init__(self, max_messages=None, keep_first_message=False):
        self._max_messages = max_messages
        self._keep_first_message = keep_first_message

    def apply_transform(self, messages):
        if self._max_messages is None or len(messages) <= self._max_messages:
            return messages
        kept_first = [messages[0]] if self._keep_first_message else []
        budget = self._max_messages - len(kept_first)
        if budget <= 0:
            return kept_first
        tail = messages[-budget:]
        while tail and tail[0].get("role") == "tool":
            tail = tail[1:]
        return kept_first + tail

    def get_logs(self, pre_transform_messages, post_transform_messages):
        pre_len = len(pre_transform_messages)
        post_len = len(post_transform_messages)
        if post_len < pre_len:
            return (
                f"Removed {pre_len - post_len} messages. "
                f"Number of messages reduced from {pre_len} to {post_len}.",
                True,
            )
        return "No messages were removed.", False


heavy_worker_window_sizes = {
    'engineer': 20,
    'researcher': 20,
    'inspirehep_context': 70,   # bumped from 20 — see note below
    'cadabra_context': 20,
    'derivation_checker': 20,
}

for agent_name, max_messages in heavy_worker_window_sizes.items():
    TransformMessages(
        transforms=[ToolSafeMessageHistoryLimiter(max_messages=max_messages, keep_first_message=True)],
    ).add_to_agent(agents[agent_name].agent)
```

Validated: `engineer`'s dynamically-routed turn went from the original
bug's ~3.6M-token bill down to ~16.6K prompt tokens (proportionate) for
a similarly-shaped hand-off. **This part is solid — don't revisit
unless a new anomaly appears.**

**Important nuance — window size is not the real lever:** widening
`inspirehep_context` from 20→70 left total cost on a 15-topic scan
essentially unchanged (~3.9M tokens either way), because a genuinely
long scan needs 55–60+ turns regardless — more window just makes each
resend bigger, trading against the agent losing track of earlier
results. **The actual fix is task design:**
`deep_research()` gives each plan step a fresh group chat, so split
long multi-topic scans across multiple plan steps (e.g. 5 topics per
step) instead of one long single-step instruction. Do this in
`plan_instructions` / task phrasing going forward, for any heavy-agent
multi-item task.

Also needs the AG2-side patch (same content class must exist / be
importable from wherever Kazu's local `ag2` working copy applies it —
was previously placed via `conversable_agent.py` in the `ag2` fork; if
missing, recreate using the same `ToolSafeMessageHistoryLimiter` class
above).

**Two unrelated bugs, fixed and stable (no action needed, kept for
context on any future anomaly):**
1. Kazu's `ag2` fork had been built from the wrong-vintage branch —
   fixed by rebuilding from the literal bytes of the real
   `cmbagent_autogen` PyPI wheel. Now `cmbagent-real-base` branch; old
   branch renamed `cmbagent-v091-DEPRECATED-wrong-base` — don't use it.
2. `UnboundLocalError` in AG2's `group_tool_executor.py` from an
   empty-but-present `tool_calls: []` — fixed with a defensive guard.
   Separately, `human_input_mode` defaulted to `"TERMINATE"` instead of
   `"NEVER"` for the five heavy agents in `base_agent.py`'s
   `set_assistant_agent`, causing unexpected interactive pauses — fixed.

---

## 4. Model routing — open decision, needs Kazu's go-ahead to execute

`cmbagent/utils/utils.py`'s `default_agents_llm_model` dict currently
has `researcher`/`plan_reviewer`/`idea_maker`/`idea_hater` on
`claude-sonnet-5`/`claude-haiku-4-5-20251001` (a stale comment
referenced Fable 5 for these, but that was never actually live).

Kazu had previously agreed, in principle, to switch these four roles to
`claude-opus-5` (released ~2026-07-24, cheaper than Fable 5 at close
performance per Anthropic, though Fable 5 is still recommended for
longer-horizon autonomous work). **Do not apply this without
re-confirming with Kazu first** — pricing/performance tradeoffs may
have shifted since the original agreement, and this file doesn't
constitute that confirmation on its own.

---

## 5. Physics — task (iv), the next thing to actually run

Established results so far (KK-tower log coefficients on
Schwarzschild×S¹ and 5D black-string setups; BGMS `-1/4 log N` result
validated against Arrighi & Casarin's Hurwitz-zeta method,
arXiv:2606.01167) are in the full handover doc / git history — not
repeated here to keep this file short. Ask if a refresher is needed.

**Task (iv), drafted, not yet run:**

> Does the crossed-product Type III₁ → Type II von Neumann algebra
> renormalization (Leutheusser–Liu / Witten / CPW-style constructions)
> commute with Kaluza-Klein decomposition on Schwarzschild₄×S¹? I.e., is
> the Type II entropy of the full 5D algebra equal to a suitably
> regularized sum of per-KK-mode Type II entropies, and does the
> species-scale/tower divergence reappear as an obstruction anywhere in
> that assembly?

- Driver script name previously used:
  `research_crossed_product_kk_formulation.py` (needs to be redrafted —
  didn't persist; content above is sufficient to redraft it)
- Intended `work_dir`: `output/2026-08-28_crossed_product_kk_formulation`
  (date bumped to migration date; adjust to actual run date)
- **Structure as multiple plan steps** per §3's lesson: e.g. one step
  for the literature scan, one for the formulation write-up, one for
  `derivation_checker` adversarial review — not one long single-step
  instruction, especially for the literature-scan portion.

---

## 6. Known secondary issues (low priority, open)

- `extract_report.py` globs for `chat_history_step_N.json`, but actual
  files are named `chat_output_{agent}_step_1.json` /
  `nested_chat_output_{agent}_step_1_attempt_M.json` — breaks automatic
  report extraction for some runs.
- `deep_research.py`'s own `chat_history_step_N.json` /
  `context_step_N.pkl` saves exist in source but don't reliably land on
  disk even for successful steps. Debug tracing in place, root cause
  not confirmed.
- `restart_at_step`: `engineer_instructions`/`max_n_attempts` only wire
  in during initial planning, silently ignored on resume — new
  guidance for a resumed step must be smuggled in via the task text.

---

## 7. Session log

Append one entry per session here going forward — a few lines is
enough: date, what was done, what's confirmed, what's next.

- **2026-08-28** — Migrated to Claude Team for Scientists account.
  Introduced Claude Code (terminal) as the execution layer, supervised
  by a Claude chat session. Agreed to start read-only. This status file
  created from the prior handover doc. **Next: run the §2 git-log
  check, read-only, report back before any edits.**
  
  2026-08-28 (cont.) — Configured Claude Code to defaultMode: "plan" in .claude/settings.json after it ran an unrequested command during read-only testing. Located the mode toggle. Next: adversarial test (ask it to write a trivial file, confirm real refusal) before proceeding to §2's actual verification work.
