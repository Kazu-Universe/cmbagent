"""
Wolfram Language / Mathematica execution via wolframscript, for use FROM
within engineer's generated Python code (not a registered LLM tool call
like inspirehep_search.py - engineer writes arbitrary Python, so this is
consumed as a plain import: `from cmbagent.apis.wolframscript_runner import
run_wolframscript`).

Requires a working `wolframscript` binary on PATH - either a full
Mathematica installation or the free (for personal/non-commercial use)
Wolfram Engine (https://www.wolfram.com/engine/). This module cannot
install or license Wolfram software; it only invokes what is already
present.

Design notes:
- Code is written to a temp .wls file and run via `wolframscript -file`,
  rather than passed inline via `-code`, to avoid shell-escaping issues
  with Wolfram Language's heavy use of brackets and quotes, and to avoid
  command-line length limits for nontrivial tensor/index computations
  (exactly what this is for - Gauss-Codazzi decompositions, xAct-style
  tensor algebra, etc., tend to be long).
- Errors return an explicit "WOLFRAMSCRIPT TOOL ERROR" string rather than
  raising, matching inspirehep_search.py's pattern: the calling Python code
  (and the agent reading its printed output) visibly learns the call
  failed, rather than getting a silent empty result or an unhandled
  subprocess traceback that derails the rest of the script.
- wolframscript's default auto-printing behavior for a -file script is not
  fully reliable across versions/configurations for anything beyond the
  last top-level expression - callers MUST use explicit Print[...]
  statements in their Wolfram code for anything they want captured. This
  is stated here AND in engineer.yaml's guidance so it isn't a silent trap.
"""

import os
import re
import shutil
import subprocess
import tempfile

WOLFRAMSCRIPT_BINARY = "wolframscript"
_DEFAULT_TIMEOUT_S = 120

# hep-theory fork: matches Wolfram Language's standard message-line format,
# e.g. "ToExpression::sntxi: Incomplete expression; more input is needed."
# Confirmed via a real live test that wolframscript does NOT reliably use a
# non-zero exit code for this class of error - a genuinely malformed/
# incomplete expression exited 0 with ONLY this kind of message line in
# stdout, no actual computed result. Exit code alone is not a trustworthy
# success signal; this pattern is the second check.
_WOLFRAM_MESSAGE_LINE_RE = re.compile(r"^\s*[A-Za-z$][A-Za-z0-9$]*::[a-zA-Z]+\s*:")


def _is_pure_wolfram_message_output(text: str) -> bool:
    """
    True if every non-empty line of text matches Wolfram's standard
    diagnostic-message format and there is at least one such line - i.e.
    the output consists ENTIRELY of error/warning messages with no actual
    computed result mixed in. This is treated as a failure even at exit
    code 0, since a real computation with a genuine warning alongside a
    real result would have OTHER content too (the thing that got Print[]ed).
    """
    lines = [line for line in text.splitlines() if line.strip()]
    if not lines:
        return False
    return all(_WOLFRAM_MESSAGE_LINE_RE.match(line) for line in lines)


def run_wolframscript(code: str, timeout: int = _DEFAULT_TIMEOUT_S) -> str:
    """
    Run Wolfram Language code via wolframscript and return its stdout.

    Args:
        code: Wolfram Language source. Use explicit Print[...] statements
            for anything you want to see in the output - do not rely on
            top-level-expression auto-printing, which is not reliable
            across wolframscript configurations for anything but possibly
            the final expression.
        timeout: seconds to allow before killing the process (default 120 -
            tensor/index algebra with xAct can be slow; raise this for
            genuinely heavy computations rather than letting them silently
            truncate).

    Returns:
        str: the captured stdout on success, or a string starting with
        "WOLFRAMSCRIPT TOOL ERROR" if the binary is missing, the process
        exited non-zero, or it timed out. Any non-empty stderr is appended
        even on a zero exit, since Wolfram Language warnings/messages
        (e.g. from General::, Simplify::) are often diagnostically
        important and go to stderr without necessarily indicating failure.
    """
    if shutil.which(WOLFRAMSCRIPT_BINARY) is None:
        return (
            "WOLFRAMSCRIPT TOOL ERROR: 'wolframscript' was not found on PATH. "
            "This requires a working Mathematica or Wolfram Engine "
            "installation - this module cannot install or license Wolfram "
            "software. Do not fabricate a plausible-looking result; report "
            "this as a genuine tooling limitation."
        )

    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".wls", delete=False
        ) as tmp_file:
            tmp_file.write(code)
            tmp_path = tmp_file.name

        try:
            result = subprocess.run(
                [WOLFRAMSCRIPT_BINARY, "-file", tmp_path],
                capture_output=True,
                text=True,
                timeout=timeout,
            )
        except subprocess.TimeoutExpired:
            return (
                f"WOLFRAMSCRIPT TOOL ERROR: execution exceeded the {timeout}s "
                "timeout and was killed. If this computation is genuinely "
                "this heavy, retry with a larger timeout argument; do not "
                "fabricate a result for the incomplete computation."
            )
        except OSError as e:
            return (
                f"WOLFRAMSCRIPT TOOL ERROR: failed to launch wolframscript "
                f"({type(e).__name__}: {e})."
            )

        if result.returncode != 0:
            return (
                f"WOLFRAMSCRIPT TOOL ERROR: wolframscript exited with code "
                f"{result.returncode}.\n"
                f"--- stdout ---\n{result.stdout}\n"
                f"--- stderr ---\n{result.stderr}"
            )

        # hep-theory fork: exit code 0 is NOT a reliable success signal on
        # its own - confirmed via a real live test, a malformed/incomplete
        # expression exited 0 with only a Wolfram diagnostic message line
        # in stdout (e.g. "ToExpression::sntxi: Incomplete expression;
        # more input is needed."), no actual computed result. If stdout is
        # entirely message-format lines with nothing else, treat this as a
        # failure regardless of exit code.
        if _is_pure_wolfram_message_output(result.stdout):
            return (
                "WOLFRAMSCRIPT TOOL ERROR: wolframscript exited with code 0, "
                "but its output consists entirely of Wolfram Language "
                "diagnostic message(s) with no actual computed result - this "
                "usually means the code was malformed or incomplete, even "
                "though the process itself did not report a failure exit "
                "code. Do not treat this as a successful result.\n"
                f"--- stdout ---\n{result.stdout}\n"
                f"--- stderr ---\n{result.stderr}"
            )

        output = result.stdout
        if result.stderr.strip():
            output += (
                "\n\n[wolframscript stderr - may be diagnostic Wolfram "
                "Language messages, not necessarily a failure]:\n"
                + result.stderr
            )
        if not output.strip():
            output = (
                "[wolframscript ran successfully (exit code 0) but produced "
                "no output - did the code use Print[...] for what it wanted "
                "to capture? Top-level-expression auto-printing is not "
                "reliable in -file mode.]"
            )
        return output

    finally:
        if tmp_path is not None:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
