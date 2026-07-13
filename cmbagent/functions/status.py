"""Functions for status tracking and workflow control."""

import os
from typing import Literal
from autogen.agentchat.group import ContextVariables
from autogen.agentchat.group import AgentTarget, ReplyResult
from autogen.cmbagent_utils import cmbagent_debug, IMG_WIDTH
import autogen

from IPython.display import Image as IPImage, display as ip_display

from .utils import load_docstrings, load_plots


cmbagent_disable_display = autogen.cmbagent_disable_display


def _get_status_icon(status: str) -> str:
    """Get emoji icon for status."""
    status_icons = {
        "completed": "✅",
        "failed": "❌",
        "in progress": "⏳"
    }
    return status_icons.get(status, "")


def _update_context_variables(
    context_variables: ContextVariables,
    current_status: str,
    current_plan_step_number: int,
    current_sub_task: str,
    current_instructions: str,
    agent_for_sub_task: str
) -> None:
    """Update context variables with current step information."""
    # BUG FIX (hep-theory fork): capture the OLD agent_for_sub_task before
    # overwriting it. Confirmed via a real run that controller, when
    # recording a "failed" status after a derivation_checker FAIL, commonly
    # sets agent_for_sub_task to the NEXT agent it's about to invoke (e.g.
    # "cadabra_context") in the SAME record_status call, not to
    # "derivation_checker" itself - a reasonable, natural reading of the
    # field that the increment check below did not originally account for,
    # which meant derivation_review_attempts silently never incremented on
    # a real FAIL. Checking the PREVIOUS value (who the step was actually
    # assigned to when it failed) is correct regardless of which agent
    # controller names as the next hop.
    previous_agent_for_sub_task = context_variables.get("agent_for_sub_task")

    context_variables["current_plan_step_number"] = current_plan_step_number
    context_variables["current_sub_task"] = current_sub_task
    context_variables["agent_for_sub_task"] = agent_for_sub_task
    context_variables["current_instructions"] = current_instructions
    context_variables["current_status"] = current_status

    # Update step_execution_status based on current_status
    # Only the controller (via record_status) can mark a step as "completed"
    if current_status == "completed":
        context_variables["step_execution_status"] = "completed"
    elif current_status == "in progress":
        context_variables["step_execution_status"] = "in_progress"
    # Reset code_execution_status when starting new work
    if current_status == "in progress":
        context_variables["code_execution_status"] = None

    # hep-theory fork: hard-enforced counter for derivation_checker
    # review-fix cycles (see derivation_review_attempts in context.py).
    # Increment on every FAIL/UNRESOLVED-DEGENERATE recorded against
    # derivation_checker's own step; reset whenever any step is recorded
    # completed (a fresh step starts a fresh count). This is independent of
    # the controller's own judgment - the routing functions below enforce
    # the cap regardless of what the controller LLM decides to do next.
    if current_status == "failed" and previous_agent_for_sub_task == "derivation_checker":
        context_variables["derivation_review_attempts"] = (
            context_variables.get("derivation_review_attempts", 0) + 1
        )
    elif current_status == "completed":
        context_variables["derivation_review_attempts"] = 0


def _load_codebase_info(cmbagent_instance, context_variables: ContextVariables) -> str:
    """Load and format docstrings from codebase."""
    codes = os.path.join(cmbagent_instance.work_dir, context_variables['codebase_path'])
    docstrings = load_docstrings(codes)

    output_str = ""
    for module, info in docstrings.items():
        output_str += "-----------\n"
        output_str += f"Filename: {module}.py\n"
        output_str += f"File path: {info['file_path']}\n\n"

        # Show parse errors (if any)
        if "error" in info:
            output_str += f"⚠️  Parse error: {info['error']}\n\n"

        output_str += "Available functions:\n"

        if info["functions"]:
            for func, doc in info["functions"].items():
                output_str += f"function name: {func}\n"
                output_str += "````\n"
                output_str += f"{doc or '(no docstring)'}\n"
                output_str += "````\n\n"
        else:
            output_str += "(none)\n\n"

    return output_str


