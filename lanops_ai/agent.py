import json
import logging
from typing import Annotated, Any, TypedDict

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_ollama import ChatOllama
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages

from lanops_ai.config import get_settings
from lanops_ai.tools import TOOLS

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a cautious LAN operations assistant. Diagnose before proposing changes.
Use tools for live facts and runbook retrieval; never invent command output. Prefer read-only checks.
Explain the evidence, likely cause, and next safe action. Ask for confirmation before disruptive steps.
Never expose credentials or secrets. Targets are restricted to configured network ranges.

Respond with exactly one JSON object and no markdown. To use a tool:
{{"type":"tool","name":"ping","args":{{"host":"192.168.1.1","count":3}}}}
To answer the user:
{{"type":"answer","answer":"Your concise evidence-based answer"}}

Available tools:
{tools}
"""


class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    action: dict[str, Any] | None
    client_ip: str | None


def _content_text(content: str | list[str | dict[str, Any]]) -> str:
    """Normalize plain and structured model content into text."""
    if isinstance(content, str):
        return content
    return "".join(
        block if isinstance(block, str) else str(block.get("text", ""))
        for block in content
    )


def _parse_action(content: str) -> dict[str, Any]:
    cleaned = content.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    try:
        action = json.loads(cleaned)
    except json.JSONDecodeError:
        return {"type": "answer", "answer": content}
    if not isinstance(action, dict) or action.get("type") not in {"tool", "answer"}:
        return {"type": "answer", "answer": content}
    return action


async def _invoke_with_failover(
    primary: Any | None, failover: Any, messages: list[BaseMessage]
) -> BaseMessage:
    """Use the local Ollama model when Gemini cannot complete a request."""
    if primary is not None:
        try:
            return await primary.ainvoke(messages)
        except Exception as exc:  # noqa: BLE001 - provider errors trigger failover
            logger.warning("Gemini request failed; using Ollama failover: %s", type(exc).__name__)
    return await failover.ainvoke(messages)


def build_agent():
    settings = get_settings()
    primary_model = (
        ChatGoogleGenerativeAI(
            model=settings.chat_model,
            api_key=settings.gemini_api_key.get_secret_value(),
            temperature=0,
            max_tokens=settings.model_max_tokens,
            response_mime_type="application/json",
        )
        if settings.gemini_api_key is not None
        else None
    )
    failover_model = ChatOllama(
        model=settings.ollama_failover_model,
        base_url=settings.ollama_failover_url,
        temperature=0,
        format="json",
        num_predict=settings.model_max_tokens,
        reasoning=False,
    )
    tools = {item.name: item for item in TOOLS}
    descriptions = "\n".join(
        f"- {item.name}: {item.description}; schema={json.dumps(item.args)}" for item in TOOLS
    )

    async def plan(state: AgentState):
        prompt = SYSTEM_PROMPT.format(tools=descriptions)
        if state.get("client_ip"):
            prompt += (
                "\nRequest context: the trusted reverse proxy observed the requesting "
                f"workstation IP as {state['client_ip']}. When asked for this workstation's "
                "or this client's IP address, use this value.\n"
            )
        response = await _invoke_with_failover(
            primary_model,
            failover_model,
            [SystemMessage(content=prompt), *state["messages"]],
        )
        response_text = _content_text(response.content)
        action = _parse_action(response_text)
        if action["type"] == "answer":
            response = AIMessage(content=str(action.get("answer", response_text)))
        return {"messages": [response], "action": action}

    async def execute_tool(state: AgentState):
        action = state["action"] or {}
        name = str(action.get("name", ""))
        selected = tools.get(name)
        if selected is None:
            observation = f"Tool error: unknown tool {name!r}"
        else:
            try:
                observation = await selected.ainvoke(action.get("args", {}))
            except Exception as exc:  # noqa: BLE001 - tool failures become observations
                observation = f"Tool error: {exc}"
        return {
            "messages": [
                HumanMessage(content=f"Tool observation from {name}:\n{observation}\nNow continue.")
            ],
            "action": None,
        }

    def route(state: AgentState):
        return "tools" if (state.get("action") or {}).get("type") == "tool" else END

    builder = StateGraph(AgentState)
    builder.add_node("agent", plan)
    builder.add_node("tools", execute_tool)
    builder.add_edge(START, "agent")
    builder.add_conditional_edges("agent", route, {"tools": "tools", END: END})
    builder.add_edge("tools", "agent")
    return builder.compile()
