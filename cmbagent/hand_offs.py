from autogen.agentchat.group import AgentTarget, TerminateTarget, OnCondition, StringLLMCondition, OnContextCondition
from autogen.agentchat.group.context_condition import ExpressionContextCondition
from autogen import ContextExpression
from autogen.cmbagent_utils import cmbagent_debug
import autogen
from autogen import GroupChatManager, GroupChat
from autogen.agentchat.contrib.capabilities.transform_messages import TransformMessages
from autogen.agentchat.contrib.capabilities.transforms import MessageHistoryLimiter

cmbagent_debug = autogen.cmbagent_utils.cmbagent_debug


class ToolSafeMessageHistoryLimiter:
    """Like MessageHistoryLimiter, but never leaves an orphaned tool-result
    message (role == "tool") at the front of the truncated window.

    hep-theory fork: the plain MessageHistoryLimiter cuts strictly by count,
    which can land the window boundary between an assistant message's
    tool_calls and the corresponding tool-result message. Anthropic's API
    rejects a "tool" role message that isn't immediately preceded by the
    assistant message that issued the matching tool_call - so a naive
    count-based cut intermittently breaks tool-heavy agents (engineer,
    inspirehep_context, cadabra_context, derivation_checker) after this
    limiter was added to bound the group chat's shared-history resend cost.
    This variant keeps trimming forward, one message at a time, until the
    window's first (non-kept) message is not an orphaned tool result.
    """

    def __init__(self, max_messages=None, keep_first_message=False):
        if max_messages is not None and max_messages < 1:
            raise ValueError("max_messages must be None or greater than 1")
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

        # Drop leading orphaned tool-result messages: a "tool" role message
        # is only valid if the assistant message carrying its matching
        # tool_calls is still present earlier in the window.
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