def _display_new_images(cmbagent_instance, context_variables: ContextVariables) -> None:
    """Load and display new plot images from data directory."""
    data_directory = os.path.join(cmbagent_instance.work_dir, context_variables['database_path'])
    image_files = load_plots(data_directory)

    displayed_images = context_variables.get("displayed_images", [])
    new_images = [img for img in image_files if img not in displayed_images]

    for img_file in new_images:
        if not cmbagent_disable_display:
            ip_display(IPImage(filename=img_file, width=2 * IMG_WIDTH))
        else:
            print(f"\n- Saved {img_file}")

    context_variables["displayed_images"] = displayed_images + new_images


def _initialize_transfer_flags(context_variables: ContextVariables) -> None:
    """Initialize all agent transfer flags to False."""
    # hep-theory fork: added inspirehep_context/cadabra_context/derivation_checker
    agent_transfer_map = {
        "engineer": "transfer_to_engineer",
        "researcher": "transfer_to_researcher",
        "idea_maker": "transfer_to_idea_maker",
        "idea_hater": "transfer_to_idea_hater",
        "camb_context": "transfer_to_camb_context",
        "inspirehep_context": "transfer_to_inspirehep_context",
        "cadabra_context": "transfer_to_cadabra_context",
        "derivation_checker": "transfer_to_derivation_checker",
    }

    for flag_name in agent_transfer_map.values():
        context_variables[flag_name] = False
    context_variables["transfer_to_classy_context"] = False


def _determine_next_agent_human_in_loop(cmbagent_instance, context_variables: ContextVariables):
    """Determine next agent for human-in-the-loop mode."""
    # hep-theory fork: added inspirehep_context/cadabra_context/derivation_checker
    agent_transfer_map = {
        "engineer": "transfer_to_engineer",
        "researcher": "transfer_to_researcher",
        "idea_maker": "transfer_to_idea_maker",
        "idea_hater": "transfer_to_idea_hater",
        "camb_context": "transfer_to_camb_context",
        "inspirehep_context": "transfer_to_inspirehep_context",
        "cadabra_context": "transfer_to_cadabra_context",
        "derivation_checker": "transfer_to_derivation_checker",
    }

    agent_to_transfer_to = None

    if "in progress" in context_variables["current_status"]:
        agent_name = context_variables["agent_for_sub_task"]
        if agent_name in agent_transfer_map:
            transfer_flag = agent_transfer_map[agent_name]
            context_variables[transfer_flag] = True
            agent_to_transfer_to = cmbagent_instance.get_agent_from_name(agent_name)

    if "completed" in context_variables["current_status"]:
        agent_to_transfer_to = cmbagent_instance.get_agent_from_name('admin')
        context_variables["n_attempts"] = 0

    if "failed" in context_variables["current_status"]:
        if context_variables["agent_for_sub_task"] == "engineer":
            agent_to_transfer_to = cmbagent_instance.get_agent_from_name('engineer')
        elif context_variables["agent_for_sub_task"] == "researcher":
            agent_to_transfer_to = cmbagent_instance.get_agent_from_name('researcher_response_formatter')
        elif context_variables["agent_for_sub_task"] in (
            "derivation_checker", "cadabra_context", "inspirehep_context"
        ):
            # hep-theory fork: same rationale as _determine_next_agent_default -
            # a derivation_checker FAIL/UNRESOLVED-DEGENERATE doesn't have a
            # single fixed agent to hand back to. In this mode a human is
            # already driving the loop, so surface the failure back to them
            # (as "completed" already does above) rather than guessing which
            # upstream agent to re-invoke automatically.
            agent_to_transfer_to = cmbagent_instance.get_agent_from_name('admin')

    return agent_to_transfer_to


