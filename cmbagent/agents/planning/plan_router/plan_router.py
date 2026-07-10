"""
Plan Router Agent - minimal non-LLM pass-through node.

This agent exists SOLELY to host the OnContextCondition-based routing
(feedback_left == 0 -> terminator, else -> plan_reviewer) that used to live on
plan_recorder itself. AG2's swarm framework runs OnContextConditions "before
any other reply function" for whichever agent owns them (confirmed via
autogen/agentchat/group/group_utils.py) — meaning if plan_recorder owned both
its custom Python recording logic AND a pair of mutually-exhaustive
OnContextConditions, the context-condition check would ALWAYS fire first and
ALWAYS produce a definitive routing decision, permanently preventing
plan_recorder's own _record_plan_reply from ever executing (confirmed via
direct instrumentation - see CHANGELOG).

By moving the OnContextCondition pair here, to an agent with NO competing
custom reply logic, plan_recorder can hand off to this node unconditionally
(a plain set_after_work), let its own Python logic run and set final_plan/
proposed_plan/number_of_steps_in_plan, and THEN this node makes the routing
decision using the now-updated context.

No custom reply function is registered here at all — the OnContextCondition
dispatch is the agent's entire behavior, by design.
"""
import os
from cmbagent.base_agent import BaseAgent
from autogen.agentchat import ConversableAgent


class PlanRouterAgent(BaseAgent):
    """Non-LLM pass-through agent; all behavior is via OnContextCondition."""

    def __init__(self, llm_config=None, **kwargs):
        agent_id = os.path.splitext(os.path.abspath(__file__))[0]
        super().__init__(llm_config=llm_config, agent_id=agent_id, **kwargs)

    def set_agent(self, **kwargs):
        """Create a non-LLM agent with no custom reply logic of its own."""
        self.agent = PlanRouterConversableAgent(
            name=self.name,
            description=self.info.get("description", "Plan router agent"),
            llm_config=False,  # No LLM needed
            human_input_mode="NEVER",
        )


class PlanRouterConversableAgent(ConversableAgent):
    """
    A ConversableAgent that doesn't use LLM and has no custom reply function.
    Its entire job is done by the OnContextCondition entries attached to its
    handoffs in hand_offs.py.
    """
    pass
