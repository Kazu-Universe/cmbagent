"""Deep research workflow for CMBAgent.

This workflow implements a multi-step research process with planning and iterative
execution phases. It creates a plan first, then executes each step with full context
carryover between steps.
"""

import os
import json
import time
import copy
import datetime
import pickle
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..execution.remote_executor import RemoteWebSocketCodeExecutor

from ..agents.planning.planner_response_formatter.planner_response_formatter import save_final_plan
from ..utils import (
    work_dir_default,
    default_llm_model as default_llm_model_default,
    default_formatter_model as default_formatter_model_default,
    default_agents_llm_model,
    get_model_config,
    get_api_keys_from_env
)
from ..context import shared_context as shared_context_default


def load_context(context_path):
    """Load context from a pickle file.

    Parameters
    ----------
    context_path : str
        Path to the pickle file containing the context

    Returns
    -------
    dict
        The loaded context dictionary
    """
    with open(context_path, 'rb') as f:
        context = pickle.load(f)
    return context


def clean_work_dir(work_dir):
    """Clean the work directory by removing all files and subdirectories.

    Parameters
    ----------
    work_dir : str
        Path to the work directory to clean
    """
    import shutil
    if os.path.exists(work_dir):
        shutil.rmtree(work_dir)


def write_file_with_sync(
    filepath: str,
    content: str,
    work_dir: str,
    custom_executor: "RemoteWebSocketCodeExecutor | None" = None,
    encoding: str = "utf-8"
) -> None:
    """Write a file locally and optionally sync to frontend.

    When a custom_executor is provided (remote mode), the file is also
    sent to the frontend via WebSocket.

    Parameters
    ----------
    filepath : str
        Absolute path to write the file
    content : str
        File content to write
    work_dir : str
        Base work directory (used to compute relative path for frontend)
    custom_executor : RemoteWebSocketCodeExecutor, optional
        If provided, also sends the file to the frontend
    encoding : str
        File encoding (default: utf-8)
    """
    # Always write locally (backend may need it for subsequent operations)
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, 'w', encoding=encoding) as f:
        f.write(content)

    # If remote mode, also send to frontend
    if custom_executor is not None:
        try:
            # Compute relative path from work_dir
            rel_path = os.path.relpath(filepath, work_dir)
            custom_executor.send_file(rel_path, content, encoding)
        except Exception as e:
            print(f"Warning: Failed to sync file to frontend: {e}")


