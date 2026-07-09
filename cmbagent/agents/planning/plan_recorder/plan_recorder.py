"""
Plan Recorder Agent - Non-LLM agent that records plans.

This agent replaces the LLM-based plan_recorder with a pure Python implementation.
It parses the formatted plan from planner_response_formatter, extracts the step count,
and updates context_variables accordingly.
"""

import os
from cmbagent.base_agent import BaseAgent
from autogen.agentchat import ConversableAgent
from autogen.agentchat.group import ContextVariables

# Import the plan parser from planner_response_formatter
from cmbagent.agents.planning.planner_response_formatter.planner_response_formatter import _parse_plan_string


class PlanRecorderAgent(BaseAgent):
    """Non-LLM agent that records plans by parsing the formatted output."""

    def __init__(self, llm_config=None, **kwargs):
        agent_id = os.path.splitext(os.path.abspath(__file__))[0]
        # Pass llm_config to parent but we won't use it
        super().__init__(llm_config=llm_config, agent_id=agent_id, **kwargs)

    def set_agent(self, **kwargs):
        """Create a non-LLM agent that parses and records plans."""
        self.agent = PlanRecorderConversableAgent(
            name=self.name,
            description=self.info.get("description", "Plan recorder agent"),
            llm_config=False,  # No LLM needed
            human_input_mode="NEVER",
        )


class PlanRecorderConversableAgent(ConversableAgent):
    """
    A ConversableAgent that doesn't use LLM.
    Instead, it parses the incoming plan and updates context_variables.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Register our custom reply function
        self.register_reply(
            trigger=lambda sender: True,  # Reply to any sender
            reply_func=self._record_plan_reply,
            position=0,  # High priority
        )

    def _record_plan_reply(
        self,
        recipient: ConversableAgent,
        messages: list[dict],
        sender: ConversableAgent,
        config: dict,
    ) -> tuple[bool, str]:
        """
        Parse the plan from the last message and record it in context_variables.

        Returns:
            Tuple of (True, message) indicating the reply was generated.
        """
        if not messages:
            return True, "No message to process."

        # hep-theory fork: search full history for real plan content.
        # messages[-1] (this agent's narrow per-sender view) is often an empty
        # placeholder attributed to _Group_Tool_Executor rather than the real
        # formatted plan text - search across ALL conversation partners for the
        # most recent substantive message from planner_response_formatter.
        content = ""
        try:
            all_partners = recipient._oai_messages
            candidates = []
            for partner, msg_list in all_partners.items():
                for m in msg_list:
                    if m.get("name") == "planner_response_formatter" and m.get("content"):
                        candidates.append(m)
            if candidates:
                content = candidates[-1].get("content", "")
        except Exception as e:
            print(f">>> DIAGNOSTIC plan_recorder: full-history search failed: {e}")

        if not content:
            # fall back to the original narrow view, in case the search above
            # legitimately found nothing (e.g. different agent name/flow)
            last_message = messages[-1] if messages else {}
            content = last_message.get("content", "")


        # Parse the formatted plan string to get structured data
        try:
            subtasks = _parse_plan_string(content)
            number_of_steps = len(subtasks)
        except Exception as e:
            # If parsing fails, try to count steps manually
            import re
            step_pattern = r"- Step \d+:"
            matches = re.findall(step_pattern, content)
            number_of_steps = len(matches)

        # The plan suggestion is the full content
        plan_suggestion = content

        # Update context_variables (accessed via the agent's context)
        # Note: context_variables is managed by the swarm/group system
        # self.context_variables is automatically set by AG2 before generate_reply
        ctx = self.context_variables

        # Record the plan - use .get() to safely access lists
        plans = ctx.get("plans", [])
        if not isinstance(plans, list):
            plans = []
        plans.append(plan_suggestion)
        ctx["plans"] = plans
        ctx["proposed_plan"] = plan_suggestion
        ctx["number_of_steps_in_plan"] = number_of_steps

        # Check if this is the final plan (no feedback left)
        feedback_left = ctx.get("feedback_left", 1)
        if feedback_left == 0:
            ctx["final_plan"] = plan_suggestion
            return True, "Plan recorded as final. Planning stage complete."
        else:
            return True, "Plan has been logged."
