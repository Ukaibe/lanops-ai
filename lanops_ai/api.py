from contextlib import asynccontextmanager
from typing import Any
from uuid import uuid4

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from lanops_ai.agent import build_agent
from lanops_ai.config import get_settings
from lanops_ai.rag import knowledge_base
from lanops_ai.syslog import RECENT_MESSAGES, start_syslog_server


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.agent = build_agent()
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


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=8000)
    thread_id: str = Field(default_factory=lambda: str(uuid4()), max_length=100)


class DocumentRequest(BaseModel):
    text: str = Field(min_length=1, max_length=200_000)
    source: str = Field(default="manual", max_length=500)


@app.get("/api/health")
async def health() -> dict[str, Any]:
    settings = get_settings()
    ollama = False
    try:
        async with httpx.AsyncClient(timeout=2) as client:
            ollama = (await client.get(f"{settings.ollama_url}/api/tags")).is_success
    except httpx.HTTPError:
        pass
    return {
        "status": "ok",
        "ollama": ollama,
        "model": settings.chat_model,
        "syslog_buffer": len(RECENT_MESSAGES),
    }


@app.post("/api/chat")
async def chat(request: ChatRequest) -> dict[str, str]:
    try:
        result = await app.state.agent.ainvoke(
            {"messages": [{"role": "user", "content": request.message}]},
            config={"configurable": {"thread_id": request.thread_id}, "recursion_limit": 12},
        )
        return {
            "thread_id": request.thread_id,
            "answer": str(result["messages"][-1].content),
        }
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Agent unavailable: {exc}") from exc


@app.post("/api/knowledge")
async def add_knowledge(request: DocumentRequest) -> dict[str, int]:
    try:
        return {"chunks": knowledge_base.add(request.text, request.source)}
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Embedding service unavailable: {exc}") from exc