def deep_research(
    task,
    max_rounds_planning=50,
    max_rounds_control=100,
    max_plan_steps=3,
    n_plan_reviews=1,
    plan_instructions='',
    engineer_instructions='',
    researcher_instructions='',
    hardware_constraints='',
    max_n_attempts=3,
    planner_model=default_agents_llm_model['planner'],
    plan_reviewer_model=default_agents_llm_model['plan_reviewer'],
    engineer_model=default_agents_llm_model['engineer'],
    researcher_model=default_agents_llm_model['researcher'],
    idea_maker_model=default_agents_llm_model['idea_maker'],
    idea_hater_model=default_agents_llm_model['idea_hater'],
    camb_context_model=default_agents_llm_model['camb_context'],
    # hep-theory fork: added inspirehep_context, cadabra_context, derivation_checker
    inspirehep_context_model=default_agents_llm_model['inspirehep_context'],
    cadabra_context_model=default_agents_llm_model['cadabra_context'],
    derivation_checker_model=default_agents_llm_model['derivation_checker'],
    default_llm_model=default_llm_model_default,
    default_formatter_model=default_formatter_model_default,
    work_dir=work_dir_default,
    api_keys=None,
    restart_at_step=-1,
    clear_work_dir=False,
    researcher_filename=shared_context_default['researcher_filename'],
    custom_executor=None,
    # hep-theory fork: "overwrite" (default, original behavior) or "unique".
    # See engineer_response_formatter.py's set_code_history_config() for
    # the full explanation of what each mode does.
    code_history_mode=shared_context_default.get('code_history_mode', 'overwrite'),
):
    """Execute a complex research task with planning and multi-step execution.

    This workflow first creates a detailed plan, then executes each step iteratively
    with full context carryover. It's designed for complex tasks that require
    multiple phases of work.

    Parameters
    ----------
    task : str
        The research task description
    max_rounds_planning : int, optional
        Maximum rounds for planning phase, by default 50
    max_rounds_control : int, optional
        Maximum rounds for each control step, by default 100
    max_plan_steps : int, optional
        Maximum number of steps in the plan, by default 3
    n_plan_reviews : int, optional
        Number of plan review iterations, by default 1
    plan_instructions : str, optional
        Additional instructions for the planner
    engineer_instructions : str, optional
        Additional instructions for the engineer agent
    researcher_instructions : str, optional
        Additional instructions for the researcher agent
    hardware_constraints : str, optional
        Hardware constraints to consider
    max_n_attempts : int, optional
        Maximum number of retry attempts per step, by default 3
    planner_model : str, optional
        Model to use for planner agent
    plan_reviewer_model : str, optional
        Model to use for plan reviewer agent
    engineer_model : str, optional
        Model to use for engineer agent
    researcher_model : str, optional
        Model to use for researcher agent
    idea_maker_model : str, optional
        Model to use for idea maker agent
    idea_hater_model : str, optional
        Model to use for idea hater agent
    camb_context_model : str, optional
        Model to use for CAMB context agent
    default_llm_model : str, optional
        Default LLM model for unspecified agents
    default_formatter_model : str, optional
        Default model for response formatters
    work_dir : str, optional
        Working directory for outputs
    api_keys : dict, optional
        API keys for model providers
    restart_at_step : int, optional
        Step number to restart from (-1 or 0 for no restart), by default -1
    clear_work_dir : bool, optional
        Whether to clear work directory before starting, by default False
    researcher_filename : str, optional
        Filename for researcher output
    custom_executor : CodeExecutor, optional
        Custom code executor for remote execution (e.g., RemoteWebSocketCodeExecutor).
        If provided, code will be executed on the frontend/user's machine instead of locally.

    Returns
    -------
    dict
        Results dictionary containing:
        - chat_history: List of all conversation messages
        - final_context: Final execution context after all steps
        - initialization_time_control: Time spent on initialization
        - execution_time_control: Time spent on execution
    """
    # Import here to avoid circular dependency
    from ..cmbagent import CMBAgent

    # Create work directory if it doesn't exist
    Path(work_dir).expanduser().resolve().mkdir(parents=True, exist_ok=True)
    work_dir = os.path.expanduser(work_dir)

    if clear_work_dir:
        clean_work_dir(work_dir)

    context_dir = Path(work_dir).expanduser().resolve() / "context"
    os.makedirs(context_dir, exist_ok=True)

    print("Created context directory: ", context_dir)

    if api_keys is None:
        api_keys = get_api_keys_from_env()

    ## planning
    if restart_at_step <= 0:

        ## planning
        planning_dir = Path(work_dir).expanduser().resolve() / "planning"
        planning_dir.mkdir(parents=True, exist_ok=True)

        # Update custom executor's work_dir to match planning directory
        # This ensures planning files are synced to the correct path on the frontend
        if custom_executor is not None:
            custom_executor.work_dir = str(planning_dir)

        start_time = time.time()

        planner_config = get_model_config(planner_model, api_keys)
        plan_reviewer_config = get_model_config(plan_reviewer_model, api_keys)

        cmbagent = CMBAgent(
            work_dir=planning_dir,
            default_llm_model=default_llm_model,
            default_formatter_model=default_formatter_model,
            agent_llm_configs={
                'planner': planner_config,
                'plan_reviewer': plan_reviewer_config,
            },
            api_keys=api_keys,
            # hep-theory fork: without this, self.mode defaults to
            # "planning_and_control" (CMBAgent's own __init__ default) - the
            # SAME value a genuine single-call planning_and_control run gets.
            # hand_offs.py's plan_router needs to tell these apart: this
            # instance's planning phase must still hand off to terminator
            # when done (the outer per-step loop below takes over from
            # there), while a real planning_and_control run must hand off to
            # controller instead. See hand_offs.py's plan_router setup.
            mode="deep_research",
        )
        end_time = time.time()
        initialization_time_planning = end_time - start_time

        start_time = time.time()

        cmbagent.solve(
            task,
            max_rounds=max_rounds_planning,
            initial_agent="plan_setter",
            shared_context={
                'feedback_left': n_plan_reviews,
                'max_n_attempts': max_n_attempts,
                'maximum_number_of_steps_in_plan': max_plan_steps,
                'planner_append_instructions': plan_instructions,
                'engineer_append_instructions': engineer_instructions,
                'researcher_append_instructions': researcher_instructions,
                'plan_reviewer_append_instructions': plan_instructions,
                'hardware_constraints': hardware_constraints,
                'researcher_filename': researcher_filename,
                'code_history_mode': code_history_mode,
            }
        )
        end_time = time.time()
        execution_time_planning = end_time - start_time

        # Create a dummy groupchat attribute if it doesn't exist
        if not hasattr(cmbagent, 'groupchat'):
            Dummy = type('Dummy', (object,), {'new_conversable_agents': []})
            cmbagent.groupchat = Dummy()

        # Now call display_cost without triggering the AttributeError
        cmbagent.display_cost()

        # Sync planning cost file to frontend if using remote execution
        if custom_executor is not None and 'cost_report_path' in cmbagent.final_context:
            cost_path = cmbagent.final_context['cost_report_path']
            if os.path.exists(cost_path):
                with open(cost_path, 'r') as f:
                    cost_content = f.read()
                # Use planning_dir as base since executor.work_dir is planning_dir
                rel_cost_path = os.path.relpath(cost_path, planning_dir)
                custom_executor.send_file(rel_cost_path, cost_content)

        planning_output = copy.deepcopy(cmbagent.final_context)

        outfile = save_final_plan(planning_output, planning_dir)
        print(f"\nStructured plan written to {outfile}")
        print(f"\nPlanning took {execution_time_planning:.4f} seconds\n")

        # Sync final plan to frontend if using remote execution
        if custom_executor is not None and os.path.exists(outfile):
            with open(outfile, 'r') as f:
                plan_content = f.read()
            # Use planning_dir as base since executor.work_dir is planning_dir
            rel_plan_path = os.path.relpath(outfile, planning_dir)
            custom_executor.send_file(rel_plan_path, plan_content)

        context_path = os.path.join(context_dir, "context_step_0.pkl")
        with open(context_path, 'wb') as f:
            pickle.dump(cmbagent.final_context, f)

        # Save timing report as JSON
        timing_report = {
            'initialization_time_planning': initialization_time_planning,
            'execution_time_planning': execution_time_planning,
            'total_time': initialization_time_planning + execution_time_planning
        }

        # Add timestamp
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        timing_path = os.path.join(planning_output['work_dir'], f"time/timing_report_planning_{timestamp}.json")
        write_file_with_sync(
            timing_path,
            json.dumps(timing_report, indent=2),
            str(planning_dir),  # Use planning_dir since executor.work_dir is planning_dir
            custom_executor
        )

        print(f"\nTiming report data saved to: {timing_path}\n")

        ## delete empty folders during planning
        database_full_path = os.path.join(planning_output['work_dir'], planning_output['database_path'])
        codebase_full_path = os.path.join(planning_output['work_dir'], planning_output['codebase_path'])
        for folder in [database_full_path, codebase_full_path]:
            if os.path.exists(folder) and not os.listdir(folder):
                os.rmdir(folder)

    ## control
    engineer_config = engineer_model if isinstance(engineer_model, dict) else get_model_config(engineer_model, api_keys)
    researcher_config = get_model_config(researcher_model, api_keys)
    camb_context_config = get_model_config(camb_context_model, api_keys)
    inspirehep_context_config = get_model_config(inspirehep_context_model, api_keys)
    cadabra_context_config = get_model_config(cadabra_context_model, api_keys)
    derivation_checker_config = get_model_config(derivation_checker_model, api_keys)
    idea_maker_config = get_model_config(idea_maker_model, api_keys)
    idea_hater_config = get_model_config(idea_hater_model, api_keys)

    control_dir = Path(work_dir).expanduser().resolve() / "control"
    control_dir.mkdir(parents=True, exist_ok=True)

    # Update custom executor's work_dir to match the actual control directory
    # This ensures files are synced to the correct Denario project path on the frontend
    if custom_executor is not None:
        custom_executor.work_dir = str(control_dir)

    current_context = copy.deepcopy(planning_output) if restart_at_step <= 0 else load_context(os.path.join(context_dir, f"context_step_{restart_at_step-1}.pkl"))
    number_of_steps_in_plan = current_context['number_of_steps_in_plan']

    # hep-theory fork: on a restart_at_step resume, the loaded pickled
    # context could carry a stale code_history_mode from whenever that run
    # was first started (or be missing it entirely, for a pre-existing run
    # from before this setting existed). The explicit parameter to THIS
    # call should always take effect, e.g. resuming in "unique" mode even
    # though the original run started in "overwrite" mode.
    current_context['code_history_mode'] = code_history_mode

    # BUG FIX (hep-theory fork): step_summaries previously always started as
    # an empty list, even when restart_at_step > 0. Since
    # previous_steps_execution_summary is rebuilt every step as
    # "\n\n".join(step_summaries), restarting silently discarded every prior
    # step's content from every subsequent step's context - confirmed via a
    # real run where derivation_checker (step 4, after a restart_at_step=2
    # resume) genuinely never received step 1's cadabra_context output, and
    # correctly reported gaps as "NOT REVIEWABLE" as a result. The already-
    # computed summary text from the resumed step's pickled context is not
    # separable back into a list of individual per-step entries (it was only
    # ever stored pre-joined), so it is seeded here as a single existing
    # entry - later steps' summaries still append normally after it.
    if restart_at_step > 0 and current_context.get('previous_steps_execution_summary'):
        step_summaries = [current_context['previous_steps_execution_summary']]
    else:
        step_summaries = []

    initial_step = 1 if restart_at_step <= 0 else restart_at_step

    def load_plan(plan_path):
        """Load plan from JSON file."""
        plan_path = os.path.expanduser(plan_path)
        with open(plan_path, 'r') as f:
            plan_dict = json.load(f)
        return plan_dict

    for step in range(initial_step, number_of_steps_in_plan + 1):
        clear_work_dir_step = True if step == 1 and restart_at_step <= 0 else False
        starter_agent = "controller" if step == 1 else "control_starter"

        start_time = time.time()
        cmbagent = CMBAgent(
            work_dir=control_dir,
            clear_work_dir=clear_work_dir_step,
            default_llm_model=default_llm_model,
            default_formatter_model=default_formatter_model,
            agent_llm_configs={
                'engineer': engineer_config,
                'researcher': researcher_config,
                'idea_maker': idea_maker_config,
                'idea_hater': idea_hater_config,
                'camb_context': camb_context_config,
                'inspirehep_context': inspirehep_context_config,
                'cadabra_context': cadabra_context_config,
                'derivation_checker': derivation_checker_config,
            },
            mode="deep_research",
            api_keys=api_keys,
            custom_executor=custom_executor,
        )

        end_time = time.time()
        initialization_time_control = end_time - start_time

        # hep-theory fork: explicit per-step plan loading. The plan file is now
        # loaded and applied for EVERY step, not just step 1 - previously,
        # current_sub_task/current_instructions were never set from the plan
        # file for step>1, only inherited stale from the previous step's
        # context, causing every step after the first to show frozen Step-1
        # task text instead of advancing through the actual plan.
        plan_input = load_plan(os.path.join(work_dir, "planning/final_plan.json"))["sub_tasks"]
        this_step_entry = plan_input[step - 1]
        agent_for_step = this_step_entry['sub_task_agent']

        parsed_context = copy.deepcopy(current_context)
        parsed_context["agent_for_sub_task"] = agent_for_step
        parsed_context["current_sub_task"] = this_step_entry.get('sub_task', parsed_context.get('current_sub_task'))
        parsed_context["current_instructions"] = "\n".join(
            f"- {b}" for b in this_step_entry.get('bullet_points', [])
        ) or parsed_context.get('current_instructions')
        parsed_context["current_plan_step_number"] = step
        parsed_context["n_attempts"] = 0  # reset number of failures for each step
        parsed_context["derivation_review_attempts"] = 0  # hep-theory fork: reset derivation_checker review-fix cycle count for each step

        start_time = time.time()

        cmbagent.solve(
            task,
            max_rounds=max_rounds_control,
            initial_agent=starter_agent,
            shared_context=parsed_context,
            step=step
        )

        end_time = time.time()
        execution_time_control = end_time - start_time

        # number of failures:
        number_of_failures = cmbagent.final_context['n_attempts']

        results = {
            'chat_history': cmbagent.chat_result.chat_history,
            'final_context': cmbagent.final_context
        }

        if number_of_failures >= cmbagent.final_context['max_n_attempts']:
            print(f"in deep_research: number of failures: {number_of_failures} >= max_n_attempts: {cmbagent.final_context['max_n_attempts']}. Exiting.")
            break

        # Collect step summaries
        # hep-theory fork: check original unstripped agent name - fixes
        # custom agents (inspirehep_context, cadabra_context) that don't have
        # a _response_formatter companion, so the stripped-name lookup below
        # (built for camb_context's convention) never matched their real
        # output, silently leaving previous_steps_execution_summary empty.
        # hep-theory fork: capture ALL content-bearing agents that spoke this
        # step, not just the single plan-assigned agent - controller can
        # invoke additional agents at its own discretion (e.g. re-checking
        # literature via inspirehep_context mid-step), and their
        # contributions were previously silently dropped if they weren't the
        # one agent matching agent_for_step.
        original_agent_for_step = agent_for_step
        stripped_agent_for_step = agent_for_step.removesuffix("_context").removesuffix("_agent")
        watched_names = {
            "engineer", "researcher", "cadabra_context",
            "inspirehep_context", "derivation_checker",
            original_agent_for_step, stripped_agent_for_step,
            f"{stripped_agent_for_step}_nest",
            f"{stripped_agent_for_step}_response_formatter",
        }
        agent_msgs = {}
        for msg in results['chat_history']:
            name = msg.get('name')
            msg_content = (msg.get('content') or '').strip()
            if name in watched_names and msg_content:
                agent_msgs[name] = msg_content  # overwrite -> last message per agent wins
        if agent_msgs:
            parts = [f"#### {name}\n{c}" for name, c in agent_msgs.items()]
            this_step_execution_summary = "\n\n".join(parts)
            summary = f"### Step {step}\n{this_step_execution_summary.strip()}"
            step_summaries.append(summary)
            cmbagent.final_context['previous_steps_execution_summary'] = "\n\n".join(step_summaries)

        print("previous_steps_execution_summary: \n", cmbagent.final_context['previous_steps_execution_summary'])

        current_context = copy.deepcopy(cmbagent.final_context)

        results['initialization_time_control'] = initialization_time_control
        results['execution_time_control'] = execution_time_control

        # Save timing report as JSON
        timing_report = {
            'initialization_time_control': initialization_time_control,
            'execution_time_control': execution_time_control,
            'total_time': initialization_time_control + execution_time_control
        }

        # Add timestamp
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        timing_path = os.path.join(current_context['work_dir'], f"time/timing_report_step_{step}_{timestamp}.json")
        write_file_with_sync(
            timing_path,
            json.dumps(timing_report, indent=2),
            str(control_dir),  # Use control_dir since executor.work_dir is control_dir
            custom_executor
        )

        print(f"\nTiming report data saved to: {timing_path}\n")

        # Create a dummy groupchat attribute if it doesn't exist
        if not hasattr(cmbagent, 'groupchat'):
            Dummy = type('Dummy', (object,), {'new_conversable_agents': []})
            cmbagent.groupchat = Dummy()

        # Now call display_cost without triggering the AttributeError
        cmbagent.display_cost(name_append=f"step_{step}")

        # Sync cost file to frontend if using remote execution
        if custom_executor is not None and 'cost_report_path' in cmbagent.final_context:
            cost_path = cmbagent.final_context['cost_report_path']
            if os.path.exists(cost_path):
                with open(cost_path, 'r') as f:
                    cost_content = f.read()
                # Use control_dir as base since executor.work_dir is control_dir
                rel_cost_path = os.path.relpath(cost_path, control_dir)
                custom_executor.send_file(rel_cost_path, cost_content)

        ## save the chat history and the final context
        chat_full_path = os.path.join(current_context['work_dir'], "chats")
        chat_output_path = os.path.join(chat_full_path, f"chat_history_step_{step}.json")
        write_file_with_sync(
            chat_output_path,
            json.dumps(results['chat_history'], indent=2),
            str(control_dir),  # Use control_dir since executor.work_dir is control_dir
            custom_executor
        )

        context_path = os.path.join(context_dir, f"context_step_{step}.pkl")
        with open(context_path, 'wb') as f:
            pickle.dump(cmbagent.final_context, f)

    ## delete empty folders after execution
    database_full_path = os.path.join(current_context['work_dir'], current_context['database_path'])
    codebase_full_path = os.path.join(current_context['work_dir'], current_context['codebase_path'])
    for folder in [database_full_path, codebase_full_path]:
        if os.path.exists(folder) and not os.listdir(folder):
            os.rmdir(folder)

    return results
