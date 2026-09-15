# LAN Ops AI

A network operations assistant built with FastAPI, LangGraph, Gemini, Ollama embeddings, Nginx, and Docker Compose. It can perform allowlisted ping, DNS, SNMP, SSH, WinRM/PowerShell, syslog, and runbook retrieval operations.

Gemini is the primary chat provider. If it is unavailable, the agent automatically falls back to the local Ollama model configured by `LANOPS_OLLAMA_FAILOVER_MODEL`.

## Run

1. Copy `.env.example` to `.env`, set `GEMINI_API_KEY`, and adjust the allowed networks and credentials.
2. Run `docker compose up --build` (the first start downloads the embedding model).
3. On Windows Docker Desktop, start the host gateway with `uv run uvicorn lanops_ai.host_gateway:app --host 0.0.0.0 --port 8080`.
4. Open `http://localhost:8080`; API documentation is at `http://localhost:8080/api/docs`.

LAN browsers should use `http://<server-lan-ip>:8080`; the host listener preserves each client's real LAN source address before proxying to the loopback-only Docker API port.

Send network devices to the syslog listener on UDP port `1514`. Index a runbook with:

```bash
curl -X POST http://localhost:8080/api/knowledge \
  -H "Content-Type: application/json" \
  -d '{"source":"core-switch","text":"Your runbook text"}'
```

Remote command tools are off by default. Enable them only on a trusted management network. SSH requires known host keys and rejects unknown hosts. Production deployments should add authentication/TLS, use Docker secrets, replace SNMP v2c with SNMPv3, and restrict ingress to the management VLAN.

## MCP tools

The agent discovers and invokes its network tools through the MCP Streamable HTTP
endpoint at `http://127.0.0.1:8000/mcp/`. When running Compose, the loopback-only
published API port is `8001`, so a host-side MCP client can use
`http://127.0.0.1:8001/mcp/`. The endpoint exposes `ping`, `dns_lookup`, `snmp_get`,
`ssh_command`, `powershell_winrm`, `search_runbooks`, and `recent_syslog`.

Set `LANOPS_MCP_URL` if the agent should connect to a separately deployed MCP
server. Keep that server on the trusted management network: the MCP tool handlers
apply the same target allowlist and remote-command feature flag as the chat API.

## Development

Use Python 3.14+: `uv sync --extra dev`, `uv run pytest`, and `uv run ruff check .`.