def register_all_hand_offs(cmbagent_instance):
    """Register all agent handoffs in a data-driven, Pythonic way."""

    if cmbagent_debug:
        print('\nregistering all hand_offs...')

    mode = cmbagent_instance.mode

    # ============================================================================
    # 1. AGENT RETRIEVAL - Use dictionary comprehension for bulk retrieval
    # ============================================================================

    # Core agents (always needed)
    core_agent_names = [
        'planner', 'planner_response_formatter',
        'plan_recorder', 'plan_reviewer', 'reviewer_response_formatter', 'review_recorder',
        'idea_maker', 'idea_maker_response_formatter', 'idea_hater', 'idea_hater_response_formatter',
        'researcher', 'researcher_response_formatter', 'engineer', 'engineer_response_formatter',
        'summarizer', 'summarizer_response_formatter',
        'executor', 'researcher_executor', 'executor_bash', 'terminator', 'controller',
        'admin', 'aas_keyword_finder', 'executor_response_formatter',
        'plan_setter', 'installer', 'engineer_nest', 'idea_saver',
        'camb_context',
        'camb_response_formatter',
        'inspirehep_context',
        'cadabra_context',
        'derivation_checker',
        'plan_router',  # hep-theory fork: plan_router decoupling
    ]

    # Retrieve all core agents at once
    agents = {
        name: cmbagent_instance.get_agent_object_from_name(name)
        for name in core_agent_names
    }

    # ============================================================================
    # 2. SIMPLE HANDOFF CHAINS - Use data structure + loop
    # ============================================================================

    # Define simple A -> B handoff chains
    simple_handoffs = [
        # Planning flow
        ('plan_setter', 'planner'),
        ('planner', 'planner_response_formatter'),
        ('planner_response_formatter', 'plan_recorder'),
        # plan_recorder has conditional handoff (see below)
        ('plan_reviewer', 'reviewer_response_formatter'),
        ('reviewer_response_formatter', 'review_recorder'),
        ('review_recorder', 'planner'),

        # Coding and Execution flow
        ('engineer', 'engineer_nest'),
        ('engineer_nest', 'executor_response_formatter'),
        ('installer', 'executor_bash'),
        ('executor_bash', 'executor_response_formatter'),

        # Research flow
        ('researcher', 'researcher_response_formatter'),
        ('researcher_response_formatter', 'researcher_executor'),
        ('researcher_executor', 'controller'),

        # Summarizer flow
        ('summarizer', 'summarizer_response_formatter'),
        ('summarizer_response_formatter', 'terminator'),

        # Idea flow
        ('idea_hater', 'idea_hater_response_formatter'),
        ('idea_hater_response_formatter', 'controller'),
        ('idea_maker', 'idea_maker_response_formatter'),
        ('idea_maker_response_formatter', 'idea_saver'),
        ('idea_saver', 'controller'),

        # Other flows
        ('aas_keyword_finder', 'controller'),

        # Context agents
        ('camb_context', 'camb_response_formatter'),

        # Theory context agents
        ('inspirehep_context', 'controller'),
        ('cadabra_context', 'controller'),
        ('derivation_checker', 'controller'),
    ]

    # Apply simple handoffs
    for source, target in simple_handoffs:
        agents[source].agent.handoffs.set_after_work(AgentTarget(agents[target].agent))

    # ============================================================================
    # 3. CONDITIONAL HANDOFFS - Based on context variables
    # ============================================================================

    # plan_recorder: conditional routing based on feedback_left
    # If feedback_left == 0, planning is complete.
    # hep-theory fork: planning being complete does NOT always mean the run
    # is done. For a genuine single-call planning_and_control run
    # (mode == "planning_and_control", the CMBAgent __init__ default), this
    # MUST hand off to controller so the control phase (engineer/researcher/
    # inspirehep_context/cadabra_context/derivation_checker) actually runs -
    # previously this branch always targeted terminator regardless of mode,
    # so planning_and_control runs terminated immediately after planning and
    # never reached the control phase at all.
    # For deep_research's planning-only phase (mode == "deep_research", set
    # explicitly on that CMBAgent instance in deep_research.py), terminator
    # remains correct: deep_research's own outer Python loop takes over from
    # there via separate solve() calls per plan step, and must not have
    # plan_router redirect it into an in-process control phase instead.
    # Otherwise, continue to plan_reviewer for feedback.
    # hep-theory fork: plan_router decoupling.
    # plan_recorder now hands off unconditionally to plan_router, so its own
    # Python logic (_record_plan_reply) actually gets to run and set
    # final_plan/proposed_plan/number_of_steps_in_plan. plan_router (which has
    # no competing custom reply logic of its own) carries the actual
    # feedback_left-based routing decision.
    agents['plan_recorder'].agent.handoffs.set_after_work(AgentTarget(agents['plan_router'].agent))

    plan_complete_target = 'terminator' if mode == "deep_research" else 'controller'

    agents['plan_router'].agent.handoffs.add_context_conditions([
        OnContextCondition(
            target=AgentTarget(agents[plan_complete_target].agent),
            condition=ExpressionContextCondition(ContextExpression("${feedback_left} == 0")),
        ),
        OnContextCondition(
            target=AgentTarget(agents['plan_reviewer'].agent),
            condition=ExpressionContextCondition(ContextExpression("${feedback_left} != 0")),
        ),
    ])

    # Response formatters that route differently based on mode
    mode_dependent_formatters = ['camb_response_formatter']
    target = 'engineer' if mode == "one_shot" else 'controller'

    for formatter in mode_dependent_formatters:
        agents[formatter].agent.handoffs.set_after_work(AgentTarget(agents[target].agent))

    # ============================================================================
    # 4. MESSAGE HISTORY LIMITING - Use list + loop
    # ============================================================================

    # Formatter/recorder agents only need the last message
    formatter_context = TransformMessages(
        transforms=[MessageHistoryLimiter(max_messages=1)],
    )

    limited_history_agents = [
        'executor_response_formatter', 'planner_response_formatter', 'plan_recorder',
        'reviewer_response_formatter', 'review_recorder', 'researcher_response_formatter',
        'researcher_executor', 'idea_maker_response_formatter', 'idea_hater_response_formatter',
        'summarizer_response_formatter', 'idea_saver',
    ]

    for agent_name in limited_history_agents:
        formatter_context.add_to_agent(agents[agent_name].agent)

    # Controller: keep recent messages + first message (plan state is in context variables)
    controller_context = TransformMessages(
        transforms=[MessageHistoryLimiter(max_messages=5, keep_first_message=True)],
    )
    controller_context.add_to_agent(agents['controller'].agent)


    # Controller: keep recent messages + first message (plan state is in context variables)
    terminator_context = TransformMessages(
        transforms=[MessageHistoryLimiter(max_messages=1)],
    )
    terminator_context.add_to_agent(agents['terminator'].agent)


    # hep-theory fork: bound the shared group-chat resend cost for the
    # heavy LLM worker agents. AG2's GroupChat broadcasts every message to
    # every agent, so an agent invoked later in a plan step (including via
    # the controller's dynamic mid-step routing) inherits and re-pays for
    # the ENTIRE accumulated shared history on every one of its own turns -
    # on top of whatever the max_consecutive_auto_reply turn cap already
    # bounds for that agent's own reply count. This is upstream AG2 group-
    # chat behavior (broadcast-to-all with no default windowing), not
    # fork-specific. controller/formatters/recorders were already covered
    # above; this extends the same TransformMessages/MessageHistoryLimiter
    # mechanism to the agents that actually do most of the LLM work and
    # were previously left unbounded. Uses the tool-safe variant since
    # these agents make heavy use of tool calls, where a naive count-based
    # cut can strand an orphaned tool-result message at the window start.
    heavy_worker_context = TransformMessages(
        transforms=[ToolSafeMessageHistoryLimiter(max_messages=20, keep_first_message=True)],
    )

    heavy_worker_agents = [
        'engineer', 'researcher',
        'inspirehep_context', 'cadabra_context', 'derivation_checker',
    ]

    for agent_name in heavy_worker_agents:
        heavy_worker_context.add_to_agent(agents[agent_name].agent)


    # ============================================================================
    # 6. NESTED CHATS - Helper function to reduce duplication
    # ============================================================================

    def setup_nested_chat(trigger_agent, manager_name, chat_agents, max_round=3):
        """Helper to set up nested chat pattern."""
        group_chat = GroupChat(
            agents=[agents[name].agent for name in chat_agents],
            messages=[],
            max_round=max_round,
            speaker_selection_method='round_robin',
        )

        manager = GroupChatManager(
            groupchat=group_chat,
            llm_config=cmbagent_instance.llm_config,
            name=manager_name,
        )

        nested_chats = [{
            "recipient": manager,
            "message": lambda recipient, messages, sender, config: f"{messages[-1]['content']}" if messages else "",
            "max_turns": 1,
            "summary_method": "last_msg",
        }]

        # Create trigger: all agents except the trigger agent
        other_agents = [agent for agent in cmbagent_instance.agents if agent != agents[trigger_agent].agent]

        agents[f"{trigger_agent}_nest"].agent.register_nested_chats(
            trigger=lambda sender: sender not in other_agents,
            chat_queue=nested_chats
        )

    # Set up nested chats
    setup_nested_chat(
        trigger_agent='engineer',
        manager_name='engineer_nested_chat',
        chat_agents=['engineer_response_formatter', 'executor'],
        max_round=3
    )

    # Note: idea_maker flow now uses simple handoffs (no nested chat needed)
    # idea_maker → idea_maker_response_formatter → idea_saver → controller

    # ============================================================================
    # 7. TERMINATOR & CONTROLLER SETUP
    # ============================================================================

    # Terminator always terminates
    agents['terminator'].agent.handoffs.set_after_work(TerminateTarget())

    # Controller behavior depends on mode
    if mode == "human_in_the_loop":
        agent_on = cmbagent_instance.get_agent_object_from_name(cmbagent_instance.chat_agent)
        agents['controller'].agent.handoffs.set_after_work(AgentTarget(agents['admin'].agent))
        agents['admin'].agent.handoffs.set_after_work(AgentTarget(agent_on.agent))
    else:
        agents['controller'].agent.handoffs.set_after_work(AgentTarget(agents['terminator'].agent))

        # Controller LLM conditions - use data structure
        controller_conditions = [
            ('engineer', "Code execution failed."),
            ('researcher', "Researcher needed to generate reasoning, write report, or interpret results"),
            ('engineer', "Engineer needed to write code, make plots, do calculations."),
            ('idea_maker', "idea_maker needed to make new ideas"),
            ('idea_hater', "idea_hater needed to critique ideas"),
            ('terminator', "The task is completed."),
            ('inspirehep_context', "inspirehep_context needed to retrieve or verify HEP-theory literature."),
            ('cadabra_context', "cadabra_context needed for symbolic tensor/index algebra guidance."),
            ('derivation_checker', "derivation_checker needed to critique a derivation before accepting it."),
        ]

        agents['controller'].agent.handoffs.add_llm_conditions([
            OnCondition(
                target=AgentTarget(agents[target_agent].agent),
                condition=StringLLMCondition(prompt=prompt)
            )
            for target_agent, prompt in controller_conditions
        ])

    if cmbagent_debug:
        print('\nall hand_offs registered...')
