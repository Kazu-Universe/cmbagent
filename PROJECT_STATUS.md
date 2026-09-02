# PROJECT_STATUS.md — CMBAgentForHEPTH_wClaude

**Last updated:** 2026-09-02

> Convention: update this file at the end of every work session — what
> changed, what's confirmed, what's open, and the exact next command.
> Read it first thing at the start of every session, then verify it
> against `git log` / `git status` before doing anything else.

---

## 0. Who / what

Kazu — theoretical physics (string theory, KK compactifications, black
hole thermodynamics) + astrophysical data analysis (Cobaya, CMB
likelihoods). India, UTC+5:30. Still learning git — walk through git ops
one command at a time. Ubuntu machine (Dell Latitude 5420).

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

## 1. Working style

**Default: hands-on relay.** Kazu runs git, python, and pipeline
commands himself in the terminal and pastes output into a Claude chat
session for diagnosis and next steps. This is deliberate — running the
commands personally is how the toolchain gets learned, and that's a
goal in its own right, not just a means to an end.

**Claude Code is used only where it has a definite advantage:**

1. **Reading real source to diagnose a bug** — where the answer lives in
   the actual `ag2`/`cmbagent` files. Relaying source by copy-paste is
   where the token-resend and wrong-fork-base bugs cost the most time.
2. **Multi-file edits that must stay consistent** — e.g. a change
   touching `hand_offs.py` and the ag2 side together.
3. **Offline reproductions with a mocked LLM client** — iterate-test-
   adjust loops where each round trip through chat is pure overhead.

Everything else — running the research pipeline, git operations,
reading outputs, deciding what to run next — stays hands-on.

**Claude Code permissions:** `.claude/settings.json` sets
`defaultMode: "plan"`, so sessions start read-only (reads and read-only
shell commands; no source edits). The mode toggle is available in the
Claude Code UI, and `--permission-mode <mode>` sets it at launch.
This matters: permission modes are enforced by Claude Code itself,
whereas an instruction in the prompt is only a request to the model —
in the first trial session, Claude Code ran a command after being told
not to. **Still to do: adversarial test** — ask it to create a trivial
file and confirm it actually refuses, before trusting the setting.

Keep commits small, with messages explaining *why*, not just *what*.
Git note learned 2026-09-02: `git commit -m` treats everything before
the first *blank* line as the subject, so a multi-line quoted string
without a blank line becomes one enormous subject. Use one `-m` per
paragraph instead — git inserts the blank lines.

---

## 2. Current state — clean

As of 2026-09-02 the working tree is clean and `main` is level with
`origin/main` at `afff173`. Recent history:

```
afff173  Ignore disposable hep-theory debugging scaffolding
29de9c7  Track hep-theory fork research drivers, docs, and dependency patch scripts
4595b24  Tune per-agent history window sizes; drop temporary diagnostic
f250ce0  Force human_input_mode=NEVER for heavy worker agents
5502d23  Bound shared group-chat history resend for heavy worker agents
```

The previously-unconfirmed work is resolved: `5502d23` (bounding) was
already pushed, but the per-agent window tuning had never made it into
`cmbagent/hand_offs.py` — the intended version was sitting as an
untracked copy at the repo root. It is now in place and committed, the
temporary diagnostic print is removed, and the `human_input_mode` fix
is committed too.

**Next actual work:** §4 (model routing decision) and §5 (physics task
iv). Nothing is blocking.

---

## 3. Token-resend bug — fixed, live, and committed

**Root cause:** AG2's `GroupChat` broadcasts every message to every
agent; without a bounding transform, a heavy agent dynamically routed
into an already-long conversation re-pays for the entire accumulated
history on every turn. `hand_offs.py` had bounding for cheap plumbing
agents but not for the five heavy LLM workers: `engineer`, `researcher`,
`inspirehep_context`, `cadabra_context`, `derivation_checker`.

**Fix, now live in `cmbagent/hand_offs.py`:** a custom
`ToolSafeMessageHistoryLimiter` transform (like AG2's
`MessageHistoryLimiter` but never leaves an orphaned tool-result message
at the front of the truncated window, which the Anthropic API would
reject), registered per-agent in `register_all_hand_offs()` via a
`heavy_worker_window_sizes` dict: `inspirehep_context` at 70, the other
four at 20.

Validated: `engineer`'s dynamically-routed turn went from the original
bug's ~3.6M-token bill down to ~16.6K prompt tokens for a
similarly-shaped hand-off. **Don't revisit unless a new anomaly appears.**

**Why 70 for `inspirehep_context`:** a flat 20 correctly bounds message
count but is too small for its real workload — one multi-search
literature scan needs 2–3 messages per search round trip, so a
15-search scan runs 30–45+ messages of its own turns before the
controller's interleaved instructions. Once earlier results scrolled
out of the window, the agent lost sight of its own completed work and
redid finished searches — genuine redundant work, not a resend-bug
symptom.

**Important nuance — window size is not the cost lever:** widening
20→70 left total cost on a 15-topic scan essentially unchanged (~3.9M
tokens either way), because a genuinely long scan needs 55–60+ turns
regardless. The 70 is justified by the redundant-work problem above,
not by cost. **The actual cost fix is task design:** `deep_research()`
gives each plan step a fresh group chat, so split long multi-topic
scans across multiple plan steps (e.g. 5 topics per step) rather than
one long single-step instruction. Apply this in `plan_instructions` /
task phrasing for any heavy-agent multi-item task.

