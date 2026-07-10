import os
from cmbagent.base_agent import BaseAgent


class CadabraContextAgent(BaseAgent):
    """
    Context agent for symbolic tensor/index algebra (Cadabra2, SymPy tensor modules,
    EinsteinPy). Plays the same role camb_context plays for numerical cosmology:
    it doesn't write the final code itself, it surfaces the correct methods,
    conventions, and index-notation gotchas so the engineer agent uses them correctly.
    """

    def __init__(self, llm_config=None, **kwargs):
        agent_id = os.path.splitext(os.path.abspath(__file__))[0]
        super().__init__(llm_config=llm_config, agent_id=agent_id, **kwargs)

    def set_agent(self, **kwargs):
        super().set_assistant_agent(**kwargs)
