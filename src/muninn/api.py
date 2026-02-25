"""REST API routes for the Muninn dashboard.

Provides JSON endpoints that the web frontend consumes.
Uses store.py directly (not MCP tools) for structured data access.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from typing import TYPE_CHECKING

from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

if TYPE_CHECKING:
    from muninn.store import MuninnStore


def _safe_int(value: str | None, default: int, lo: int, hi: int) -> int:
    """Parse an integer from a query param, clamped to [lo, hi]."""
    if value is None:
        return default
    try:
        return max(lo, min(hi, int(value)))
    except (ValueError, TypeError):
        return default


def _memory_to_dict(memory: object) -> dict:
    """Convert a Memory dataclass to a JSON-friendly dict."""
    d = asdict(memory)  # type: ignore[arg-type]
    d["tags"] = list(d["tags"])
    d["short_id"] = d["id"][:8]
    depth_labels = {0: "summary", 1: "context", 2: "detailed", 3: "full"}
    d["depth_label"] = depth_labels.get(d["depth"], str(d["depth"]))
    return d


def _project_to_dict(project: object) -> dict:
    """Convert a Project dataclass to a JSON-friendly dict."""
    return asdict(project)  # type: ignore[arg-type]


def create_api_routes(store: MuninnStore) -> list[Route]:
    """Create dashboard REST API routes bound to the given store."""

    # ------------------------------------------------------------------
    # Projects
    # ------------------------------------------------------------------

    async def list_projects(request: Request) -> JSONResponse:
        status = request.query_params.get("status")
        projects = store.list_projects(status=status)
        return JSONResponse([_project_to_dict(p) for p in projects])

    async def get_project(request: Request) -> JSONResponse:
        project_id = request.path_params["project_id"]
        project = store.get_project(project_id)
        if project is None:
            return JSONResponse(
                {"error": f"Project '{project_id}' not found", "code": "NOT_FOUND"},
                status_code=404,
            )
        data = _project_to_dict(project)
        data["depth_distribution"] = store.get_depth_distribution(project_id)
        return JSONResponse(data)

    async def create_project(request: Request) -> JSONResponse:
        try:
            body = await request.json()
        except json.JSONDecodeError:
            return JSONResponse(
                {"error": "Invalid JSON body", "code": "BAD_REQUEST"},
                status_code=400,
            )
        project_id = body.get("id")
        name = body.get("name")
        if not project_id or not name:
            return JSONResponse(
                {"error": "'id' and 'name' are required", "code": "BAD_REQUEST"},
                status_code=400,
            )
        existing = store.get_project(project_id)
        if existing is not None:
            return JSONResponse(
                {"error": f"Project '{project_id}' already exists", "code": "CONFLICT"},
                status_code=409,
            )
        project = store.create_project(
            id=project_id,
            name=name,
            summary=body.get("summary"),
            github_repo=body.get("github_repo"),
        )
        return JSONResponse(_project_to_dict(project), status_code=201)

    async def update_project(request: Request) -> JSONResponse:
        project_id = request.path_params["project_id"]
        try:
            body = await request.json()
        except json.JSONDecodeError:
            return JSONResponse(
                {"error": "Invalid JSON body", "code": "BAD_REQUEST"},
                status_code=400,
            )
        allowed = {"name", "status", "summary", "github_repo"}
        kwargs = {k: v for k, v in body.items() if k in allowed}
        if not kwargs:
            return JSONResponse(
                {"error": "No valid fields to update", "code": "BAD_REQUEST"},
                status_code=400,
            )
        try:
            project = store.update_project(project_id, **kwargs)
        except ValueError as exc:
            return JSONResponse(
                {"error": str(exc), "code": "NOT_FOUND"},
                status_code=404,
            )
        return JSONResponse(_project_to_dict(project))

    # ------------------------------------------------------------------
    # Memories
    # ------------------------------------------------------------------

    async def list_memories(request: Request) -> JSONResponse:
        project_id = request.path_params["project_id"]
        project = store.get_project(project_id)
        if project is None:
            return JSONResponse(
                {"error": f"Project '{project_id}' not found", "code": "NOT_FOUND"},
                status_code=404,
            )
        depth = _safe_int(request.query_params.get("depth"), default=3, lo=0, hi=3)
        max_chars = _safe_int(request.query_params.get("max_chars"), default=50000, lo=100, hi=500000)
        tags_param = request.query_params.get("tags")
        tags = [t.strip() for t in tags_param.split(",") if t.strip()] if tags_param else None

        memories_by_project, stats = store.recall(
            project_id=project_id,
            depth=depth,
            max_chars=max_chars,
            tags=tags,
        )
        memories = memories_by_project.get(project_id, [])
        return JSONResponse({
            "memories": [_memory_to_dict(m) for m in memories],
            "stats": stats,
        })

    async def get_memory(request: Request) -> JSONResponse:
        memory_id = request.path_params["memory_id"]
        memory = store.get_memory(memory_id)
        if memory is None:
            return JSONResponse(
                {"error": f"Memory '{memory_id}' not found", "code": "NOT_FOUND"},
                status_code=404,
            )
        return JSONResponse(_memory_to_dict(memory))

    async def create_memory(request: Request) -> JSONResponse:
        try:
            body = await request.json()
        except json.JSONDecodeError:
            return JSONResponse(
                {"error": "Invalid JSON body", "code": "BAD_REQUEST"},
                status_code=400,
            )
        project_id = body.get("project_id")
        content = body.get("content")
        if not project_id or not content:
            return JSONResponse(
                {"error": "'project_id' and 'content' are required", "code": "BAD_REQUEST"},
                status_code=400,
            )
        project = store.get_project(project_id)
        if project is None:
            return JSONResponse(
                {"error": f"Project '{project_id}' not found", "code": "NOT_FOUND"},
                status_code=404,
            )
        raw_depth = body.get("depth", 1)
        try:
            depth = max(0, min(3, int(raw_depth)))
        except (ValueError, TypeError):
            depth = 1
        try:
            memory = store.save_memory(
                project_id=project_id,
                content=content,
                depth=depth,
                source=body.get("source", "manual"),
                tags=body.get("tags"),
                parent_memory_id=body.get("parent_memory_id"),
            )
        except ValueError as exc:
            return JSONResponse(
                {"error": str(exc), "code": "BAD_REQUEST"},
                status_code=400,
            )
        return JSONResponse(_memory_to_dict(memory), status_code=201)

    async def update_memory(request: Request) -> JSONResponse:
        memory_id = request.path_params["memory_id"]
        try:
            body = await request.json()
        except json.JSONDecodeError:
            return JSONResponse(
                {"error": "Invalid JSON body", "code": "BAD_REQUEST"},
                status_code=400,
            )
        kwargs = {}
        if "content" in body:
            kwargs["content"] = body["content"]
        if "depth" in body:
            try:
                kwargs["depth"] = max(0, min(3, int(body["depth"])))
            except (ValueError, TypeError):
                return JSONResponse(
                    {"error": "depth must be an integer 0-3", "code": "BAD_REQUEST"},
                    status_code=400,
                )
        if "tags" in body:
            kwargs["tags"] = body["tags"]
        if "parent_memory_id" in body:
            kwargs["parent_memory_id"] = body["parent_memory_id"]
        if not kwargs:
            return JSONResponse(
                {"error": "No valid fields to update", "code": "BAD_REQUEST"},
                status_code=400,
            )
        try:
            memory = store.update_memory(memory_id, **kwargs)
        except ValueError as exc:
            return JSONResponse(
                {"error": str(exc), "code": "BAD_REQUEST"},
                status_code=400,
            )
        if memory is None:
            return JSONResponse(
                {"error": f"Memory '{memory_id}' not found", "code": "NOT_FOUND"},
                status_code=404,
            )
        return JSONResponse(_memory_to_dict(memory))

    async def delete_memory(request: Request) -> JSONResponse:
        memory_id = request.path_params["memory_id"]
        deleted = store.delete_memory(memory_id)
        if not deleted:
            return JSONResponse(
                {"error": f"Memory '{memory_id}' not found", "code": "NOT_FOUND"},
                status_code=404,
            )
        return JSONResponse({"deleted": True})

    # ------------------------------------------------------------------
    # Search, Tags, Stats, Supersede Chain
    # ------------------------------------------------------------------

    async def search_memories(request: Request) -> JSONResponse:
        query = request.query_params.get("q", "")
        if not query.strip():
            return JSONResponse(
                {"error": "'q' query parameter is required", "code": "BAD_REQUEST"},
                status_code=400,
            )
        project_id = request.query_params.get("project")
        tags_param = request.query_params.get("tags")
        tags = [t.strip() for t in tags_param.split(",") if t.strip()] if tags_param else None
        limit = _safe_int(request.query_params.get("limit"), default=50, lo=1, hi=200)

        memories = store.search(
            query=query,
            project_id=project_id,
            tags=tags,
            limit=limit,
        )
        return JSONResponse({
            "results": [_memory_to_dict(m) for m in memories],
            "count": len(memories),
        })

    async def list_tags(request: Request) -> JSONResponse:
        project_id = request.query_params.get("project")
        tags = store.get_all_tags(project_id=project_id)
        return JSONResponse(tags)

    async def get_stats(request: Request) -> JSONResponse:
        stats = store.get_dashboard_stats()
        return JSONResponse(stats)

    async def get_supersede_chain(request: Request) -> JSONResponse:
        memory_id = request.path_params["memory_id"]
        chain = store.get_supersede_chain(memory_id)
        if not chain:
            return JSONResponse(
                {"error": f"Memory '{memory_id}' not found", "code": "NOT_FOUND"},
                status_code=404,
            )
        return JSONResponse([_memory_to_dict(m) for m in chain])

    # ------------------------------------------------------------------
    # Graph
    # ------------------------------------------------------------------

    async def get_memory_graph(request: Request) -> JSONResponse:
        project_id = request.path_params["project_id"]
        project = store.get_project(project_id)
        if project is None:
            return JSONResponse(
                {"error": f"Project '{project_id}' not found", "code": "NOT_FOUND"},
                status_code=404,
            )
        memories = store.get_memory_graph(project_id)
        nodes = [_memory_to_dict(m) for m in memories]
        edges = []
        for m in memories:
            if m.parent_memory_id:
                edges.append({
                    "id": f"e-{m.parent_memory_id[:8]}-{m.id[:8]}",
                    "source": m.parent_memory_id,
                    "target": m.id,
                })
        return JSONResponse({"nodes": nodes, "edges": edges})

    # ------------------------------------------------------------------
    # Route table
    # ------------------------------------------------------------------

    return [
        Route("/projects", list_projects, methods=["GET"]),
        Route("/projects", create_project, methods=["POST"]),
        Route("/projects/{project_id}", get_project, methods=["GET"]),
        Route("/projects/{project_id}", update_project, methods=["PATCH"]),
        Route("/projects/{project_id}/memories", list_memories, methods=["GET"]),
        Route("/projects/{project_id}/graph", get_memory_graph, methods=["GET"]),
        Route("/memories", create_memory, methods=["POST"]),
        Route("/memories/{memory_id}", get_memory, methods=["GET"]),
        Route("/memories/{memory_id}", update_memory, methods=["PATCH"]),
        Route("/memories/{memory_id}", delete_memory, methods=["DELETE"]),
        Route("/memories/{memory_id}/chain", get_supersede_chain, methods=["GET"]),
        Route("/search", search_memories, methods=["GET"]),
        Route("/tags", list_tags, methods=["GET"]),
        Route("/stats", get_stats, methods=["GET"]),
    ]
