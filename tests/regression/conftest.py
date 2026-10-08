"""Fixtures for the Tier 1 regression suite.

Every fixture here hands back a *live* module or object - the patched code
actually installed in this environment. Pre-fix baselines (for the bite
checks) are loaded separately by `_baseline.py` and exercised only by
`bite_check.py`, never by the pytest suite itself, so a missing `ag2`
checkout or `git` binary can never fail `pytest tests/regression -q`.
"""

from __future__ import annotations

import autogen.agentchat.conversable_agent as conversable_agent
import autogen.agentchat.group.group_tool_executor as group_tool_executor
import autogen.oai.anthropic as anthropic
import cmbagent.hand_offs as hand_offs
import pytest


@pytest.fixture
def live_anthropic_module():
    return anthropic


@pytest.fixture
def live_conversable_agent_module():
    return conversable_agent


@pytest.fixture
def live_group_tool_executor_module():
    return group_tool_executor


@pytest.fixture
def live_hand_offs_module():
    return hand_offs