def _determine_next_agent_default(cmbagent_instance, context_variables: ContextVariables):
    """Determine next agent for default mode."""
    # hep-theory fork: added inspirehep_context/cadabra_context/derivation_checker
    agent_transfer_map = {
        "engineer": "transfer_to_engineer",
        "researcher": "transfer_to_researcher",
        "idea_maker": "transfer_to_idea_maker",
        "idea_hater": "transfer_to_idea_hater",
        "camb_context": "transfer_to_camb_context",
        "inspirehep_context": "transfer_to_inspirehep_context",
        "cadabra_context": "transfer_to_cadabra_context",
        "derivation_checker": "transfer_to_derivation_checker",
    }

    agent_to_transfer_to = None

    if "in progress" in context_variables["current_status"]:
        agent_name = context_variables["agent_for_sub_task"]

        # BUG FIX (hep-theory fork): this used to check the mismatch below
        # and force terminator, AFTER already computing agent_to_transfer_to
        # above - now it clamps and corrects first. Confirmed via a real
        # run: controller, after correctly detecting a derivation_checker
        # FAIL and correctly re-invoking the responsible upstream agent,
        # mistakenly set current_plan_step_number back to the ORIGINAL
        # step being redone (e.g. 1, for "I am redoing step 1's work")
        # rather than leaving it at the step THIS conversation is scoped to
        # (e.g. 4) - an understandable field-meaning ambiguity for an LLM,
        # not a case that ever legitimately needs a different step number
        # within a single deep_research() solve() call. The mismatch guard
        # then force-terminated the run immediately, discarding a freshly
        # regenerated derivation that had not yet been forwarded back to
        # derivation_checker for re-review. There is no legitimate scenario
        # in this architecture where current_plan_step_number should differ
        # from cmbagent_instance.step within one solve() call, so silently
        # correcting it and continuing is strictly safer than terminating.
        if cmbagent_instance.mode == "deep_research" and \
           context_variables["current_plan_step_number"] != cmbagent_instance.step:
            context_variables["current_plan_step_number"] = cmbagent_instance.step

        if agent_name in agent_transfer_map:
            transfer_flag = agent_transfer_map[agent_name]
            context_variables[transfer_flag] = True
            agent_to_transfer_to = cmbagent_instance.get_agent_from_name(agent_name)

    if "completed" in context_variables["current_status"]:
        if context_variables["current_plan_step_number"] == context_variables["number_of_steps_in_plan"]:
            agent_to_transfer_to = cmbagent_instance.get_agent_from_name('terminator')
        else:
            agent_to_transfer_to = cmbagent_instance.get_agent_from_name('controller')
            if cmbagent_instance.mode != "deep_research":
                context_variables["n_attempts"] = 0

    if "failed" in context_variables["current_status"]:
        if context_variables["agent_for_sub_task"] == "engineer":
            agent_to_transfer_to = cmbagent_instance.get_agent_from_name('engineer')
        elif context_variables["agent_for_sub_task"] == "researcher":
            agent_to_transfer_to = cmbagent_instance.get_agent_from_name('researcher_response_formatter')
        elif context_variables["agent_for_sub_task"] in (
            "derivation_checker", "cadabra_context", "inspirehep_context"
        ):
            # hep-theory fork: a "failed" status here means derivation_checker
            # returned FAIL/UNRESOLVED-DEGENERATE on the current step's content
            # (or, less commonly, cadabra_context/inspirehep_context themselves
            # errored out). There is no single fixed agent to hand this back to
            # the way engineer/researcher retry themselves - the correct next
            # agent depends on which "Required fix" items derivation_checker
            # raised, which only controller (reading current_instructions and
            # the plan) can judge. Route explicitly back to controller rather
            # than relying on the implicit agent_to_transfer_to=None fallback,
            # so this path is documented and doesn't silently break if that
            # fallback's default target ever changes. controller.yaml is
            # responsible for then re-invoking the correct upstream agent
            # (staying on the SAME current_plan_step_number - jumping back to
            # an earlier step number will trigger the step-mismatch guard
            # above and force an early terminator call).
            #
            # Hard-enforced retry cap: this does not rely on the controller
            # LLM correctly following its own "cap at 2 re-attempts"
            # instruction. Once derivation_review_attempts reaches
            # max_derivation_review_attempts, force termination here in code,
            # regardless of what controller would otherwise decide.
            attempts = context_variables.get("derivation_review_attempts", 0)
            max_attempts = context_variables.get("max_derivation_review_attempts", 3)
            if attempts >= max_attempts:
                agent_to_transfer_to = cmbagent_instance.get_agent_from_name('terminator')
            else:
                agent_to_transfer_to = cmbagent_instance.get_agent_from_name('controller')

    return agent_to_transfer_to


