"""Shared assertion helpers for the Tier 1 regression suite.

Every check here is a plain function that takes the module(s) under test and
either returns a value to assert on, or performs the action and lets whatever
exception it raises propagate. This lets `test_r*.py` and `bite_check.py` run
*literally the same code* against the live, patched modules and against
pre-fix baselines loaded by `_baseline.py` - the whole point of a bite check
is that it isn't a second, hand-written copy of the assertion that could
itself be wrong.

None of this touches the network or an API key: `AnthropicClient` instances
are built via `__new__` (bypassing `__init__`, which reads `ANTHROPIC_API_KEY`
/ AWS / GCP env vars and constructs a real SDK client) and `create()` is given
a `MagicMock()` in place of the SDK client.
"""

from __future__ import annotations

import ast
import asyncio
import contextlib
import copy
import hashlib
import io
import json
import os
import re
import warnings
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

# Sentinel distinguishing "the key is absent" from "the key is present and None".
ABSENT = object()

# Present in ANTHROPIC_PRICING_1k so _calculate_cost doesn't emit a stray
# UserWarning that would otherwise need filtering in every test.
TEST_MODEL = "claude-3-5-sonnet-20241022"

GUARD_MARKER = "hep-theory fork: empty messages guard"
DEFENSIVE_GUARD_MARKER = "hep-theory fork: defensive guard"


# ---------------------------------------------------------------------------
# R1: tool_choice translation + R4 (anthropic.py half): empty-messages conversion
# ---------------------------------------------------------------------------


def make_offline_anthropic_client(anthropic_module):
    """An AnthropicClient with no SDK object and no env-var reads.

    ``create()`` only touches ``self._client``, ``self._response_format`` and
    ``self._last_tooluse_status`` - setting exactly those three is enough.
    """
    client = anthropic_module.AnthropicClient.__new__(anthropic_module.AnthropicClient)
    client._client = MagicMock()
    client._response_format = None
    client._last_tooluse_status = {}
    return client


def make_mock_response(content=(), stop_reason="end_turn"):
    response = MagicMock()
    response.content = list(content)
    response.stop_reason = stop_reason
    response.id = "msg_test"
    response.usage.input_tokens = 1
    response.usage.output_tokens = 1
    return response


def sent_tool_choice(anthropic_module, tool_choice: Any, extra_params: dict | None = None):
    """Run ``AnthropicClient.create()`` with the given OpenAI-schema
    ``params["tool_choice"]`` and return whatever actually reached the
    (mocked) SDK's ``messages.create(**kwargs)`` - or ``ABSENT`` if the key
    never made it into the call at all.
    """
    client = make_offline_anthropic_client(anthropic_module)
    client._client.messages.create.return_value = make_mock_response()
    params: dict[str, Any] = {
        "model": TEST_MODEL,
        "messages": [{"role": "user", "content": "hi"}],
        "tools": [
            {
                "type": "function",
                "function": {
                    "name": "record_plan",
                    "description": "record the plan",
                    "parameters": {"type": "object", "properties": {}},
                },
            }
        ],
    }
    if extra_params:
        params.update(extra_params)
    if tool_choice is not ABSENT:
        params["tool_choice"] = tool_choice

    client.create(dict(params))

    call = client._client.messages.create.call_args
    if call is None:
        return ABSENT
    return call.kwargs.get("tool_choice", ABSENT)


def convert_empty_messages(anthropic_module):
    """``oai_messages_to_anthropic_messages`` takes the whole ``params``
    dict, not a bare message list."""
    return anthropic_module.oai_messages_to_anthropic_messages({"messages": []})


# ---------------------------------------------------------------------------
# R3: empty-but-present tool_calls in the group tool executor
# ---------------------------------------------------------------------------


def make_peer_agent():
    """A minimal, LLM-free agent to pass as the ``agent`` argument of
    ``_generate_group_tool_reply`` - always the real, live ``ConversableAgent``.
    ``GroupToolExecutor`` (live or baseline) itself subclasses the live
    ``ConversableAgent`` via a relative import that resolves against the real
    installed package regardless of which ``group_tool_executor`` module is
    under test, so there is no baseline/live mismatch to worry about here."""
    from autogen.agentchat.conversable_agent import ConversableAgent

    return ConversableAgent(name="peer", llm_config=False)


