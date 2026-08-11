from typing import Dict, Optional
from .base import BaseAgent
from ..models.schemas import AgentType
from .manager import ManagerAgent
from .sales import SalesAgent
from .support import SupportAgent
from .marketing import MarketingAgent
from .operations import OperationsAgent
from .analytics import AnalyticsAgent

_agent_registry: Dict[str, BaseAgent] = {}


def get_agent(agent_type: AgentType, business_id: str) -> BaseAgent:
    '''Get or create an agent instance.'''
    key = f'{business_id}_{agent_type.value}'
    if key not in _agent_registry:
        if agent_type == AgentType.MANAGER:
            _agent_registry[key] = ManagerAgent(business_id)
        elif agent_type == AgentType.SALES:
            _agent_registry[key] = SalesAgent(business_id)
        elif agent_type == AgentType.SUPPORT:
            _agent_registry[key] = SupportAgent(business_id)
        elif agent_type == AgentType.MARKETING:
            _agent_registry[key] = MarketingAgent(business_id)
        elif agent_type == AgentType.OPERATIONS:
            _agent_registry[key] = OperationsAgent(business_id)
        elif agent_type == AgentType.ANALYTICS:
            _agent_registry[key] = AnalyticsAgent(business_id)
    return _agent_registry[key]


def clear_registry():
    '''Clear agent registry (useful for testing).'''
    _agent_registry.clear()
