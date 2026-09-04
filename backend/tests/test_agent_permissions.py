"""Unit tests for the inter-agent permission matrix (backend/src/agents/base.py).

Pure logic, no DB or API involved.
"""
from src.agents.base import PERMISSION_MATRIX, can_request
from src.models.schemas import AgentType


def test_manager_can_request_every_specialist():
    for agent in (AgentType.SALES, AgentType.SUPPORT, AgentType.MARKETING,
                  AgentType.OPERATIONS, AgentType.ANALYTICS):
        assert can_request(AgentType.MANAGER, agent)


def test_analytics_cannot_request_anyone():
    for agent in AgentType:
        assert not can_request(AgentType.ANALYTICS, agent)


def test_sales_can_only_request_operations():
    assert can_request(AgentType.SALES, AgentType.OPERATIONS)
    for agent in (AgentType.MANAGER, AgentType.SUPPORT, AgentType.MARKETING, AgentType.ANALYTICS):
        assert not can_request(AgentType.SALES, agent)


def test_support_can_only_request_manager():
    assert can_request(AgentType.SUPPORT, AgentType.MANAGER)
    for agent in (AgentType.SALES, AgentType.MARKETING, AgentType.OPERATIONS, AgentType.ANALYTICS):
        assert not can_request(AgentType.SUPPORT, agent)


def test_marketing_and_operations_can_only_request_analytics():
    assert can_request(AgentType.MARKETING, AgentType.ANALYTICS)
    assert can_request(AgentType.OPERATIONS, AgentType.ANALYTICS)
    for agent in (AgentType.MANAGER, AgentType.SALES, AgentType.SUPPORT):
        assert not can_request(AgentType.MARKETING, agent)
        assert not can_request(AgentType.OPERATIONS, agent)


def test_every_agent_type_has_a_matrix_entry():
    for agent in AgentType:
        assert agent in PERMISSION_MATRIX


def test_base_agent_can_communicate_with_delegates_to_matrix():
    from src.agents.sales import SalesAgent
    agent = SalesAgent('biz-1')
    assert agent.can_communicate_with(AgentType.OPERATIONS)
    assert not agent.can_communicate_with(AgentType.MARKETING)