def call_empty_tool_calls_reply(group_tool_executor_module, peer_agent=None):
    """Exercise the exact bug: a present-but-empty ``tool_calls`` list used
    to leave ``tool_message`` unbound. Returns the reply tuple on the fixed
    code path; raises ``UnboundLocalError`` on the pre-fix baseline."""
    peer_agent = peer_agent or make_peer_agent()
    executor = group_tool_executor_module.GroupToolExecutor()
    message = {"role": "assistant", "content": "", "tool_calls": []}
    return executor._generate_group_tool_reply(peer_agent, messages=[message])


def call_tool_reply_with_empty_history(group_tool_executor_module, peer_agent=None):
    """The sibling, still-unguarded site: no patch script covers this one.
    Raises ``IndexError`` today (live and baseline alike) - shipped as
    ``xfail(strict=True)``, not as a fixed-and-guarded check."""
    peer_agent = peer_agent or make_peer_agent()
    executor = group_tool_executor_module.GroupToolExecutor()
    return executor._generate_group_tool_reply(peer_agent, messages=[])


# ---------------------------------------------------------------------------
# R4: empty-history guards in conversable_agent.py
# ---------------------------------------------------------------------------


def make_bare_agent(conversable_agent_module):
    """Build a ``ConversableAgent`` from *the module under test* - so a
    baseline module's own (unguarded) methods are what get exercised."""
    return conversable_agent_module.ConversableAgent(name="t", llm_config=False)


def call_empty_history_sync(conversable_agent_module, method_name: str):
    agent = make_bare_agent(conversable_agent_module)
    return getattr(agent, method_name)(messages=[])


def call_empty_history_async(conversable_agent_module, method_name: str):
    agent = make_bare_agent(conversable_agent_module)
    return asyncio.run(getattr(agent, method_name)(messages=[]))


def guard_marker_count(source: str) -> int:
    return source.count(GUARD_MARKER)


def not_messages_count(source: str) -> int:
    return source.count("if not messages:")


# ---------------------------------------------------------------------------
# R5: ToolSafeMessageHistoryLimiter + heavy-worker registration
# ---------------------------------------------------------------------------


def assistant_tool_call_message(call_id: str) -> dict:
    return {
        "role": "assistant",
        "content": "",
        "tool_calls": [{"id": call_id, "type": "function", "function": {"name": "search", "arguments": "{}"}}],
    }


def tool_result_message(call_id: str) -> dict:
    return {"role": "tool", "tool_call_id": call_id, "content": "result"}


def alternating_tool_history(n_pairs: int, leading_user: bool = True) -> list[dict]:
    """A synthetic OpenAI-shape history: an optional leading user message,
    then ``n_pairs`` of (assistant tool_calls, matching tool result)."""
    messages: list[dict] = []
    if leading_user:
        messages.append({"role": "user", "content": "task"})
    for i in range(n_pairs):
        call_id = f"call_{i}"
        messages.append(assistant_tool_call_message(call_id))
        messages.append(tool_result_message(call_id))
    return messages


def multi_call_tool_history(n_turns: int, calls_per_turn: int = 2, leading_user: bool = True) -> list[dict]:
    """A synthetic history where each assistant turn issues several tool
    calls at once, producing a *run* of consecutive tool-result messages
    (rather than the strict 1:1 alternation ``alternating_tool_history``
    produces). This is the shape that defeats the stock
    ``MessageHistoryLimiter``'s single boundary-slot role check: that check
    only inspects one message at the cut point, so a run of two or more
    consecutive tool results leaves the ones behind the checked slot
    unprotected."""
    messages: list[dict] = []
    if leading_user:
        messages.append({"role": "user", "content": "task"})
    for turn in range(n_turns):
        call_ids = [f"call_{turn}_{j}" for j in range(calls_per_turn)]
        messages.append(
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {"id": call_id, "type": "function", "function": {"name": "search", "arguments": "{}"}}
                    for call_id in call_ids
                ],
            }
        )
        messages.extend(tool_result_message(call_id) for call_id in call_ids)
    return messages


def strip_kept_first(out: list[dict], history: list[dict]) -> list[dict]:
    """``apply_transform``'s output, with the unconditionally-kept first
    message (when ``keep_first_message=True`` and it survived) removed, so
    callers can inspect the actual cut boundary - the first message that was
    subject to truncation - rather than the always-kept head."""
    if out and history and out[0] is history[0]:
        return out[1:]
    return out


