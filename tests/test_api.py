"""Unit tests for the Muninn dashboard REST API."""

from __future__ import annotations

import pytest
from starlette.applications import Starlette
from starlette.routing import Mount
from starlette.testclient import TestClient

from muninn.api import create_api_routes
from muninn.store import MuninnStore


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def api_store(tmp_path):
    """Return a MuninnStore backed by an isolated temporary SQLite database."""
    db_path = str(tmp_path / "test_api.db")
    return MuninnStore(db_path=db_path)


@pytest.fixture
def client(api_store):
    """Return a Starlette TestClient with the API routes mounted."""
    routes = create_api_routes(api_store)
    app = Starlette(routes=[Mount("/api", routes=routes)])
    return TestClient(app, raise_server_exceptions=True)


@pytest.fixture
def seeded_store(api_store):
    """Return a store with sample projects and memories."""
    api_store.create_project(id="muninn", name="Muninn", summary="MCP memory server")
    api_store.create_project(id="aido", name="Aido")
    api_store.save_memory("muninn", "Project identity: MCP memory server", depth=0, tags=["core"])
    api_store.save_memory("muninn", "Using SQLite with WAL mode", depth=1, tags=["decision", "architecture"])
    api_store.save_memory("muninn", "Full schema design notes", depth=2, tags=["architecture"])
    api_store.save_memory("aido", "AI startup scoring engine", depth=0, tags=["core"])
    return api_store


@pytest.fixture
def seeded_client(seeded_store):
    """Return a TestClient with pre-seeded data."""
    routes = create_api_routes(seeded_store)
    app = Starlette(routes=[Mount("/api", routes=routes)])
    return TestClient(app, raise_server_exceptions=True)


# ---------------------------------------------------------------------------
# GET /api/projects
# ---------------------------------------------------------------------------


class TestListProjects:
    def test_empty_projects(self, client):
        resp = client.get("/api/projects")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_returns_all_projects(self, seeded_client):
        resp = seeded_client.get("/api/projects")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        ids = {p["id"] for p in data}
        assert ids == {"muninn", "aido"}

    def test_filter_by_status(self, seeded_client, seeded_store):
        seeded_store.update_project("aido", status="paused")
        resp = seeded_client.get("/api/projects?status=active")
        data = resp.json()
        assert len(data) == 1
        assert data[0]["id"] == "muninn"

    def test_project_has_memory_count(self, seeded_client):
        resp = seeded_client.get("/api/projects")
        data = resp.json()
        muninn = next(p for p in data if p["id"] == "muninn")
        assert muninn["memory_count"] == 3


# ---------------------------------------------------------------------------
# GET /api/projects/:id
# ---------------------------------------------------------------------------


class TestGetProject:
    def test_existing_project(self, seeded_client):
        resp = seeded_client.get("/api/projects/muninn")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == "muninn"
        assert data["name"] == "Muninn"
        assert data["summary"] == "MCP memory server"
        assert "depth_distribution" in data

    def test_depth_distribution(self, seeded_client):
        resp = seeded_client.get("/api/projects/muninn")
        dist = resp.json()["depth_distribution"]
        # Keys are strings in JSON
        assert dist["0"] == 1
        assert dist["1"] == 1
        assert dist["2"] == 1

    def test_not_found(self, client):
        resp = client.get("/api/projects/nonexistent")
        assert resp.status_code == 404
        assert resp.json()["code"] == "NOT_FOUND"


# ---------------------------------------------------------------------------
# POST /api/projects
# ---------------------------------------------------------------------------


class TestCreateProject:
    def test_create_project(self, client):
        resp = client.post("/api/projects", json={"id": "test", "name": "Test Project"})
        assert resp.status_code == 201
        data = resp.json()
        assert data["id"] == "test"
        assert data["name"] == "Test Project"

    def test_create_with_summary(self, client):
        resp = client.post("/api/projects", json={
            "id": "test",
            "name": "Test",
            "summary": "A test project",
        })
        assert resp.status_code == 201
        assert resp.json()["summary"] == "A test project"

    def test_duplicate_project(self, seeded_client):
        resp = seeded_client.post("/api/projects", json={"id": "muninn", "name": "Dup"})
        assert resp.status_code == 409

    def test_missing_fields(self, client):
        resp = client.post("/api/projects", json={"id": "test"})
        assert resp.status_code == 400

    def test_invalid_json(self, client):
        resp = client.post("/api/projects", content=b"not json", headers={"content-type": "application/json"})
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# PATCH /api/projects/:id
# ---------------------------------------------------------------------------


