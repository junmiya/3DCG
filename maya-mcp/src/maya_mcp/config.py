"""Configuration management for Maya MCP Server."""

import os
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class MayaConfig:
    """Maya connection settings."""

    host: str = "localhost"
    port: int = 7001
    command_timeout: float = 30.0


@dataclass
class ProviderConfig:
    """3D generation provider settings."""

    default_provider: str = "rodin"
    generation_timeout: float = 300.0
    asset_dir: Path = field(default_factory=lambda: Path.home() / "maya_mcp_assets")
    rodin_api_key: str = ""
    meshy_api_key: str = ""
    tripo_api_key: str = ""


@dataclass
class Config:
    """Root configuration."""

    maya: MayaConfig = field(default_factory=MayaConfig)
    provider: ProviderConfig = field(default_factory=ProviderConfig)

    @classmethod
    def from_env(cls) -> "Config":
        """Load configuration from environment variables."""
        maya = MayaConfig(
            host=os.getenv("MAYA_HOST", "localhost"),
            port=int(os.getenv("MAYA_PORT", "7001")),
            command_timeout=float(os.getenv("COMMAND_TIMEOUT", "30")),
        )
        provider = ProviderConfig(
            default_provider=os.getenv("DEFAULT_PROVIDER", "rodin"),
            generation_timeout=float(os.getenv("GENERATION_TIMEOUT", "300")),
            asset_dir=Path(os.getenv("ASSET_DIR", str(Path.home() / "maya_mcp_assets"))),
            rodin_api_key=os.getenv("RODIN_API_KEY", ""),
            meshy_api_key=os.getenv("MESHY_API_KEY", ""),
            tripo_api_key=os.getenv("TRIPO_API_KEY", ""),
        )
        return cls(maya=maya, provider=provider)