def assert_pairs_intact(messages: list[dict]) -> None:
    """Every tool-result's call id must have its matching tool_calls message
    present earlier in the same list - a window that split a pair would fail
    this (and would also be rejected outright by the Anthropic API)."""
    issued: set[str] = set()
    for message in messages:
        if message.get("role") == "tool":
            assert message["tool_call_id"] in issued, (
                f"orphaned tool result {message['tool_call_id']!r} with no preceding tool_calls in the window"
            )
        for tool_call in message.get("tool_calls") or []:
            issued.add(tool_call["id"])


class StubAgentWrapper:
    """Mimics cmbagent's agent-wrapper shape: ``.agent`` holds the real
    ``ConversableAgent``. ``register_all_hand_offs`` only ever reads
    ``agents[name].agent``."""

    def __init__(self, agent):
        self.agent = agent


class StubCmbagentInstance:
    """The minimal surface ``register_all_hand_offs`` actually calls:
    ``.mode``, ``.llm_config``, ``.agents``, ``.chat_agent`` and
    ``.get_agent_object_from_name``. Verified against the live function for
    the default ``mode="planning_and_control"`` path, which every current R5
    test exercises - it builds every handoff and context condition that path
    normally would, using LLM-free ``ConversableAgent``s.

    ``chat_agent`` is only read on the ``mode == "human_in_the_loop"``
    branch, which no current test takes; it defaults to an agent name
    already in ``core_agent_names`` so that branch doesn't immediately crash
    with ``AttributeError`` if a future test adds that mode."""

    def __init__(self, mode: str = "planning_and_control"):
        self.mode = mode
        self.llm_config = False
        self.chat_agent = "engineer"
        self._wrappers: dict[str, StubAgentWrapper] = {}

    def get_agent_object_from_name(self, name: str) -> StubAgentWrapper:
        if name not in self._wrappers:
            from autogen.agentchat.conversable_agent import ConversableAgent

            self._wrappers[name] = StubAgentWrapper(ConversableAgent(name=name, llm_config=False))
        return self._wrappers[name]

    @property
    def agents(self):
        return [wrapper.agent for wrapper in self._wrappers.values()]


def run_register_all_hand_offs(hand_offs_module, mode: str = "planning_and_control") -> StubCmbagentInstance:
    stub = StubCmbagentInstance(mode=mode)
    hand_offs_module.register_all_hand_offs(stub)
    return stub


def extract_dict_literal(source: str, variable_name: str) -> dict:
    """Parse ``source`` and return the literal dict assigned to
    ``variable_name`` (the first such assignment found), via
    ``ast.literal_eval`` - no execution of the module. Used to keep a test's
    own hardcoded fixture data honest against the real source, without
    needing to run the module to introspect it."""
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == variable_name for target in node.targets
        ):
            return ast.literal_eval(node.value)
    raise ValueError(f"no assignment to {variable_name!r} found in source")


def registered_transforms(agent) -> list:
    """Recover the ``MessageTransform`` objects registered on an agent via
    ``TransformMessages.add_to_agent`` (which hooks
    ``process_all_messages_before_reply`` with a bound
    ``TransformMessages._transform_messages`` method)."""
    hooks = agent.hook_lists.get("process_all_messages_before_reply", [])
    transforms: list = []
    for hook in hooks:
        bound_self = getattr(hook, "__self__", None)
        transforms.extend(getattr(bound_self, "_transforms", []))
    return transforms


# ---------------------------------------------------------------------------
# C0: per-call usage log (Phase 0 of docs/prompt_caching_plan.md)
#
# Every check takes the module(s) under test, so the live pytest suite and
# `bite_check.py` (baseline and mutant modules) run literally the same code.
# ---------------------------------------------------------------------------

CALL_LOG_ENV = "CMBAGENT_CALL_LOG"
CALL_LOG_MARKER = "hep-theory fork: per-call usage log"


@contextlib.contextmanager
def call_log_env(value):
    """Set ``CMBAGENT_CALL_LOG`` to ``value`` (unset it if ``None``) and
    restore the previous state on exit."""
    old = os.environ.get(CALL_LOG_ENV)
    if value is None:
        os.environ.pop(CALL_LOG_ENV, None)
    else:
        os.environ[CALL_LOG_ENV] = str(value)
    try:
        yield
    finally:
        if old is None:
            os.environ.pop(CALL_LOG_ENV, None)
        else:
            os.environ[CALL_LOG_ENV] = old


