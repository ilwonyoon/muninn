"""Tests for server CLI parsing and MCP instance creation."""

from __future__ import annotations

import pytest

from muninn.server import _INSTRUCTIONS, _build_parser, _create_mcp, _load_instructions


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
    def test_creates_mcp_with_tools(self, store):
        mcp = _create_mcp(store=store)
        tool_names = list(mcp._tool_manager._tools.keys())
        assert "muninn_save" in tool_names
        assert "muninn_recall" in tool_names
        assert "muninn_search" in tool_names
        assert "muninn_status" in tool_names
        assert "muninn_manage" in tool_names

    def test_creates_mcp_with_six_tools(self, store):
        mcp = _create_mcp(store=store)
        assert len(mcp._tool_manager._tools) == 6

    def test_creates_mcp_with_sync_tool(self, store):
        mcp = _create_mcp(store=store)
        tool_names = list(mcp._tool_manager._tools.keys())
        assert "muninn_sync" in tool_names

    def test_refreshes_instructions_on_each_initialization(self, store):
        store.update_instructions("Instruction A")
        mcp = _create_mcp(store=store)

        first = mcp._mcp_server.create_initialization_options()
        assert first.instructions == "Instruction A"

        store.update_instructions("Instruction B")
        second = mcp._mcp_server.create_initialization_options()
        assert second.instructions == "Instruction B"


class TestInstructionLoading:
    def test_seeds_db_from_legacy_file_when_db_empty(self, store, tmp_path, monkeypatch):
        legacy = tmp_path / "instructions.md"
        legacy.write_text("legacy instructions", encoding="utf-8")
        monkeypatch.setattr("muninn.server._instructions_path", lambda: legacy)

        assert store.get_instructions() == ""
        loaded = _load_instructions(store)

        assert loaded == "legacy instructions"
        assert store.get_instructions() == "legacy instructions"

    def test_seeds_db_with_default_when_db_and_file_are_empty(self, store, tmp_path, monkeypatch):
        missing = tmp_path / "missing-instructions.md"
        monkeypatch.setattr("muninn.server._instructions_path", lambda: missing)

        loaded = _load_instructions(store)

        assert loaded == _INSTRUCTIONS
        assert store.get_instructions() == _INSTRUCTIONS