class TestUpdateProject:
    def test_update_status(self, seeded_client):
        resp = seeded_client.patch("/api/projects/muninn", json={"status": "paused"})
        assert resp.status_code == 200
        assert resp.json()["status"] == "paused"

    def test_update_name(self, seeded_client):
        resp = seeded_client.patch("/api/projects/muninn", json={"name": "Muninn v2"})
        assert resp.status_code == 200
        assert resp.json()["name"] == "Muninn v2"

    def test_update_not_found(self, client):
        resp = client.patch("/api/projects/nope", json={"name": "x"})
        assert resp.status_code == 404

    def test_update_empty_body(self, seeded_client):
        resp = seeded_client.patch("/api/projects/muninn", json={"unknown": "field"})
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# GET /api/projects/:id/memories
# ---------------------------------------------------------------------------


class TestListMemories:
    def test_returns_memories(self, seeded_client):
        resp = seeded_client.get("/api/projects/muninn/memories")
        assert resp.status_code == 200
        data = resp.json()
        assert "memories" in data
        assert "stats" in data
        assert len(data["memories"]) == 3

    def test_depth_filter(self, seeded_client):
        resp = seeded_client.get("/api/projects/muninn/memories?depth=0")
        memories = resp.json()["memories"]
        assert len(memories) == 1
        assert memories[0]["depth"] == 0

    def test_tags_filter(self, seeded_client):
        resp = seeded_client.get("/api/projects/muninn/memories?tags=architecture")
        memories = resp.json()["memories"]
        assert len(memories) == 2
        for m in memories:
            assert "architecture" in m["tags"]

    def test_project_not_found(self, client):
        resp = client.get("/api/projects/nope/memories")
        assert resp.status_code == 404

    def test_memory_has_expected_fields(self, seeded_client):
        resp = seeded_client.get("/api/projects/muninn/memories")
        mem = resp.json()["memories"][0]
        assert "id" in mem
        assert "short_id" in mem
        assert "content" in mem
        assert "depth" in mem
        assert "depth_label" in mem
        assert "tags" in mem
        assert isinstance(mem["tags"], list)

    def test_stats_structure(self, seeded_client):
        resp = seeded_client.get("/api/projects/muninn/memories")
        stats = resp.json()["stats"]
        assert "chars_loaded" in stats
        assert "chars_budget" in stats
        assert "memories_loaded" in stats
        assert "memories_dropped" in stats


# ---------------------------------------------------------------------------
# POST /api/memories
# ---------------------------------------------------------------------------


