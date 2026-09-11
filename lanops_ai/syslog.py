import asyncio
from collections import deque
from datetime import UTC, datetime
from pathlib import Path

from lanops_ai.config import get_settings

RECENT_MESSAGES: deque[dict] = deque(maxlen=500)


class SyslogProtocol(asyncio.DatagramProtocol):
    def datagram_received(self, data: bytes, addr: tuple[str, int]) -> None:
        record = {
            "timestamp": datetime.now(UTC).isoformat(),
            "host": addr[0],
            "message": data.decode("utf-8", errors="replace").strip()[:8192],
        }
        RECENT_MESSAGES.append(record)
        path = Path(get_settings().syslog_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(f"{record['timestamp']} {record['host']} {record['message']}\n")


async def start_syslog_server() -> asyncio.DatagramTransport:
    loop = asyncio.get_running_loop()
    transport, _ = await loop.create_datagram_endpoint(
        SyslogProtocol, local_addr=("0.0.0.0", get_settings().syslog_port)
    )
    return transport
