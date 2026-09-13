from pathlib import Path

import httpx
from fastapi import FastAPI, Request, Response
from fastapi.staticfiles import StaticFiles

API_URL = "http://127.0.0.1:8001"
WEB_ROOT = Path(__file__).resolve().parent.parent / "web"

app = FastAPI(title="LAN Ops AI Host Gateway", docs_url=None, redoc_url=None)


@app.api_route(
    "/api/{path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
)
async def proxy_api(path: str, request: Request) -> Response:
    """Proxy API traffic while preserving the LAN client's TCP source address."""
    client_ip = request.client.host if request.client else ""
    headers = {
        "content-type": request.headers.get("content-type", "application/octet-stream"),
        "host": request.headers.get("host", ""),
        "x-forwarded-for": client_ip,
    }
    async with httpx.AsyncClient(timeout=130) as client:
        upstream = await client.request(
            request.method,
            f"{API_URL}/api/{path}",
            params=request.query_params,
            content=await request.body(),
            headers=headers,
        )
    return Response(
        content=upstream.content,
        status_code=upstream.status_code,
        media_type=upstream.headers.get("content-type"),
    )


app.mount("/", StaticFiles(directory=WEB_ROOT, html=True), name="web")