class StubNamedAgent:
    """Hashable stand-in for an agent: the wrapper reads ``.name`` and, if
    present, ``.context_variables`` (the plan step number lives there)."""

    def __init__(self, name, step=None, context_variables=None):
        self.name = name
        if context_variables is not None:
            self.context_variables = context_variables
        elif step is not None:
            self.context_variables = {"current_plan_step_number": step}


class RaisingContextVariables:
    """context_variables whose ``.get`` blows up: the step lookup must not raise."""

    def get(self, *args, **kwargs):
        raise RuntimeError("context variables unavailable")


def c0_params() -> dict:
    return {
        "model": TEST_MODEL,
        "system": "You are a careful assistant.",
        "messages": [{"role": "user", "content": "hi"}],
        "tools": [
            {
                "type": "function",
                "function": {
                    "name": "record_plan",
                    "description": "record the plan",
                    "parameters": {"type": "object", "properties": {}},
                },
            }
        ],
    }


def _text_block(text):
    block = MagicMock()
    block.type = "text"
    block.text = text
    return block


def _tool_block():
    block = MagicMock()
    block.type = "tool_use"
    block.id = "toolu_1"
    block.name = "record_plan"
    block.input = {"plan": "x"}
    return block


# Response shapes covering each branch of AnthropicClient.create's response handling.
C0_RESPONSE_KINDS = ("text", "tool_use", "max_tokens")


def c0_response(kind: str = "text", usage: dict | None = None):
    if kind == "text":
        response = make_mock_response([_text_block("hello")], "end_turn")
    elif kind == "tool_use":
        response = make_mock_response([_tool_block()], "tool_use")
    elif kind == "max_tokens":
        response = make_mock_response([], "max_tokens")
    else:
        raise ValueError(kind)
    for key, value in (usage or {}).items():
        setattr(response.usage, key, value)
    return response


def run_c0_create(anthropic_module, *, log: bool, kind: str = "text", usage: dict | None = None) -> dict:
    """One offline ``AnthropicClient.create`` call.

    Returns ``sent`` (deep copy of the kwargs taken at the moment the mocked
    SDK was called), ``sent_after`` (the kwargs object the mock recorded, which
    shares nested objects with the client's own request dict, so it exposes
    any later mutation), ``result`` (the returned completion, minus its
    timestamp) and the ``client``.
    """
    client = make_offline_anthropic_client(anthropic_module)
    snapshots: list = []

    def fake_create(**kwargs):
        snapshots.append(copy.deepcopy(kwargs))
        return c0_response(kind, usage)

    client._client.messages.create.side_effect = fake_create
    with call_log_env(os.devnull if log else None), warnings.catch_warnings():
        warnings.simplefilter("ignore")
        result = client.create(c0_params())
    return {
        "sent": snapshots[0],
        "sent_after": client._client.messages.create.call_args.kwargs,
        "result": result.model_dump(exclude={"created"}),
        "client": client,
    }


def check_off_is_inert(anthropic_module):
    for value in (None, ""):
        client = make_offline_anthropic_client(anthropic_module)
        client._client.messages.create.return_value = c0_response()
        with call_log_env(value):
            client.create(c0_params())
        assert not hasattr(client, "_cmbagent_last_call"), f"record built with {CALL_LOG_ENV}={value!r}"


def check_on_sends_identical_request(anthropic_module):
    for kind in C0_RESPONSE_KINDS:
        off = run_c0_create(anthropic_module, log=False, kind=kind)
        on = run_c0_create(anthropic_module, log=True, kind=kind)
        assert on["sent"] == off["sent"], f"{kind}: request differs with logging on"
        assert on["sent"] == on["sent_after"], f"{kind}: request mutated after the SDK call"


def check_on_returns_identical_response(anthropic_module):
    for kind in C0_RESPONSE_KINDS:
        off = run_c0_create(anthropic_module, log=False, kind=kind)
        on = run_c0_create(anthropic_module, log=True, kind=kind)
        assert on["result"] == off["result"], f"{kind}: returned completion differs with logging on"