def _format_status_message(context_variables: ContextVariables, icon: str) -> str:
    """Format the status message."""
    code_status = context_variables.get("code_execution_status", "N/A")
    step_status = context_variables.get("step_execution_status", "pending")
    derivation_attempts = context_variables.get("derivation_review_attempts", 0)
    max_derivation_attempts = context_variables.get("max_derivation_review_attempts", 3)
    # hep-theory fork: only surface this line once at least one derivation
    # review cycle has actually failed, so it doesn't clutter unrelated steps.
    derivation_attempts_line = (
        f"\n**Derivation review attempts:** {derivation_attempts} / {max_derivation_attempts}"
        if derivation_attempts > 0 else ""
    )

    return f"""
**Step number:** {context_variables["current_plan_step_number"]} out of {context_variables["number_of_steps_in_plan"]}.

**Sub-task:** {context_variables["current_sub_task"]}

**Agent in charge of sub-task:** `{context_variables["agent_for_sub_task"]}`

**Instructions:**

{context_variables["current_instructions"]}

**Controller status:** {context_variables["current_status"]} {icon}

**Code execution status:** {code_status}

**Step execution status:** {step_status}
{derivation_attempts_line}
        """


def create_record_status(cmbagent_instance, controller):
    """Factory function to create record_status with cmbagent instance."""

    def record_status(
        current_status: Literal["in progress", "failed", "completed"],
        current_plan_step_number: int,
        current_sub_task: str,
        current_instructions: str,
        agent_for_sub_task: Literal["engineer", "researcher", "idea_maker", "idea_hater",
                                    "camb_context", "classy_context", "aas_keyword_finder",
                                    "inspirehep_context", "cadabra_context", "derivation_checker"],
        context_variables: ContextVariables
    ) -> ReplyResult:
        """
        Updates the execution context and returns the current progress.
        Must be called **before calling the agent in charge of the next sub-task**.
        Must be called **after** each action taken.

        Args:
            current_status (str): The current status ("in progress", "failed", or "completed").
            current_plan_step_number (int): The current step number in the plan.
            current_sub_task (str): Description of the current sub-task.
            current_instructions (str): Instructions for the sub-task.
            agent_for_sub_task (str): The agent responsible for the sub-task in the current step.
            context_variables (dict): Execution context dictionary.

        Returns:
            ReplyResult: Contains a formatted status message and updated context.
        """
        # Get status icon
        icon = _get_status_icon(current_status)

        # Update context variables
        _update_context_variables(
            context_variables, current_status, current_plan_step_number,
            current_sub_task, current_instructions, agent_for_sub_task
        )

        print("previous_steps_execution_summary: ", context_variables["previous_steps_execution_summary"])

        # Load codebase information
        context_variables["current_codebase"] = _load_codebase_info(cmbagent_instance, context_variables)

        # Display new images
        _display_new_images(cmbagent_instance, context_variables)

        # Initialize transfer flags
        _initialize_transfer_flags(context_variables)

        # Determine next agent based on mode
        if cmbagent_instance.mode == "human_in_the_loop":
            agent_to_transfer_to = _determine_next_agent_human_in_loop(cmbagent_instance, context_variables)
        else:
            agent_to_transfer_to = _determine_next_agent_default(cmbagent_instance, context_variables)

        # Debug logging
        if cmbagent_debug:
            if agent_to_transfer_to is None:
                print("agent_to_transfer_to is None")
            else:
                print("agent_to_transfer_to: ", agent_to_transfer_to.name)

        # Format and return result
        message = _format_status_message(context_variables, icon)

        if agent_to_transfer_to is None:
            target = AgentTarget(controller)
        else:
            target = AgentTarget(agent_to_transfer_to)

        return ReplyResult(target=target, message=message, context_variables=context_variables)

    return record_status


