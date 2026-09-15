from contextlib import asynccontextmanager
from ipaddress import IPv4Address, ip_address, ip_network
from typing import Any
from uuid import uuid4

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from lanops_ai.config import get_settings
from lanops_ai.mcp_server import mcp, mcp_app
from lanops_ai.rag import knowledge_base
from lanops_ai.services import AgentService, AgentTimeoutError
from lanops_ai.syslog import RECENT_MESSAGES, start_syslog_server


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with mcp.session_manager.run():
        app.state.agent_service = AgentService()
        app.state.syslog_transport = await start_syslog_server()
        yield
        app.state.syslog_transport.close()


app = FastAPI(
    title="LAN Ops AI",
    version="0.1.0",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[],
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)
app.mount("/mcp", mcp_app, name="mcp")


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=8000)
    thread_id: str = Field(default_factory=lambda: str(uuid4()), max_length=100)


class DocumentRequest(BaseModel):
    text: str = Field(min_length=1, max_length=200_000)
    source: str = Field(default="manual", max_length=500)


def _request_client_ip(request: Request) -> str | None:
    """Return the proxy-observed client IP, with a local-server fallback."""
    settings = get_settings()
    if request.url.hostname in {"localhost", "127.0.0.1", "::1"}:
        return settings.host_ipv4_address

    candidate = request.headers.get("x-forwarded-for")
    if candidate:
        candidate = candidate.split(",")[-1].strip()
    elif request.client:
        candidate = request.client.host
    if not candidate:
        return None
    try:
        parsed_candidate = ip_address(candidate)
    except ValueError:
        return None

    # With Docker Desktop port forwarding, Nginx can see the Docker bridge
    # gateway (for example 172.18.0.1) instead of the Windows host. Only apply
    # the configured host fallback when both proxy hops are Docker-private
    # addresses, preserving genuine LAN client addresses forwarded by Nginx.
    docker_private_network = ip_network("172.16.0.0/12")
    direct_client = request.client.host if request.client else ""
    try:
        parsed_direct_client = ip_address(direct_client)
    except ValueError:
        parsed_direct_client = None
    if (
        settings.host_ipv4_address
        and isinstance(parsed_candidate, IPv4Address)
        and parsed_candidate in docker_private_network
        and isinstance(parsed_direct_client, IPv4Address)
        and parsed_direct_client in docker_private_network
    ):
        return settings.host_ipv4_address
    return str(parsed_candidate)


@app.get("/api/health")
async def health() -> dict[str, Any]:
    settings = get_settings()
    ollama = False
    ollama_failover = False
    try:
        async with httpx.AsyncClient(timeout=2) as client:
            ollama = (await client.get(f"{settings.ollama_url}/api/tags")).is_success
            ollama_failover = (
                await client.get(f"{settings.ollama_failover_url}/api/tags")
            ).is_success
    except httpx.HTTPError:
        pass
    return {
        "status": "ok",
        "ollama": ollama,
        "ollama_failover": ollama_failover,
        "ollama_failover_model": settings.ollama_failover_model,
        "gemini_configured": settings.gemini_api_key is not None,
        "model": settings.chat_model,
        "syslog_buffer": len(RECENT_MESSAGES),
    }


@app.get("/api/client-ip")
async def client_ip(request: Request) -> dict[str, str | None]:
    """Report the browser system address observed by the host gateway."""
    return {"client_ip": _request_client_ip(request)}


@app.post("/api/chat")
async def chat(payload: ChatRequest, request: Request) -> dict[str, str]:
    try:
        answer = await app.state.agent_service.chat(
            payload.message,
            payload.thread_id,
            client_ip=_request_client_ip(request),
        )
        return {
            "thread_id": payload.thread_id,
            "answer": answer,
        }
    except AgentTimeoutError as exc:
        raise HTTPException(status_code=504, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Agent unavailable: {exc}") from exc


@app.post("/api/knowledge")
async def add_knowledge(request: DocumentRequest) -> dict[str, int]:
    try:
        return {"chunks": knowledge_base.add(request.text, request.source)}
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Embedding service unavailable: {exc}") from exc