def _sha16(obj) -> str:
    s = obj if isinstance(obj, str) else json.dumps(obj, sort_keys=True, default=str)
    return hashlib.sha256(s.encode("utf-8", "replace")).hexdigest()[:16]


C0_USAGE = {
    "input_tokens": 100,
    "cache_creation_input_tokens": 900,
    "cache_read_input_tokens": 50,
    "output_tokens": 7,
}


def check_record_fields(anthropic_module):
    run = run_c0_create(anthropic_module, log=True, usage=C0_USAGE)
    record = getattr(run["client"], "_cmbagent_last_call", None)
    assert isinstance(record, dict), "no record was built"
    sent = run["sent"]
    system = c0_params()["system"]
    assert record["model"] == TEST_MODEL
    assert (
        record["input_tokens"],
        record["cache_creation_input_tokens"],
        record["cache_read_input_tokens"],
        record["output_tokens"],
    ) == (100, 900, 50, 7)
    assert record["system_sha256"] == _sha16(system)
    assert record["system_chars"] == len(system)
    assert re.fullmatch(r"[0-9a-f]{16}", record["tools_sha256"])
    assert record["n_messages"] == len(sent["messages"])
    assert record["first_msg_sha256"] == _sha16(sent["messages"][0])
    assert record["stop_reason"] == "end_turn"

    # A one-character change to the system block must change its hash.
    client = make_offline_anthropic_client(anthropic_module)
    client._client.messages.create.return_value = c0_response()
    params = c0_params()
    params["system"] += "!"
    with call_log_env(os.devnull):
        client.create(params)
    assert client._cmbagent_last_call["system_sha256"] != record["system_sha256"]
    assert client._cmbagent_last_call["system_sha256"] == _sha16(system + "!")

    # `thinking` and `tool_choice` take part in cache validity, so a change in
    # either must show up in the record instead of looking like a stable prefix.
    opts = {record["cache_opts_sha256"]}
    for extra in (
        {"thinking": {"type": "enabled", "budget_tokens": 1024}},
        {"tool_choice": {"type": "tool", "name": "record_plan"}},
    ):
        client = make_offline_anthropic_client(anthropic_module)
        client._client.messages.create.return_value = c0_response()
        with call_log_env(os.devnull):
            client.create({**c0_params(), **extra})
        opts.add(client._cmbagent_last_call["cache_opts_sha256"])
    assert len(opts) == 3, "thinking / tool_choice changes are not visible in the record"


def check_magicmock_usage_not_coerced(anthropic_module):
    # make_mock_response sets only input/output tokens; the cache fields stay
    # MagicMock, and int(MagicMock()) is 1, so coercion would log a bogus 1.
    run = run_c0_create(anthropic_module, log=True)
    record = getattr(run["client"], "_cmbagent_last_call", None)
    assert isinstance(record, dict), "no record was built"
    cache_fields = (record["cache_creation_input_tokens"], record["cache_read_input_tokens"])
    assert cache_fields == (None, None), f"mock usage was coerced to {cache_fields!r}, expected (None, None)"
    assert (record["input_tokens"], record["output_tokens"]) == (1, 1)


def check_record_builder_never_raises(anthropic_module):
    record = anthropic_module._cmbagent_call_record({"messages": 5}, MagicMock())
    assert "error" in record
    # No usage at all, an empty history and a block-list system must all work.
    record = anthropic_module._cmbagent_call_record(
        {"model": TEST_MODEL, "system": [{"type": "text", "text": "x"}], "messages": []}, object()
    )
    assert "error" not in record
    assert record["n_messages"] == 0 and record["first_msg_sha256"] is None
    assert record["input_tokens"] is None and record["system_sha256"] is not None


def make_offline_wrapper(client_module, anthropic_module, response=None):
    """``OpenAIWrapper`` from ``client_module`` whose only client is an offline
    ``AnthropicClient`` from ``anthropic_module`` (mocked SDK)."""
    wrapper = client_module.OpenAIWrapper(
        config_list=[{"api_type": "anthropic", "model": TEST_MODEL, "api_key": "test-key"}]
    )
    offline = make_offline_anthropic_client(anthropic_module)
    offline._client.messages.create.side_effect = lambda **kw: response or c0_response(usage=C0_USAGE)
    wrapper._clients[0] = offline
    return wrapper, offline


