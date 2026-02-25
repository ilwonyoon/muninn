"""Tests for server CLI parsing and MCP instance creation."""

from __future__ import annotations

import pytest

from muninn.server import _build_parser, _create_mcp


# ---------------------------------------------------------------------------
# CLI argument parsing
# ---------------------------------------------------------------------------


class TestBuildParser:
    def test_default_transport_is_stdio(self):
        parser = _build_parser()
        args = parser.parse_args([])
        assert args.transport == "stdio"

    def test_transport_http(self):
        parser = _build_parser()
        args = parser.parse_args(["--transport", "http"])
        assert args.transport == "http"

    def test_transport_stdio_explicit(self):
        parser = _build_parser()
        args = parser.parse_args(["--transport", "stdio"])
        assert args.transport == "stdio"

    def test_invalid_transport_rejected(self):
        parser = _build_parser()
        with pytest.raises(SystemExit):
            parser.parse_args(["--transport", "websocket"])

    def test_default_host(self):
        parser = _build_parser()
        args = parser.parse_args([])
        assert args.host == "127.0.0.1"

    def test_custom_host(self):
        parser = _build_parser()
        args = parser.parse_args(["--host", "0.0.0.0"])
        assert args.host == "0.0.0.0"

    def test_default_port(self):
        parser = _build_parser()
        args = parser.parse_args([])
        assert args.port == 8000

    def test_custom_port(self):
        parser = _build_parser()
        args = parser.parse_args(["--port", "9000"])
        assert args.port == 9000

    def test_all_args_combined(self):
        parser = _build_parser()
        args = parser.parse_args([
            "--transport", "http",
            "--host", "0.0.0.0",
            "--port", "9999",
        ])
        assert args.transport == "http"
        assert args.host == "0.0.0.0"
        assert args.port == 9999


# ---------------------------------------------------------------------------
# MCP instance creation
# ---------------------------------------------------------------------------


class TestCreateMcp:
    def test_creates_mcp_with_tools(self):
        mcp = _create_mcp()
        tool_names = list(mcp._tool_manager._tools.keys())
        assert "muninn_save" in tool_names
        assert "muninn_recall" in tool_names
        assert "muninn_search" in tool_names
        assert "muninn_status" in tool_names
        assert "muninn_manage" in tool_names

    def test_creates_mcp_with_six_tools(self):
        mcp = _create_mcp()
        assert len(mcp._tool_manager._tools) == 6

    def test_creates_mcp_with_sync_tool(self):
        mcp = _create_mcp()
        tool_names = list(mcp._tool_manager._tools.keys())
        assert "muninn_sync" in tool_names
