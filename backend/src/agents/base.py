from abc import ABC, abstractmethod
from typing import Any, Optional
from datetime import datetime

from ..models.schemas import (
    AgentType,
    AgentMessage,
    AgentResponse,
    AgentLog,
)
from ..services.firestore import agent_log_service, business_service
from ..services.gemini import gemini_service
from ..core.currency import currency_symbol

# Distinguishes "not looked up yet" from "looked up, and there is no owner".
_UNRESOLVED = object()


# === Permission System ===

PERMISSION_MATRIX: dict[AgentType, dict[str, list[AgentType]]] = {
    AgentType.MANAGER: {
        "can_request": [
            AgentType.SALES,
            AgentType.SUPPORT,
            AgentType.MARKETING,
            AgentType.OPERATIONS,
            AgentType.ANALYTICS,
        ],
        "can_access": [
            AgentType.SALES,
            AgentType.SUPPORT,
            AgentType.MARKETING,
            AgentType.OPERATIONS,
            AgentType.ANALYTICS,
        ],
    },
    AgentType.SALES: {
        "can_request": [AgentType.OPERATIONS],
        "can_access": [AgentType.OPERATIONS],
    },
    AgentType.SUPPORT: {
        "can_request": [AgentType.MANAGER],
        "can_access": [AgentType.MANAGER],
    },
    AgentType.MARKETING: {
        "can_request": [AgentType.ANALYTICS],
        "can_access": [AgentType.ANALYTICS],
    },
    AgentType.OPERATIONS: {
        "can_request": [AgentType.ANALYTICS],
        "can_access": [AgentType.ANALYTICS],
    },
    AgentType.ANALYTICS: {
        "can_request": [],
        "can_access": [],
    },
}


def can_request(requester: AgentType, target: AgentType) -> bool:
    """Check if requester agent can request action from target agent."""
    permissions = PERMISSION_MATRIX.get(requester, {})
    return target in permissions.get("can_request", [])


# === Agent Memory ===

class AgentMemory:
    """Stores agent-specific context and history."""

    def __init__(self, agent_type: AgentType, business_id: str):
        self.agent_type = agent_type
        self.business_id = business_id
        self.short_term: list[dict[str, Any]] = []
        self.preferences: dict[str, Any] = {}

    def add_context(self, context: dict[str, Any]):
        """Add to short-term conversation memory."""
        self.short_term.append(context)
        if len(self.short_term) > 20:
            self.short_term = self.short_term[-20:]

    def get_context(self) -> list[dict[str, Any]]:
        """Get current short-term memory."""
        return self.short_term

    def set_preference(self, key: str, value: Any):
        """Store a learned preference."""
        self.preferences[key] = value


# === Base Agent ===

class BaseAgent(ABC):
    """Base class for all METIS agents."""

    def __init__(self, agent_type: AgentType, business_id: str):
        self.agent_type = agent_type
        self.business_id = business_id
        self.memory = AgentMemory(agent_type, business_id)
        self.gemini = gemini_service
        self._tools: dict[str, callable] = {}
        self._owner_uid: Any = _UNRESOLVED

    @property
    @abstractmethod
    def system_prompt(self) -> str:
        """System prompt defining agent behavior."""
        ...

    @property
    @abstractmethod
    def agent_name(self) -> str:
        """Human-readable agent name."""
        ...

    def get_currency_symbol(self) -> str:
        """This business's chosen currency symbol, for prompts and summaries."""
        business = business_service.get(self.business_id) or {}
        return currency_symbol(business.get('currency', ''))

    @property
    def owner_uid(self) -> Optional[str]:
        """Whose Gemini key this agent spends.

        An agent acts on behalf of a business, so the key that pays for its
        thinking is the business owner's -- including on the public storefront,
        where the shopper driving the conversation has no account and no key of
        their own. Cached because every think() would otherwise re-read the
        business document.

        Empty for a business created before ownership existed, which resolves
        to the same global key that install has always used.
        """
        if self._owner_uid is _UNRESOLVED:
            business = business_service.get(self.business_id) or {}
            self._owner_uid = business.get('owner_uid') or None
        return self._owner_uid

    def register_tool(self, name: str, func: callable):
        """Register a tool the agent can use."""
        self._tools[name] = func

    def execute_tool(self, name: str, **kwargs) -> Any:
        """Execute a registered tool."""
        if name in self._tools:
            return self._tools[name](**kwargs)
        return {"error": f"Tool '{name}' not found."}

    def log_action(
        self,
        action: str,
        details: dict[str, Any],
        status: str = "completed",
        result: str = "",
    ) -> str:
        """Log agent action to Firestore."""
        log = AgentLog(
            business_id=self.business_id,
            agent_type=self.agent_type,
            action=action,
            details=details,
            status=status,
            result=result,
        )
        return agent_log_service.create(log.model_dump())

    def think(self, prompt: str, temperature: float = 0.7, history: Optional[list[dict[str, Any]]] = None) -> str:
        """Generate a response using Gemini, optionally with conversation history."""
        return self.gemini.generate(
            prompt,
            system_instruction=self.system_prompt,
            temperature=temperature,
            history=history,
            owner_uid=self.owner_uid,
        )

    def think_structured(self, prompt: str) -> str:
        """Generate structured output using Gemini."""
        return self.gemini.generate_structured(
            prompt,
            system_instruction=self.system_prompt,
            owner_uid=self.owner_uid,
        )

    @abstractmethod
    async def handle_message(self, message: AgentMessage) -> AgentResponse:
        """Handle an incoming message from another agent."""
        ...

    def can_communicate_with(self, target: AgentType) -> bool:
        """Check if this agent can communicate with target agent."""
        return can_request(self.agent_type, target)
