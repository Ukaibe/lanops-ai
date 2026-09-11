# LAN Ops AI

A local-first network operations assistant built with FastAPI, LangGraph, Ollama/Gemma, Nginx, and Docker Compose. It can perform allowlisted ping, DNS, SNMP, SSH, WinRM/PowerShell, syslog, and runbook retrieval operations.

## Run

1. Copy `.env.example` to `.env` and adjust the allowed networks and credentials.
2. Run `docker compose up --build` (the first start downloads Gemma and the embedding model).
3. Open `http://localhost:8080`; API documentation is at `http://localhost:8080/api/docs`.

Send network devices to the syslog listener on UDP port `1514`. Index a runbook with:

```bash
curl -X POST http://localhost:8080/api/knowledge \
  -H "Content-Type: application/json" \
  -d '{"source":"core-switch","text":"Your runbook text"}'
```

Remote command tools are off by default. Enable them only on a trusted management network. SSH requires known host keys and rejects unknown hosts. Production deployments should add authentication/TLS, use Docker secrets, replace SNMP v2c with SNMPv3, and restrict ingress to the management VLAN.

## Development

Use Python 3.12+: `uv sync --extra dev`, `uv run pytest`, and `uv run ruff check .`.
