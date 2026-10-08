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
