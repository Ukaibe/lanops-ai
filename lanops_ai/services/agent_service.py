import asyncio
from collections.abc import Callable
from typing import Any, Protocol

from lanops_ai.agent import build_agent
from lanops_ai.config import get_settings


class AgentTimeoutError(RuntimeError):
    """Raised when an agent request exceeds its execution budget."""


class AgentInvoker(Protocol):
    """The part of a compiled agent used by the service."""

    async def ainvoke(
        self, input: dict[str, Any], config: dict[str, Any] | None = None
    ) -> dict[str, Any]: ...


class AgentService:
    """Coordinate application requests with the LAN operations agent."""

    def __init__(
        self,
        agent: AgentInvoker | None = None,
        agent_factory: Callable[[], AgentInvoker] = build_agent,
        timeout_seconds: float | None = None,
    ) -> None:
        self._agent = agent if agent is not None else agent_factory()
        self._timeout_seconds = (
            timeout_seconds
            if timeout_seconds is not None
            else get_settings().agent_timeout_seconds
        )

    async def chat(
        self, message: str, thread_id: str, client_ip: str | None = None
    ) -> str:
        """Send a user message and return the agent's final answer."""
        try:
            async with asyncio.timeout(self._timeout_seconds):
                result = await self._agent.ainvoke(
                    {
                        "messages": [{"role": "user", "content": message}],
                        "client_ip": client_ip,
                    },
                    config={
                        "configurable": {"thread_id": thread_id},
                        "recursion_limit": 12,
                    },
                )
        except TimeoutError as exc:
            raise AgentTimeoutError(
                f"Agent did not respond within {self._timeout_seconds:g} seconds"
            ) from exc
        messages = result.get("messages", [])
        if not messages:
            raise RuntimeError("Agent returned no messages")

        content = getattr(messages[-1], "content", None)
        if content is None:
            raise RuntimeError("Agent returned a message without content")
        return str(content)
