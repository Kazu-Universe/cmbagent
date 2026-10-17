"""
Patch: per-call usage log for the ag2 Anthropic client (Phase 0 of
docs/prompt_caching_plan.md).

Reproduces, byte for byte, the fork commit on ag2 branch `cmbagent-real-base`
that adds this feature, so the installed `.venv` and the fork stay identical.
`tests/regression/bite_check.py` checks that equivalence ("script reproduces
commit" row).

WHAT IT ADDS (inert unless the env var CMBAGENT_CALL_LOG is set):

- autogen/oai/anthropic.py: right after `self._client.messages.create(...)`,
  `_cmbagent_call_record(params, response)` builds a record - model, input /
  cache-write / cache-read / output tokens (ints only, else None), sha256
  prefixes of the system block, tools list and first message, message count,
  stop reason - and leaves it on the client as `_cmbagent_last_call`.
- autogen/oai/client.py: right after `client.create(params)`,
  `_cmbagent_write_call_log(client, agent)` adds a timestamp and the agent's
  name and appends one JSON line to $CMBAGENT_CALL_LOG. Write failures only
  warn. Clients without a record (non-Anthropic) are skipped.

It is a read-only observer: the request sent and the response returned are
unchanged. `anthropic.py` has a single SDK call site, so one hook covers every
API path.

SAFETY: idempotent (marker string). Every anchor must match exactly once or
the script exits 1 without writing either file. If the second write fails the
first file is restored, so an install is never left half-patched. A marker
present in only one of the two files (a partial patch) also exits 1.

Run once against your installed environment:
    python patch_call_usage_log.py
Optional overrides (used by the bite check):
    python patch_call_usage_log.py --anthropic PATH --client PATH
"""

import argparse
import importlib.util
import os
import sys
import tempfile

MARKER = "hep-theory fork: per-call usage log"

ANTHROPIC_HOOK_OLD = """        response = self._client.messages.create(**anthropic_params)
"""
ANTHROPIC_HOOK_NEW = """        response = self._client.messages.create(**anthropic_params)

        # hep-theory fork: per-call usage log (Phase 0 of docs/prompt_caching_plan.md;
        # inert unless CMBAGENT_CALL_LOG is set). Read-only observer: it only builds
        # a record from the request/response; client.py writes it out with the agent name.
        if os.environ.get("CMBAGENT_CALL_LOG"):
            self._cmbagent_last_call = _cmbagent_call_record(anthropic_params, response)
"""

ANTHROPIC_HELPER_OLD = """def _calculate_cost(input_tokens: int, output_tokens: int, model: str) -> float:"""
ANTHROPIC_HELPER_NEW = '''def _cmbagent_call_record(params: dict[str, Any], response: Any) -> dict[str, Any]:
    """hep-theory fork: per-call usage log record (Phase 0 of the caching plan).

    Pure observer: reads ``params`` and ``response`` and never mutates them.
    Token counts are recorded only if they are real ints (a mocked or absent
    usage field gives ``None``). Hashes cover the full system block, the tools
    list, the first message and the ``thinking`` / ``tool_choice`` options (all
    of which take part in cache validity), so prefix changes between calls are
    visible. Never raises: on any failure it returns ``{"error": repr(e)}``.
    """
    try:
        import hashlib

        def _h(obj: Any) -> Optional[str]:
            if obj is None:
                return None
            s = obj if isinstance(obj, str) else json.dumps(obj, sort_keys=True, default=str)
            return hashlib.sha256(s.encode("utf-8", "replace")).hexdigest()[:16]

        usage = getattr(response, "usage", None)

        def _tokens(name: str) -> Optional[int]:
            v = getattr(usage, name, None)
            return v if isinstance(v, int) and not isinstance(v, bool) else None

        system = params.get("system", "")
        messages = params.get("messages") or []
        return {
            "model": params.get("model"),
            "input_tokens": _tokens("input_tokens"),
            "cache_creation_input_tokens": _tokens("cache_creation_input_tokens"),
            "cache_read_input_tokens": _tokens("cache_read_input_tokens"),
            "output_tokens": _tokens("output_tokens"),
            "system_sha256": _h(system),
            "system_chars": len(system) if isinstance(system, str) else len(json.dumps(system, default=str)),
            "tools_sha256": _h(params.get("tools")),
            "cache_opts_sha256": _h({"thinking": params.get("thinking"), "tool_choice": params.get("tool_choice")}),
            "n_messages": len(messages),
            "first_msg_sha256": _h(messages[0]) if messages else None,
            "stop_reason": getattr(response, "stop_reason", None),
        }
    except Exception as e:  # never let logging affect a call
        return {"error": repr(e)}


def _calculate_cost(input_tokens: int, output_tokens: int, model: str) -> float:'''

