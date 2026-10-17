"""Load pre-fix versions of patched modules, straight from git history.

This is how the regression suite demonstrates that a fix actually "bites":
rather than hand-reverting a file and running pytest manually, it loads the
file as it looked *before* the fix and runs the exact same checks against it.

Two repositories are involved:

- The `ag2` fork (a sibling checkout, not a subdirectory of this repo) is
  where R1/R3/R4 live. `AG2_BASELINE` pins the commit before any hep-theory
  fix existed ("Baseline: real cmbagent_autogen content, extracted from the
  actual published wheel" - confirmed to have zero "hep-theory" markers).
- This repo is where R5's `ToolSafeMessageHistoryLimiter` lives.
  `CMBAGENT_BASELINE` pins the revision immediately before that class was
  introduced (the parent of "Bound shared group-chat history resend for
  heavy worker agents").

Both are loaded with `git show <commit>:<path>`, written to a temporary file,
and imported under a private dotted name via
`importlib.util.spec_from_file_location`. The temporary directory is removed
before this module returns the loaded module object - `exec_module` reads the
source eagerly, so the module stays usable afterwards, but `inspect.getsource`
and traceback source lines will NOT resolve for it. Bite checks must assert on
exception *types*, not on source text, for baseline modules.

Nothing here is imported by the pytest suite itself (test_r*.py files) - only
by `bite_check.py`, which is not collected by pytest. If git or the `ag2`
checkout is unavailable, callers get `BaselineUnavailable` and should report
the affected row as SKIP rather than failing the whole run.
"""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from types import ModuleType

# Pinned baselines - see module docstring for why each was chosen.
AG2_BASELINE = "385340d4"
CMBAGENT_BASELINE = "5502d23^"  # the commit the suite guards against re-breaking

REPO_ROOT = Path(__file__).resolve().parents[2]


class BaselineUnavailable(RuntimeError):
    """Raised when a pre-fix module can't be loaded (no git, no checkout,
    commit/path not found). Callers should treat this as SKIP, not FAIL -
    the live regression tests don't depend on it."""


def _ag2_fork_dir() -> Path:
    override = os.environ.get("AG2_FORK_DIR")
    if override:
        return Path(override)
    return REPO_ROOT.parent / "ag2"


def _git_show(repo_dir: Path, commit: str, relpath: str) -> str:
    if not repo_dir.is_dir():
        raise BaselineUnavailable(f"no repo at {repo_dir}")
    try:
        result = subprocess.run(
            ["git", "-C", str(repo_dir), "show", f"{commit}:{relpath}"],
            capture_output=True,
            text=True,
            check=True,
        )
    except FileNotFoundError as exc:
        raise BaselineUnavailable("git is not available") from exc
    except subprocess.CalledProcessError as exc:
        raise BaselineUnavailable(
            f"git show {commit}:{relpath} in {repo_dir} failed: {exc.stderr.strip()}"
        ) from exc
    return result.stdout


def _load_module_from_source(source: str, modname: str, filename: str) -> ModuleType:
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir) / filename
        tmp_path.write_text(source)
        spec = importlib.util.spec_from_file_location(modname, tmp_path)
        if spec is None or spec.loader is None:
            raise BaselineUnavailable(f"could not build an import spec for {modname}")
        module = importlib.util.module_from_spec(spec)
        sys.modules[modname] = module
        try:
            spec.loader.exec_module(module)
        except Exception as exc:
            sys.modules.pop(modname, None)
            raise BaselineUnavailable(
                f"baseline module {modname} failed to import: {type(exc).__name__}: {exc}"
            ) from exc
    # Stashed so a caller that already loaded the module (e.g. for a
    # behavioural check) can also run a marker-count check on its exact
    # source without a second `git show` round-trip - see bite_check.py's
    # R4 marker-count row.
    module.__regression_baseline_source__ = source
    return module


def load_ag2_baseline_anthropic() -> ModuleType:
    """Pre-fix `autogen/oai/anthropic.py` (R1, half of R4)."""
    src = _git_show(_ag2_fork_dir(), AG2_BASELINE, "autogen/oai/anthropic.py")
    return _load_module_from_source(src, "autogen.oai._baseline_anthropic", "baseline_anthropic.py")


