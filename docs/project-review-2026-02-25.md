# Muninn Project Review — 2026-02-25

**Reviewer perspective:** Senior AI Research Engineer (as per CLAUDE.md feedback persona)
**Scope:** Full codebase review — architecture, code quality, security, scope, direction
**Codebase at review time:** ~6,800 lines Python, 264 tests passing, v0.2.0

---

## What's Genuinely Strong

### 1. Core Abstraction — Depth System

The depth system (0-3) is the most valuable design decision in this project. "What is this? / To continue / To go deeper / Just in case" provides an explicit, human-readable hierarchy for LLM context loading. Most memory systems rely on vague "relevance scores" — this gives the LLM and the user a clear mental model of what's being loaded and why.

### 2. Tool Docstrings as Prompt Engineering

The docstrings in `tools.py` are not API documentation — they're LLM instructions. The Good/Bad examples in `muninn_save`, the "when to call" / "when NOT to call" guidance in `muninn_recall` and `muninn_search` — this is best-practice MCP tool design. The tools teach the LLM how to use them correctly.

### 3. Engineering Hygiene

- Frozen dataclasses for consistent immutability
- FTS5 sync triggers for automatic search index maintenance
- WAL mode + busy_timeout for concurrency
- Character budget (no tokenizer dependency)
- Prefix ID matching (LLM-friendly — 8 chars is enough)
- 264 tests including concurrency, unicode/Korean, edge cases
- Timing-safe auth comparison (`hmac.compare_digest`)

### 4. PRD Quality

The PRD is a living document with a decision log that's actually being maintained. This is rare for side projects.

---

## Structural Issues

### 5. Connection-per-Operation Pattern

Every method in `store.py` opens and closes a new SQLite connection. A single `muninn_recall` call triggers `recall()` + N x `get_project()` = N+1 connections.

**Impact:** Negligible at solo-builder scale. Becomes meaningful under HTTP transport with concurrent clients.

**Recommendation:** Introduce a context manager pattern (`with self.connection() as conn:`) to create a migration path for future connection reuse. Not urgent.

### 6. `superseded_by = '_deleted'` Sentinel

One column carries two meanings: "the memory ID that replaced this" and "this was deleted." Mixing deletion state with referential data in the same column is a code smell.

**Impact:** Low now. Becomes painful if "undelete" or "deletion audit" features are ever needed.

**Recommendation:** Ship as-is. A separate `deleted_at TIMESTAMP` column would be cleaner, but the refactoring cost exceeds the current benefit.

### 7. `muninn_manage` Overloaded

5 actions in one tool with a stringly-typed `field`/`value` pattern:

```python
action: Literal["set_status", "delete_memory", "update_memory", "update_project", "create_project"]
```

LLMs cannot determine from the JSON schema which parameters are required for which action. Nothing prevents passing `status="paused"` with `action="update_memory"`.

**Recommendation:** Consider splitting into at least two tools (`muninn_manage` for project ops, `muninn_edit` for memory ops). Monitor LLM error rates via `usage.jsonl` to validate whether this is actually causing problems.

### 8. Module-level `_store` Global

```python
_store: MuninnStore | None = None
```

This is a constraint partly inherited from MCP SDK's tool registration model (`mcp.tool()(func)`). It works but makes testing require explicit `init_store()` calls and prevents running multiple store instances.

**Recommendation:** Accept as SDK limitation for now. Revisit if FastMCP adds dependency injection support.

---

## Security / Stability

### 9. REST API Input Validation Missing

`api.py:126`:
```python
depth = int(request.query_params.get("depth", "3"))
```

Passing `?depth=abc` triggers an uncaught `ValueError` → HTTP 500. Same for `limit`. Negative values and extremely large numbers pass without validation.

**Severity:** Medium. MCP tools are protected by model-level validation, but REST API is a directly exposed attack surface.

**Recommendation:** Add try/except with sensible defaults and range clamping. ~30 minutes of work.

### 10. No Memory Content Size Limit

`validate_memory_content()` only checks for empty/whitespace. A rogue LLM can dump megabytes into a single save. Over time this bloats the SQLite database.

