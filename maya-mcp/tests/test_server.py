"""Tests for MCP server configuration and tool dispatch."""

import pytest

from maya_mcp.config import Config, MayaConfig, ProviderConfig


class TestConfig:
    def test_default_config(self):
        config = Config()
        assert config.maya.host == "localhost"
        assert config.maya.port == 7001
        assert config.maya.command_timeout == 30.0
        assert config.provider.default_provider == "rodin"
        assert config.provider.generation_timeout == 300.0

    def test_from_env(self, monkeypatch):
        monkeypatch.setenv("MAYA_HOST", "192.168.1.100")
        monkeypatch.setenv("MAYA_PORT", "8001")
        monkeypatch.setenv("COMMAND_TIMEOUT", "60")
        monkeypatch.setenv("DEFAULT_PROVIDER", "meshy")
        monkeypatch.setenv("RODIN_API_KEY", "test-rodin-key")
        monkeypatch.setenv("MESHY_API_KEY", "test-meshy-key")

        config = Config.from_env()
        assert config.maya.host == "192.168.1.100"
        assert config.maya.port == 8001
        assert config.maya.command_timeout == 60.0
        assert config.provider.default_provider == "meshy"
        assert config.provider.rodin_api_key == "test-rodin-key"
        assert config.provider.meshy_api_key == "test-meshy-key"
        assert config.provider.tripo_api_key == ""

    def test_asset_dir_default(self):
        config = Config()
        assert "maya_mcp_assets" in str(config.provider.asset_dir)
