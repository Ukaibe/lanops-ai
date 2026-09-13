import asyncio
from types import SimpleNamespace
from typing import Any

import pytest

from lanops_ai.services import AgentService, AgentTimeoutError


class _Agent:
    def __init__(self, result: dict[str, Any]) -> None:
        self.result = result
        self.input: dict[str, Any] | None = None
        self.config: dict[str, Any] | None = None

    async def ainvoke(
        self, input: dict[str, Any], config: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        self.input = input
        self.config = config
        return self.result


async def test_chat_invokes_agent_with_thread_context():
    agent = _Agent({"messages": [SimpleNamespace(content="Switch is reachable")]})
    service = AgentService(agent=agent)

    answer = await service.chat(
        "Check the core switch", "thread-123", client_ip="192.168.1.50"
    )

    assert answer == "Switch is reachable"
    assert agent.input == {
        "messages": [{"role": "user", "content": "Check the core switch"}],
        "client_ip": "192.168.1.50",
    }
    assert agent.config == {
        "configurable": {"thread_id": "thread-123"},
        "recursion_limit": 12,
    }


async def test_chat_rejects_an_empty_agent_result():
    service = AgentService(agent=_Agent({"messages": []}))

    with pytest.raises(RuntimeError, match="Agent returned no messages"):
        await service.chat("Check the core switch", "thread-123")


async def test_chat_times_out_a_slow_agent():
    class _SlowAgent(_Agent):
        async def ainvoke(
            self, input: dict[str, Any], config: dict[str, Any] | None = None
        ) -> dict[str, Any]:
            await asyncio.sleep(1)
            return self.result

    service = AgentService(agent=_SlowAgent({"messages": []}), timeout_seconds=0.01)

    with pytest.raises(AgentTimeoutError, match="0.01 seconds"):
        await service.chat("Check the core switch", "thread-123")