class TestCreateMemory:
    def test_create_memory(self, seeded_client):
        resp = seeded_client.post("/api/memories", json={
            "project_id": "muninn",
            "content": "New decision: use Starlette REST",
            "depth": 1,
            "tags": ["decision"],
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["content"] == "New decision: use Starlette REST"
        assert data["depth"] == 1
        assert data["tags"] == ["decision"]
        assert data["source"] == "manual"

    def test_missing_content(self, seeded_client):
        resp = seeded_client.post("/api/memories", json={"project_id": "muninn"})
        assert resp.status_code == 400

    def test_project_not_found(self, client):
        resp = client.post("/api/memories", json={
            "project_id": "nope",
            "content": "test",
        })
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# GET /api/memories/:id
# ---------------------------------------------------------------------------


class TestGetMemory:
    def test_get_memory_by_id(self, seeded_client, seeded_store):
        # Get a known memory ID
        memories, _ = seeded_store.recall(project_id="muninn", depth=0)
        mem_id = memories["muninn"][0].id
        resp = seeded_client.get(f"/api/memories/{mem_id}")
        assert resp.status_code == 200
        assert resp.json()["id"] == mem_id

    def test_get_memory_by_prefix(self, seeded_client, seeded_store):
        memories, _ = seeded_store.recall(project_id="muninn", depth=0)
        mem_id = memories["muninn"][0].id
        resp = seeded_client.get(f"/api/memories/{mem_id[:8]}")
        assert resp.status_code == 200
        assert resp.json()["id"] == mem_id

    def test_not_found(self, client):
        resp = client.get("/api/memories/nonexistent")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# PATCH /api/memories/:id
# ---------------------------------------------------------------------------


class TestUpdateMemory:
    def test_update_content(self, seeded_client, seeded_store):
        memories, _ = seeded_store.recall(project_id="muninn", depth=1)
        mem_id = memories["muninn"][0].id
        resp = seeded_client.patch(f"/api/memories/{mem_id}", json={
            "content": "Updated content",
        })
        assert resp.status_code == 200
        assert resp.json()["content"] == "Updated content"

    def test_update_tags(self, seeded_client, seeded_store):
        memories, _ = seeded_store.recall(project_id="muninn", depth=0)
        mem_id = memories["muninn"][0].id
        resp = seeded_client.patch(f"/api/memories/{mem_id}", json={
            "tags": ["updated", "core"],
        })
        assert resp.status_code == 200
        assert set(resp.json()["tags"]) == {"updated", "core"}

    def test_update_not_found(self, client):
        resp = client.patch("/api/memories/nonexistent", json={"content": "x"})
        assert resp.status_code == 404

    def test_empty_update(self, seeded_client, seeded_store):
        memories, _ = seeded_store.recall(project_id="muninn", depth=0)
        mem_id = memories["muninn"][0].id
        resp = seeded_client.patch(f"/api/memories/{mem_id}", json={})
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# DELETE /api/memories/:id
# ---------------------------------------------------------------------------


class TestDeleteMemory:
    def test_delete_memory(self, seeded_client, seeded_store):
        memories, _ = seeded_store.recall(project_id="muninn", depth=0)
        mem_id = memories["muninn"][0].id
        resp = seeded_client.delete(f"/api/memories/{mem_id}")
        assert resp.status_code == 200
        assert resp.json()["deleted"] is True

        # Verify it's gone from recall
        memories2, _ = seeded_store.recall(project_id="muninn", depth=0)
        ids = [m.id for m in memories2.get("muninn", [])]
        assert mem_id not in ids

    def test_delete_not_found(self, client):
        resp = client.delete("/api/memories/nonexistent")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# GET /api/search
# ---------------------------------------------------------------------------


class TestSearch:
    def test_search_finds_results(self, seeded_client):
        resp = seeded_client.get("/api/search?q=SQLite")
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] >= 1
        assert any("SQLite" in r["content"] for r in data["results"])

    def test_search_with_project_filter(self, seeded_client):
        resp = seeded_client.get("/api/search?q=identity&project=muninn")
        assert resp.status_code == 200
        for r in resp.json()["results"]:
            assert r["project_id"] == "muninn"

    def test_search_empty_query(self, seeded_client):
        resp = seeded_client.get("/api/search?q=")
        assert resp.status_code == 400

    def test_search_no_results(self, seeded_client):
        resp = seeded_client.get("/api/search?q=xyznonexistent")
        assert resp.status_code == 200
        assert resp.json()["count"] == 0


# ---------------------------------------------------------------------------
# GET /api/tags
# ---------------------------------------------------------------------------


class TestTags:
    def test_all_tags(self, seeded_client):
        resp = seeded_client.get("/api/tags")
        assert resp.status_code == 200
        tags = resp.json()
        assert isinstance(tags, list)
        assert "core" in tags
        assert "architecture" in tags
        assert "decision" in tags

    def test_tags_by_project(self, seeded_client):
        resp = seeded_client.get("/api/tags?project=aido")
        assert resp.status_code == 200
        tags = resp.json()
        assert "core" in tags
        assert "architecture" not in tags

    def test_empty_tags(self, client):
        resp = client.get("/api/tags")
        assert resp.status_code == 200
        assert resp.json() == []


# ---------------------------------------------------------------------------
# GET /api/stats
# ---------------------------------------------------------------------------


class TestStats:
    def test_stats_empty(self, client):
        resp = client.get("/api/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_projects"] == 0
        assert data["total_memories"] == 0

    def test_stats_with_data(self, seeded_client):
        resp = seeded_client.get("/api/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_projects"] == 2
        assert data["active_projects"] == 2
        assert data["total_memories"] == 4


# ---------------------------------------------------------------------------
# GET /api/memories/:id/chain
# ---------------------------------------------------------------------------


class TestSupersedeChain:
    def test_single_memory_chain(self, seeded_client, seeded_store):
        memories, _ = seeded_store.recall(project_id="muninn", depth=0)
        mem_id = memories["muninn"][0].id
        resp = seeded_client.get(f"/api/memories/{mem_id}/chain")
        assert resp.status_code == 200
        chain = resp.json()
        assert len(chain) == 1
        assert chain[0]["id"] == mem_id

    def test_supersede_chain(self, seeded_client, seeded_store):
        # Create a chain: m1 → m2 → m3
        m1 = seeded_store.save_memory("muninn", "Version 1", depth=1)
        m2 = seeded_store.save_memory("muninn", "Version 2", depth=1)
        m3 = seeded_store.save_memory("muninn", "Version 3", depth=1)
        seeded_store.supersede_memory(m1.id, m2.id)
        seeded_store.supersede_memory(m2.id, m3.id)

        resp = seeded_client.get(f"/api/memories/{m3.id}/chain")
        assert resp.status_code == 200
        chain = resp.json()
        assert len(chain) == 3
        chain_ids = [c["id"] for c in chain]
        assert m1.id in chain_ids
        assert m2.id in chain_ids
        assert m3.id in chain_ids

    def test_chain_not_found(self, client):
        resp = client.get("/api/memories/nonexistent/chain")
        assert resp.status_code == 404