def _wrapper_call(wrapper, agent):
    return wrapper.create(messages=[{"role": "user", "content": "hi"}], agent=agent)


def check_wrapper_off_writes_nothing(client_module, anthropic_module, log_path):
    for value in (None, ""):
        wrapper, offline = make_offline_wrapper(client_module, anthropic_module)
        with call_log_env(value):
            _wrapper_call(wrapper, StubNamedAgent("engineer"))
        assert not hasattr(offline, "_cmbagent_last_call")
        assert not Path(log_path).exists()


def check_wrapper_writes_agent_name(client_module, anthropic_module, log_path):
    wrapper, _ = make_offline_wrapper(client_module, anthropic_module)
    engineer = StubNamedAgent("engineer", step=3)
    # (agent, expected name, expected step). The step is read defensively: an
    # agent with no context variables, no step key, or context variables that
    # raise gives step None - never an exception.
    calls = [
        (engineer, "engineer", 3),
        (engineer, "engineer", 3),  # same (client, agent) again: every call must append a line
        (None, None, None),
        (StubNamedAgent("researcher"), "researcher", None),
        (StubNamedAgent("planner", context_variables={}), "planner", None),
        (StubNamedAgent("terminator", context_variables=RaisingContextVariables()), "terminator", None),
    ]
    with call_log_env(log_path):
        for agent, _name, _step in calls:
            _wrapper_call(wrapper, agent)
    path = Path(log_path)
    assert path.exists(), "no log file was written"
    lines = [json.loads(line) for line in path.read_text().splitlines()]
    got = [(rec["agent"], rec.get("step", "<missing>")) for rec in lines]
    want = [(name, step) for _agent, name, step in calls]
    assert got == want, f"logged (agent, step) {got!r}, expected {want!r}"
    for rec in lines:
        assert isinstance(rec["ts"], float)
        assert rec["pid"] == os.getpid(), f"pid {rec.get('pid')!r}"
        assert rec["model"] == TEST_MODEL
        assert (rec["input_tokens"], rec["cache_creation_input_tokens"], rec["cache_read_input_tokens"]) == (
            100,
            900,
            50,
        )
        assert rec["output_tokens"] == 7


def check_logged_when_create_raises(client_module, anthropic_module, log_path):
    """The SDK call was made and billed, then ``create`` raised while handling
    the response: the call must still reach the log."""
    wrapper, offline = make_offline_wrapper(client_module, anthropic_module)
    bad = c0_response(usage=C0_USAGE)
    bad.stop_reason = "tool_use"
    bad.content = None  # iterating it raises TypeError after the SDK call returned
    offline._client.messages.create.side_effect = lambda **kw: bad
    with call_log_env(log_path):
        try:
            _wrapper_call(wrapper, StubNamedAgent("engineer"))
        except TypeError:
            pass
        else:
            raise AssertionError("expected the malformed response to raise")
    path = Path(log_path)
    lines = [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []
    assert len(lines) == 1, f"{len(lines)} line(s) logged for the one billed call that then raised"
    assert lines[0]["agent"] == "engineer" and lines[0]["output_tokens"] == 7


def check_unwritable_path_never_raises(client_module, anthropic_module, bad_path):
    wrapper, _ = make_offline_wrapper(client_module, anthropic_module)
    with call_log_env(bad_path), warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        result = _wrapper_call(wrapper, StubNamedAgent("engineer"))
    assert result.choices[0].message.content == "hello"
    assert any(
        issubclass(w.category, UserWarning) and "CMBAGENT_CALL_LOG write failed" in str(w.message) for w in caught
    ), "no warning about the failed log write"


def check_helper_not_lru_wrapped(client_module):
    # The writer must sit above `@lru_cache`, not between the decorator and
    # `log_cache_seed_value`: memoising it would log only the first call per
    # (client, agent) pair and strip the cache from `log_cache_seed_value`.
    assert hasattr(client_module.log_cache_seed_value, "cache_info"), "log_cache_seed_value lost its lru_cache"
    assert not hasattr(client_module._cmbagent_write_call_log, "cache_info"), "writer is wrapped in lru_cache"


def check_patch_markers(anthropic_source: str, client_source: str):
    assert CALL_LOG_MARKER in anthropic_source, "anthropic.py: call-log patch missing"
    assert CALL_LOG_MARKER in client_source, "client.py: call-log patch missing"


def check_single_sdk_call_site(anthropic_source: str):
    """Exactly one ``<receiver>.messages.<method>(...)`` call and no ``.beta``
    attribute access, so one hook covers every API path. A receiver whose
    source contains "client" or "anthropic" (case-insensitive) counts as an SDK
    client (``self._client``, ``other_client``, ``anthropic.Anthropic()``):
    unrelated ``params.messages.append(...)`` calls are not SDK calls."""
    tree = ast.parse(anthropic_source)
    sdk_calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and isinstance(node.func.value, ast.Attribute)
        and node.func.value.attr == "messages"
        and any(word in ast.unparse(node.func.value.value).lower() for word in ("client", "anthropic"))
    ]
    assert len(sdk_calls) == 1, f"expected 1 SDK messages.* call, found {len(sdk_calls)}"
    assert sdk_calls[0].func.attr == "create", f"the SDK call is messages.{sdk_calls[0].func.attr}, not create"
    beta = [n for n in ast.walk(tree) if isinstance(n, ast.Attribute) and n.attr == "beta"]
    assert not beta, "a .beta SDK path appeared: the call-log hook does not cover it"