**Still open on the ag2 side:** the same transform class needs to exist
in the local `ag2` working copy (previously placed via
`conversable_agent.py`). Not verified this session — check before the
next full pipeline run.

**Two unrelated bugs, fixed and stable (context for future anomalies):**
1. Kazu's `ag2` fork had been built from the wrong-vintage branch —
   fixed by rebuilding from the literal bytes of the real
   `cmbagent_autogen` PyPI wheel. Now `cmbagent-real-base`; old branch
   renamed `cmbagent-v091-DEPRECATED-wrong-base` — don't use it.
2. `UnboundLocalError` in AG2's `group_tool_executor.py` from an
   empty-but-present `tool_calls: []` — fixed with a defensive guard.
   Separately, `human_input_mode` defaulted to `"TERMINATE"` instead of
   `"NEVER"` for the five heavy agents in `base_agent.py`'s
   `set_assistant_agent`, pausing the pipeline for interactive input
   whenever an agent hit its `max_consecutive_auto_reply` cap — fixed
   and committed in `f250ce0`.

---

## 4. Model routing — open decision, needs Kazu's go-ahead

`cmbagent/utils/utils.py`'s `default_agents_llm_model` dict currently
has `researcher`/`plan_reviewer`/`idea_maker`/`idea_hater` on
`claude-sonnet-5`/`claude-haiku-4-5-20251001` (a stale comment
referenced Fable 5 for these, but that was never actually live).

Kazu had previously agreed in principle to switch these four roles to
`claude-opus-5`. **Do not apply without re-confirming** — pricing and
model availability have moved since (note also that Fable 5 / Mythos 5
access was suspended and restored mid-2026 under US export controls),
and this file doesn't constitute that confirmation.

---

## 5. Physics — task (iv), the next thing to run

Established results so far (KK-tower log coefficients on
Schwarzschild×S¹ and 5D black-string setups; BGMS `-1/4 log N` result
validated against Arrighi & Casarin's Hurwitz-zeta method,
arXiv:2606.01167) are in the changelogs and git history.

**Task (iv), drafted, not yet run:**

> Does the crossed-product Type III₁ → Type II von Neumann algebra
> renormalization (Leutheusser–Liu / Witten / CPW-style constructions)
> commute with Kaluza-Klein decomposition on Schwarzschild₄×S¹? I.e., is
> the Type II entropy of the full 5D algebra equal to a suitably
> regularized sum of per-KK-mode Type II entropies, and does the
> species-scale/tower divergence reappear as an obstruction anywhere in
> that assembly?

- **Correction (2026-09-02):** the driver
  `research_crossed_product_kk_formulation.py` **does exist** and is now
  tracked in git — an earlier version of this file wrongly said it had
  to be redrafted. Read it before assuming anything about its contents;
  it has not been reviewed since being written.
- Five sibling drivers are also tracked:
  `research_5d_black_string_log_coefficient.py`,
  `research_ads_kk_tower_localization_match.py`,
  `research_kk_tower_entanglement_entropy.py`,
  `research_kk_tower_susskind_uglum_check.py`,
  `research_species_scale_moduli_dependence.py`.
- Intended `work_dir`: `output/<run-date>_crossed_product_kk_formulation`
- **Structure as multiple plan steps** per §3's lesson: one step for the
  literature scan, one for the formulation write-up, one for
  `derivation_checker` adversarial review — not one long single-step
  instruction.

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
  in during initial planning, silently ignored on resume — new guidance
  for a resumed step must be smuggled in via the task text.

---

## 7. Repo housekeeping

`CHANGELOG_ADDENDUM.md` through `_4.md` (430 lines total) are now
tracked. They record **upstream** fixes to `cmbagent_autogen`/`autogen`
and the reasoning behind them — the Anthropic-vs-OpenAI `tool_choice`
schema mismatch, `top_p` rejection, the `group_tool_executor` bug, etc.
This is expensive-to-rediscover knowledge. **Open task:** consolidate
the four into one `CHANGELOG_HEP_THEORY.md`, deliberately, as its own
piece of work — not a quick tidy-up.

`patch_*.py` are tracked because they patch the *dependency* inside
`.venv`, not this repo, so they'd need re-applying after any venv
rebuild or machine move. Note the changelog references a
`patch_default_top_p.py` that isn't present — the set is incomplete;
the changelogs are the authoritative record.

Disposable scaffolding (`*.diff`, `classify_patch_scripts*.py`,
`check_resend_cost.py`, `oneshot_*.py`) is gitignored.

---

## 8. Session log

- **2026-08-28** — Migrated to Claude Team for Scientists account.
  Trialled Claude Code; it ran a command during a read-only session
  after being told not to. Configured `defaultMode: "plan"` in
  `.claude/settings.json` in response. This status file created.
- **2026-09-02** — Settled working style: hands-on relay by default,
  Claude Code only for the three cases in §1. Resolved §2's open
  questions by inspecting the actual diffs: the per-agent window tuning
  had never landed in `cmbagent/hand_offs.py` (it was an untracked copy
  at the repo root), and the `human_input_mode` fix was uncommitted.
  Five commits, all pushed: both fixes, the diagnostic print removed,
  18 previously-untracked files now tracked (research drivers, docs,
  changelogs, patch scripts), and a `.gitignore` for scaffolding.
  Working tree now clean for the first time since the migration.
  **Next: (a) the Claude Code adversarial permission test from §1,
  (b) verify the ag2-side transform per §3, (c) then §4 or §5.**