**Recommendation:** Add `max_content_length` validation (e.g., 50KB). ~10 minutes of work.

### 11. No Garbage Collection for Soft-Deleted Memories

Soft-deleted memories (`superseded_by = '_deleted'`) accumulate forever. No purge mechanism exists.

**Recommendation:** Add a `muninn_manage` action or CLI command for GC (e.g., purge deleted memories older than 90 days). Low priority but worth tracking.

---

## Scope Creep Analysis

### Core vs Peripheral Code

| Layer | Lines | Purpose |
|-------|-------|---------|
| `store.py` | 888 | SQLite operations |
| `tools.py` | 476 | MCP tool definitions |
| `formatter.py` | 257 | LLM output formatting |
| `models.py` | 122 | Data models + validators |
| **Core total** | **~1,743** | **Delivers the core value proposition** |

| Layer | Lines | Purpose |
|-------|-------|---------|
| `oauth_provider.py` | 554 | OAuth 2.1 implementation |
| `api.py` | 298 | REST API for dashboard |
| `server.py` | 278 | Multi-mode server entry |
| `github_sync.py` | 260 | GitHub integration |
| `oauth_login.py` | 112 | PIN login UI |
| `auth.py` | 89 | Bearer token middleware |
| **Peripheral total** | **~1,591** | **Infrastructure & integrations** |

The peripheral code is nearly as large as the core. This isn't inherently wrong — HTTP transport and auth are necessary for remote access. But it signals that feature development is outpacing core validation.

### The Unvalidated Hypothesis

The core value proposition is: "LLMs can effectively manage structured project memory using the depth system across multiple tools."

Questions that remain unanswered:
- Do LLMs consistently choose correct depth levels without human correction?
- Does memory quality degrade over time (duplication, staleness)?
- Is the character budget system actually effective at protecting context windows?
- Do users naturally use `muninn_manage update_memory` instead of creating duplicates?

OAuth, Dashboard, and GitHub sync were built before these questions were answered. The dashboard has a plan document and REST API but no frontend consumer.

---

## Missing Capabilities

### 12. No Deduplication

LLMs tend to save the same information repeatedly. Nothing prevents 3 copies of "OAuth implemented" from accumulating. Content similarity detection would directly protect memory quality — this is a core value concern, not a nice-to-have.

### 13. Documentation Drift

CLAUDE.md states "5 tools" but `muninn_sync` brings the actual count to 6. The tool table in CLAUDE.md is stale.

---

## Action Items

### Immediate (do now)

| Item | Effort | Impact |
|------|--------|--------|
| Add REST API input validation (depth, limit params) | 30 min | Prevents 500 errors on bad input |
| Add memory content size limit | 10 min | Prevents DB bloat from rogue saves |
| Update CLAUDE.md tool count (5 → 6, add `muninn_sync`) | 5 min | Docs accuracy |

### Short-term (validate core)

| Item | Effort | Impact |
|------|--------|--------|
| Use the 5 core tools daily across multiple AI tools | Ongoing | Validates the core hypothesis |
| Analyze `usage.jsonl` for LLM error patterns | 1 hour | Data-driven tool design decisions |
| Consider content similarity check on save | 2-4 hours | Prevents memory quality degradation |

### Deferred (let data decide)

| Item | Signal to watch |
|------|-----------------|
| Split `muninn_manage` into multiple tools | High error rate in usage logs |
| Add GC for soft-deleted memories | DB size growth over months |
| Connection pooling in store.py | Measurable latency under concurrent HTTP |
| Dashboard frontend | Confirmed need beyond CLI + MCP tools |
| `superseded_by` column refactoring | Need for undelete or audit trail |

---

## Summary

**The core is solid.** Depth system, FTS5 search, tool docstring quality, test coverage, and immutability patterns are all well above typical side-project standards.

**The biggest risk is not technical debt — it's feature creep delaying core validation.** The project needs less "more features" and more "use it every day and see what breaks." OAuth, Dashboard API, and GitHub sync add complexity without first proving that the 5 core tools deliver on the cross-tool memory promise.

**Bottom line:** Stop building infrastructure. Start using it. Let the data tell you what to build next.