CLIENT_IMPORT_OLD = """import logging
import re
"""
CLIENT_IMPORT_NEW = """import logging
import os
import re
"""

CLIENT_HOOK_OLD = """                response = client.create(params)
"""
CLIENT_HOOK_NEW = """                try:
                    response = client.create(params)
                finally:
                    # hep-theory fork: per-call usage log (inert unless CMBAGENT_CALL_LOG is set).
                    # In a finally so a call that was billed and then raised while handling the
                    # response is still logged; the writer never raises, so it cannot mask that error.
                    if os.environ.get("CMBAGENT_CALL_LOG"):
                        _cmbagent_write_call_log(client, agent)
"""

# The helper goes ABOVE the @lru_cache line: inserting it between the decorator
# and `def log_cache_seed_value` would make lru_cache wrap the helper.
CLIENT_HELPER_OLD = """@lru_cache(maxsize=128)
def log_cache_seed_value("""
CLIENT_HELPER_NEW = '''def _cmbagent_write_call_log(client: Any, agent: Any) -> None:
    """hep-theory fork: append the per-call usage record to ``$CMBAGENT_CALL_LOG``.

    ``AnthropicClient.create`` leaves its record on the client; clients that
    don't (every non-Anthropic one) are skipped. Adds the timestamp, the
    process id, the calling agent's name (None for callers that pass no
    agent) and the current plan step, read from
    ``agent.context_variables["current_plan_step_number"]`` (None if the agent
    has no context variables or no such key). Never raises: a write failure
    only emits a warning.

    Single-threaded assumption: one pending record is kept per client, so
    this relies on calls being made one at a time (cmbagent runs its agents
    sequentially, each normally with its own client). Overlapping calls on one
    shared client could mix their records up; if that path ever appears, key
    the record by thread or pass it back with the response instead.
    """
    record = client.__dict__.pop("_cmbagent_last_call", None) if hasattr(client, "__dict__") else None
    if not isinstance(record, dict):
        return
    try:
        import time

        try:
            step = agent.context_variables.get("current_plan_step_number")
        except Exception:
            step = None
        record = {"ts": time.time(), "pid": os.getpid(), "agent": getattr(agent, "name", None), "step": step, **record}
        with open(os.environ["CMBAGENT_CALL_LOG"], "a", encoding="utf-8") as f:
            f.write(json.dumps(record, default=str) + "\\n")
    except Exception as e:
        warnings.warn(f"CMBAGENT_CALL_LOG write failed ({e!r}); call logging skipped for this call.", UserWarning)


@lru_cache(maxsize=128)
def log_cache_seed_value('''

ANTHROPIC_EDITS = [
    ("messages.create hook", ANTHROPIC_HOOK_OLD, ANTHROPIC_HOOK_NEW),
    ("_calculate_cost (helper insertion point)", ANTHROPIC_HELPER_OLD, ANTHROPIC_HELPER_NEW),
]
CLIENT_EDITS = [
    ("`import logging` / `import re`", CLIENT_IMPORT_OLD, CLIENT_IMPORT_NEW),
    ("client.create(params) hook", CLIENT_HOOK_OLD, CLIENT_HOOK_NEW),
    ("@lru_cache / log_cache_seed_value (helper insertion point)", CLIENT_HELPER_OLD, CLIENT_HELPER_NEW),
]


