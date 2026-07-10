import os
from cmbagent.base_agent import BaseAgent


class InspirehepContextAgent(BaseAgent):
    """
    Context/retrieval agent for high-energy-theory literature.
    Mirrors the existing camb_context.py pattern: a plain assistant agent
    (not a GPT-Assistants-API RAG agent) whose job is to reason over
    documentation/instructions injected via the .yaml prompt template,
    plus any {inspirehep_context} content fetched at runtime by
    apis/inspirehep_search.py and interpolated into the prompt.
    """

    def __init__(self, llm_config=None, **kwargs):
        agent_id = os.path.splitext(os.path.abspath(__file__))[0]
        super().__init__(llm_config=llm_config, agent_id=agent_id, **kwargs)

    def set_agent(self, **kwargs):
        super().set_assistant_agent(**kwargs)
