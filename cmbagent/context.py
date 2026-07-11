"""Shared context for CMBAgent multi-agent system.

This dictionary stores state shared across all agents during task execution.
It's initialized with defaults and updated during the conversation flow.
"""

shared_context = {
    # =========================================================================
    # Task Information
    # =========================================================================
    "main_task": None,
    "improved_main_task": None,

    # =========================================================================
    # Planning Phase
    # =========================================================================
    "plans": [],
    "reviews": [],
    "proposed_plan": None,
    "recommendations": None,
    "feedback_left": 1,
    "final_plan": None,
    "number_of_steps_in_plan": None,
    "maximum_number_of_steps_in_plan": 5,

    # =========================================================================
    # Execution Control (Control Phase)
    # =========================================================================
    "current_plan_step_number": None,
    "current_sub_task": None,
    "agent_for_sub_task": None,
    "current_status": None,  # Controller's view of step status: "in progress", "completed", "failed"
    "current_instructions": None,
    "previous_steps_execution_summary": "\n",

    # Step vs Code execution status distinction:
    # - code_execution_status: Result of running code/commands ("success"/"failure")
    # - step_execution_status: Whether the plan step goal is achieved (only controller sets "completed")
    "step_execution_status": "pending",  # "pending", "in_progress", "completed"
    "code_execution_status": None,  # "success", "failure" - set by executor

    # =========================================================================
    # Agent Handoff Flags
    # =========================================================================
    "transfer_to_engineer": False,
    "transfer_to_researcher": False,
    "transfer_to_camb_context": False,

    # =========================================================================
    # File Paths
    # =========================================================================
    "database_path": "data/",
    "codebase_path": "codebase/",

    # =========================================================================
    # Codebase Tracking
    # =========================================================================
    "current_codebase": None,
    "displayed_images": [],

    # =========================================================================
    # Agent-Specific Instructions
    # =========================================================================
    "planner_append_instructions": None,
    "plan_reviewer_append_instructions": None,
    "engineer_append_instructions": None,
    "researcher_append_instructions": None,

    # =========================================================================
    # Retry Control
    # =========================================================================
    "n_attempts": 0,  # Number of failed code execution attempts
    "max_n_attempts": 3,

    # hep-theory fork: hard-enforced cap on derivation_checker review-fix
    # cycles, separate from n_attempts (which only tracks code-execution
    # failures). Incremented whenever a step whose agent is derivation_checker
    # is recorded as "failed"; reset to 0 whenever a step is recorded as
    # "completed". Enforced in status.py's routing logic, not just in the
    # controller's prompt, so a runaway auto-retry loop is not possible even
    # if the controller LLM misjudges when to stop.
    "derivation_review_attempts": 0,
    "max_derivation_review_attempts": 3,  # initial review + 2 fix-and-recheck cycles

    # =========================================================================
    # Domain-Specific: AAS Keywords (Astronomy)
    # =========================================================================
    "AAS_keywords_string": None,
    "text_input_for_AAS_keyword_finder": None,
    "N_AAS_keywords": 5,

    # =========================================================================
    # Domain-Specific: CAMB Context (Cosmology)
    # =========================================================================
    "camb_context": None,

    # =========================================================================
    # Other Settings
    # =========================================================================
    "hardware_constraints": None,
    "researcher_filename": "provide a suitable filename given the nature of the notes. Prefer markdown extension unless otherwise instructed.",
}
