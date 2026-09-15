from functools import lru_cache

from pydantic import AliasChoices, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="LANOPS_", extra="ignore")

    ollama_url: str = "http://ollama:11434"
    chat_model: str = "gemini-3.5-flash-lite"
    gemini_api_key: SecretStr | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "LANOPS_GEMINI_API_KEY", "GEMINI_API_KEY", "GEMINI_KEY"
        )
    )
    agent_timeout_seconds: float = 120.0
    mcp_url: str = "http://127.0.0.1:8000/mcp/"
    model_max_tokens: int = 128
    ollama_failover_url: str = "http://127.0.0.1:11434"
    ollama_failover_model: str = "qwen3.5:9b"
    host_ipv4_address: str | None = None
    embedding_model: str = "nomic-embed-text"
    allowed_networks: str = "127.0.0.0/8,10.0.0.0/8,172.16.0.0/12,192.168.0.0/16"
    enable_remote_commands: bool = False
    ssh_username: str | None = None
    ssh_password: str | None = None
    ssh_key_file: str | None = None
    winrm_username: str | None = None
    winrm_password: str | None = None
    winrm_transport: str = "ntlm"
    snmp_community: str = "public"
    rag_path: str = "/data/rag.json"
    syslog_path: str = "/data/syslog.log"
    syslog_port: int = 1514


@lru_cache
def get_settings() -> Settings:
    return Settings()