def check_patch_script_hygiene(script, base_anthropic: str, base_client: str, tmp_dir):
    """Run the patch script's ``main`` on temporary copies: it patches, a
    second run is a no-op (exit 0, bytes unchanged), and a missing anchor or a
    partial patch exits 1 and leaves both files untouched."""
    a, c = Path(tmp_dir) / "anthropic.py", Path(tmp_dir) / "client.py"

    def run() -> int:
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            return script.main(["--anthropic", str(a), "--client", str(c)])

    def snapshot():
        return a.read_bytes(), c.read_bytes()

    a.write_text(base_anthropic)
    c.write_text(base_client)
    assert run() == 0
    patched = snapshot()
    assert patched != (base_anthropic.encode(), base_client.encode()), "first run changed nothing"
    assert run() == 0 and snapshot() == patched, "second run was not a no-op"

    # Missing anchor in client.py: exit 1, and anthropic.py must stay unpatched too.
    a.write_text(base_anthropic)
    c.write_text(base_client.replace("response = client.create(params)", "response = client.create(params2)"))
    before = snapshot()
    assert run() == 1, "a missing anchor did not exit 1"
    assert snapshot() == before, "files were written despite a missing anchor"

    # A failure while writing the second file must roll the first back.
    a.write_text(base_anthropic)
    c.write_text(base_client)
    before = snapshot()
    real_write, writes = script._write_atomic, []

    def flaky_write(path, text):
        writes.append(path)
        if len(writes) == 2:
            raise OSError("disk full")
        return real_write(path, text)

    script._write_atomic = flaky_write
    try:
        code = run()
    finally:
        script._write_atomic = real_write
    assert code == 1, "a failed write did not exit 1"
    assert snapshot() == before, "the first file was left patched after the second write failed"

    # A file that is not valid UTF-8 is reported, not a traceback.
    a.write_bytes(b"\xff\xfe not utf-8")
    c.write_text(base_client)
    before = snapshot()
    assert run() == 1, "an undecodable file did not exit 1"
    assert snapshot() == before

    # Partial patch (anthropic.py patched, client.py not).
    patched_a, _ = script.apply(base_anthropic, base_client)
    a.write_text(patched_a)
    c.write_text(base_client)
    before = snapshot()
    assert run() == 1, "a partial patch did not exit 1"
    assert snapshot() == before, "files were written over a partial patch"


def check_single_sdk_call_site_precision():
    """The call-site matcher must ignore unrelated ``.messages`` attributes
    and still catch a second SDK path."""
    ok = (
        "class C:\n"
        "    def f(self, params):\n"
        "        self._client.messages.create(**params)\n"
        "        params.messages.append(1)\n"
        "        self.history.messages.extend([])\n"
    )
    check_single_sdk_call_site(ok)
    for extra in (
        "        self._client.messages.stream()\n",
        "        self._client.beta.messages.create()\n",
        "        other_client.messages.parse()\n",
        "        anthropic.Anthropic().messages.create()\n",
    ):
        try:
            check_single_sdk_call_site(ok + extra)
        except AssertionError:
            continue
        raise AssertionError(f"a second SDK path went undetected: {extra.strip()!r}")