def load_ag2_baseline_conversable_agent() -> ModuleType:
    """Pre-fix `autogen/agentchat/conversable_agent.py` (R4)."""
    src = _git_show(_ag2_fork_dir(), AG2_BASELINE, "autogen/agentchat/conversable_agent.py")
    return _load_module_from_source(
        src, "autogen.agentchat._baseline_conversable_agent", "baseline_conversable_agent.py"
    )


def load_ag2_baseline_group_tool_executor() -> ModuleType:
    """Pre-fix `autogen/agentchat/group/group_tool_executor.py` (R3)."""
    src = _git_show(_ag2_fork_dir(), AG2_BASELINE, "autogen/agentchat/group/group_tool_executor.py")
    return _load_module_from_source(
        src,
        "autogen.agentchat.group._baseline_group_tool_executor",
        "baseline_group_tool_executor.py",
    )


def load_cmbagent_baseline_hand_offs() -> ModuleType:
    """Pre-fix `cmbagent/hand_offs.py`, from this repo's own history (R5
    registration). Works even without an `ag2` checkout."""
    src = _git_show(REPO_ROOT, CMBAGENT_BASELINE, "cmbagent/hand_offs.py")
    return _load_module_from_source(src, "cmbagent._baseline_hand_offs", "baseline_hand_offs.py")


# ---------------------------------------------------------------------------
# C0: per-call usage log (Phase 0 of docs/prompt_caching_plan.md)
# ---------------------------------------------------------------------------

# Tip of ag2 `cmbagent-real-base` before the call-log commit. It is the parent
# of that commit, pinned by hash so the baseline stays the same once more
# commits land on top.
AG2_C0_BASE = "dc191dd5"
C0_FILES = ("autogen/oai/anthropic.py", "autogen/oai/client.py")


def load_module_from_source(source: str, modname: str, filename: str) -> ModuleType:
    """Public wrapper so `bite_check.py` can build mutant modules from source."""
    return _load_module_from_source(source, modname, filename)


def c0_base_sources() -> tuple[str, str]:
    """(anthropic.py, client.py) as they were before the call-log commit."""
    return tuple(_git_show(_ag2_fork_dir(), AG2_C0_BASE, rel) for rel in C0_FILES)  # type: ignore[return-value]


def load_c0_base_modules() -> tuple[ModuleType, ModuleType]:
    """Baseline (anthropic, client) modules without the call-log hooks."""
    a_src, c_src = c0_base_sources()
    return (
        _load_module_from_source(a_src, "autogen.oai._baseline_c0_anthropic", "baseline_c0_anthropic.py"),
        _load_module_from_source(c_src, "autogen.oai._baseline_c0_client", "baseline_c0_client.py"),
    )


def _load_patch_script() -> ModuleType:
    path = REPO_ROOT / "patch_call_usage_log.py"
    spec = importlib.util.spec_from_file_location("_patch_call_usage_log", path)
    if spec is None or spec.loader is None:
        raise BaselineUnavailable(f"could not load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def c0_patched_sources() -> tuple[str, str]:
    """The base sources run through `patch_call_usage_log.apply`."""
    result = _load_patch_script().apply(*c0_base_sources())
    if result is None:
        raise BaselineUnavailable("the base commit already contains the call-log marker")
    return result


def c0_fork_sources() -> tuple[tuple[str, str], str]:
    """What the patch script has to reproduce: ((anthropic, client), mode).

    - If the ag2 working-tree files equal what `git show HEAD:` returns, the
      change is committed: the sources are HEAD's, the real commit.
    - Otherwise the change is still uncommitted: the sources are the
      working-tree files.
    """
    fork = _ag2_fork_dir()
    work = []
    for rel in C0_FILES:
        path = fork / rel
        if not path.is_file():
            raise BaselineUnavailable(f"no file at {path}")
        work.append(path.read_text())
    head = [_git_show(fork, "HEAD", rel) for rel in C0_FILES]
    if work == head:
        return (head[0], head[1]), "commit (ag2 HEAD)"
    return (work[0], work[1]), "working tree (uncommitted)"
