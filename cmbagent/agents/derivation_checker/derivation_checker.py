import os
from cmbagent.base_agent import BaseAgent


class DerivationCheckerAgent(BaseAgent):
    """
    Critique agent for symbolic/analytic derivations, playing the role idea_hater /
    plot_judge play elsewhere in cmbagent: it doesn't produce the derivation, it
    tries to break it. This is the closest substitute available for a numerical
    chi-squared check when the task is analytic rather than data-fitting.
    """

    def __init__(self, llm_config=None, **kwargs):
        agent_id = os.path.splitext(os.path.abspath(__file__))[0]
        super().__init__(llm_config=llm_config, agent_id=agent_id, **kwargs)

    def set_agent(self, **kwargs):
        super().set_assistant_agent(**kwargs)