class PatchError(Exception):
    """An anchor was missing / ambiguous, or the files are in a partial state."""


def _transform(label, src, edits):
    """Apply every edit to `src`, or raise PatchError listing each bad anchor."""
    problems = []
    for name, old, _new in edits:
        n = src.count(old)
        if n != 1:
            problems.append(f"{label}: anchor [{name}] found {n} times (expected exactly 1)")
    if problems:
        raise PatchError("\n".join(problems))
    for _name, old, new in edits:
        src = src.replace(old, new, 1)
    return src


def apply(anthropic_src, client_src):
    """Pure transform. Returns (new_anthropic, new_client), or None if both are
    already patched. Raises PatchError on a partial patch or any bad anchor.
    """
    a_done, c_done = MARKER in anthropic_src, MARKER in client_src
    if a_done and c_done:
        return None
    if a_done != c_done:
        raise PatchError(
            "partial patch: marker present in "
            + ("anthropic.py but not client.py" if a_done else "client.py but not anthropic.py")
            + " - restore both files from the fork and re-run"
        )
    problems = []
    out = []
    for label, src, edits in (
        ("anthropic.py", anthropic_src, ANTHROPIC_EDITS),
        ("client.py", client_src, CLIENT_EDITS),
    ):
        try:
            out.append(_transform(label, src, edits))
        except PatchError as e:
            problems.append(str(e))
    if problems:
        raise PatchError("\n".join(problems))
    return out[0], out[1]


def _locate(modname):
    spec = importlib.util.find_spec(modname)
    if spec is None or spec.origin is None:
        raise PatchError(f"Could not locate {modname} - is autogen installed?")
    return spec.origin


def _write_atomic(path, text):
    d = os.path.dirname(path) or "."
    fd, tmp = tempfile.mkstemp(dir=d, prefix=".patch_call_usage_log.")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as f:
            f.write(text)
        os.chmod(tmp, os.stat(path).st_mode & 0o7777)
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--anthropic", help="path to autogen/oai/anthropic.py (default: installed)")
    ap.add_argument("--client", help="path to autogen/oai/client.py (default: installed)")
    args = ap.parse_args(argv)
    try:
        a_path = args.anthropic or _locate("autogen.oai.anthropic")
        c_path = args.client or _locate("autogen.oai.client")
        # Explicit UTF-8 and no newline translation, so the bytes written are
        # exactly the fork's regardless of the locale.
        with open(a_path, "r", encoding="utf-8", newline="") as f:
            a_src = f.read()
        with open(c_path, "r", encoding="utf-8", newline="") as f:
            c_src = f.read()
        result = apply(a_src, c_src)
    except (PatchError, OSError, ValueError) as e:  # ValueError covers UnicodeDecodeError
        print(f"ERROR: {e}\nNothing was written.", file=sys.stderr)
        return 1
    if result is None:
        print(f"Already patched ({a_path}, {c_path}) - nothing to do.")
        return 0
    try:
        _write_atomic(a_path, result[0])
    except OSError as e:
        print(f"ERROR: could not write {a_path}: {e}\nNothing was written.", file=sys.stderr)
        return 1
    try:
        _write_atomic(c_path, result[1])
    except OSError as e:
        # Do not leave a half-patched install: put the first file back.
        try:
            _write_atomic(a_path, a_src)
        except OSError as e2:
            print(
                f"ERROR: could not write {c_path}: {e}\nand could not restore {a_path}: {e2}\n"
                f"{a_path} is PATCHED and {c_path} is not - restore both from the fork.",
                file=sys.stderr,
            )
            return 1
        print(f"ERROR: could not write {c_path}: {e}\n{a_path} was restored; nothing was written.", file=sys.stderr)
        return 1
    print(f"Patched {a_path}\nPatched {c_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
