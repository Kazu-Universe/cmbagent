"""Main registration function for CMBAgent functions."""

from autogen import register_function

from .execution_control import create_post_execution_transfer, create_terminate_session
from .planning import create_record_plan_constraints
# Note: idea_saver is now a non-LLM agent (see idea_saver.py)
from .keywords import create_record_aas_keywords
from .status import create_record_status, create_record_status_starter
# hep-theory fork: live INSPIRE-HEP literature search tool
from ..apis.inspirehep_search import search_inspire


def register_functions_to_agents(cmbagent_instance):
    """
    This function registers the functions to the agents.
    """
    # Get all agent references
    planner = cmbagent_instance.get_agent_from_name('planner')
    planner_response_formatter = cmbagent_instance.get_agent_from_name('planner_response_formatter')
    plan_reviewer = cmbagent_instance.get_agent_from_name('plan_reviewer')
    reviewer_response_formatter = cmbagent_instance.get_agent_from_name('reviewer_response_formatter')
    researcher = cmbagent_instance.get_agent_from_name('researcher')
    researcher_response_formatter = cmbagent_instance.get_agent_from_name('researcher_response_formatter')
    engineer = cmbagent_instance.get_agent_from_name('engineer')
    engineer_response_formatter = cmbagent_instance.get_agent_from_name('engineer_response_formatter')
    executor = cmbagent_instance.get_agent_from_name('executor')
    executor_response_formatter = cmbagent_instance.get_agent_from_name('executor_response_formatter')
    terminator = cmbagent_instance.get_agent_from_name('terminator')
    controller = cmbagent_instance.get_agent_from_name('controller')
    admin = cmbagent_instance.get_agent_from_name('admin')
    aas_keyword_finder = cmbagent_instance.get_agent_from_name('aas_keyword_finder')
    plan_setter = cmbagent_instance.get_agent_from_name('plan_setter')
    idea_maker = cmbagent_instance.get_agent_from_name('idea_maker')
    installer = cmbagent_instance.get_agent_from_name('installer')
    control_starter = cmbagent_instance.get_agent_from_name('control_starter')
    camb_context = cmbagent_instance.get_agent_from_name('camb_context')
    # hep-theory fork
    inspirehep_context = cmbagent_instance.get_agent_from_name('inspirehep_context')

    # hep-theory fork: give inspirehep_context a live INSPIRE-HEP search
    # tool - previously it ran on pure LLM recall (the apis/ module its own
    # docstring referenced was never built), which is why every real run's
    # literature verdicts carried a "recall-based, no live retrieval tool
    # available" caveat. caller=executor=<same agent> mirrors how
    # aas_keyword_finder's tool is registered below.
    register_function(
        search_inspire,
        caller=inspirehep_context,
        executor=inspirehep_context,
        description=r"""
        Run one live INSPIRE-HEP literature search against the real
        https://inspirehep.net/api/literature endpoint and return formatted
        results (title, authors, arXiv ID, DOI, journal, date, citation
        count, truncated abstract snippet per record).

        Args:
            query (str): INSPIRE search query. Free text works; so does
                INSPIRE's structured syntax, e.g.
                't "entanglement entropy" and date > 2020' or
                'a Solodukhin and t entanglement' or 'arxiv:1104.3712'.
            max_results (int): number of records to return (1-25, default 10).
            sort (str): 'mostrecent' | 'mostcited' | 'bestmatch'
                (default 'mostrecent').

        Returns:
            str: formatted results, or a string starting with
            "INSPIRE TOOL ERROR" if the live query failed - in which case
            any literature statements must be explicitly disclosed as
            recall-based, not live-verified. An empty result set is reported
            as a genuine live-verified absence, distinct from a tool error.
        """,
    )

    # Create and register execution control functions
    post_execution_transfer = create_post_execution_transfer(
        controller, engineer, camb_context, installer, terminator
    )

    register_function(
        post_execution_transfer,
        caller=executor_response_formatter,
        executor=executor_response_formatter,
        description=r"""
Transfer to the next agent based on the execution status.
For the next agent suggestion, follow these rules:

    - Suggest the installer agent if error related to missing Python modules (i.e., ModuleNotFoundError).
    - Suggest the camb_context agent if CAMB documentation should be consulted, e.g., if the Python error is related to the camb code.
    - Suggest camb_context to fix Python errors related to the camb code.
    - Suggest the engineer agent if error related to generic Python code. Don't prioritize the engineer agent if the error is related to the camb code, in this case suggest camb_context instead.
    - Suggest the controller only if execution was successful.
""",
    )

    terminate_session = create_terminate_session()
    terminator._add_single_function(terminate_session)

    # Create and register planning functions
    record_plan_constraints = create_record_plan_constraints(cmbagent_instance, planner)
    plan_setter._add_single_function(record_plan_constraints)

    # Note: review_recorder is now a non-LLM agent (see review_recorder.py)
    # Note: idea_saver is now a non-LLM agent (see idea_saver.py)

    # Create and register recording functions
    record_aas_keywords = create_record_aas_keywords(aas_keyword_finder, controller)

    register_function(
        record_aas_keywords,
        caller=aas_keyword_finder,
        executor=aas_keyword_finder,
        description=r"""
        Extracts the relevant AAS keywords from the list, given the text input.
        Args:
            aas_keywords (list[str]): The list of AAS keywords to be recorded
            context_variables (dict): A dictionary maintaining execution context, including previous plans,
                feedback tracking, and finalized plans.
        """,
    )

    # Create and register status tracking functions
    record_status = create_record_status(cmbagent_instance, controller)

    register_function(
        record_status,
        caller=controller,
        executor=controller,
        description=r"""
        Updates the context and returns the current progress.
        Must be called **before calling the agent in charge of the next sub-task**.
        Must be called **after** each action taken.

        Args:
            current_status (str): The current status ("in progress", "failed", or "completed").
            current_plan_step_number (int): The current step number in the plan.
            current_sub_task (str): Description of the current sub-task.
            current_instructions (str): Instructions for the sub-task.
            agent_for_sub_task (str): The agent responsible for the sub-task.
            context_variables (dict): context dictionary.

        Returns:
            ReplyResult: Contains a formatted status message and updated context.
        """,
    )

    record_status_starter = create_record_status_starter(cmbagent_instance)

    register_function(
        record_status_starter,
        caller=control_starter,
        executor=control_starter,
        description=r"""
        Updates the context and returns the current progress.
        Must be called **before calling the agent in charge of the next sub-task**.
        Must be called **after** each action taken.

        Args:

            context_variables (dict): context dictionary.

        Returns:
            ReplyResult: Contains a formatted status message and updated context.
        """,
    )