def create_record_status_starter(cmbagent_instance):
    """Factory function to create record_status_starter with cmbagent instance."""

    def record_status_starter(context_variables: ContextVariables) -> ReplyResult:
        """
        Updates the execution context and returns the current progress.
        Must be called **before calling the agent in charge of the next sub-task**.
        Must be called **after** each action taken.

        Args:
            context_variables (dict): Execution context dictionary.

        Returns:
            ReplyResult: Contains a formatted status message and updated context.
        """

        current_status = "in progress"

        # BUG FIX (hep-theory fork): this function previously computed the
        # local `current_status = "in progress"` above but never wrote it
        # into context_variables before checking
        # context_variables["current_status"] a few lines down - so the
        # check always saw whatever the PREVIOUS step left behind (always
        # "completed", from a normal step ending), never "in progress".
        # Confirmed via direct reproduction: this caused a deterministic
        # crash (AttributeError: 'NoneType' object has no attribute 'name',
        # from AgentTarget(None)) at the start of EVERY step after step 1 in
        # deep_research() runs - control_starter would retry
        # record_status_starter repeatedly, sometimes recovering later in
        # the conversation via a different tool call, sometimes (as
        # observed) never recovering within max_rounds_control, burning the
        # entire round budget on nothing but this error with zero actual
        # step content produced. Fixed by actually writing the intended
        # status before checking it - this function's whole purpose is to
        # kick off a fresh step by handing off to agent_for_sub_task, so
        # there is no legitimate case where it should NOT do that.
        context_variables["current_status"] = current_status

        # Map statuses to icons
        status_icons = {
            "completed": "✅",
            "failed": "❌",
            "in progress": "⏳"
        }

        icon = status_icons.get(current_status, "")

        # Map agent names to their transfer flag names
        # hep-theory fork: added inspirehep_context/cadabra_context/derivation_checker
        agent_transfer_map = {
            "engineer": "transfer_to_engineer",
            "researcher": "transfer_to_researcher",
            "idea_maker": "transfer_to_idea_maker",
            "idea_hater": "transfer_to_idea_hater",
            "camb_context": "transfer_to_camb_context",
            "inspirehep_context": "transfer_to_inspirehep_context",
            "cadabra_context": "transfer_to_cadabra_context",
            "derivation_checker": "transfer_to_derivation_checker",
        }

        # Initialize all transfer flags to False
        for flag_name in agent_transfer_map.values():
            context_variables[flag_name] = False

        agent_to_transfer_to = None
        if "in progress" in context_variables["current_status"]:
            agent_name = context_variables["agent_for_sub_task"]
            if agent_name in agent_transfer_map:
                transfer_flag = agent_transfer_map[agent_name]
                context_variables[transfer_flag] = True
                agent_to_transfer_to = cmbagent_instance.get_agent_from_name(agent_name)

        return ReplyResult(
            target=AgentTarget(agent_to_transfer_to),
            message=f"""
**Step number:** {context_variables["current_plan_step_number"]} out of {context_variables["number_of_steps_in_plan"]}.\n
**Sub-task:** {context_variables["current_sub_task"]}\n
**Agent in charge of sub-task:** `{context_variables["agent_for_sub_task"]}`\n
**Instructions:**\n
{context_variables["current_instructions"]}\n
**Status:** {context_variables["current_status"]} {icon}
""",
            context_variables=context_variables
        )

    return record_status_starter
