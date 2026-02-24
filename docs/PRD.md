# Muninn — Product Requirements Document

*Living document. Updated as implementation progresses.*

> "Odin feared losing Muninn more than Huginn — losing memory is worse than losing thought."

**Last updated:** 2026-02-24
**Status:** Phase 1 — Complete ✅ | Phase 2 — Not started
**Author:** Ilwon Yoon

---

## Table of Contents

1. [Problem Statement](#1-problem-statement)
2. [Target Persona](#2-target-persona)
3. [Success Scenarios](#3-success-scenarios)
4. [Product Vision](#4-product-vision)
5. [Core Philosophy](#5-core-philosophy)
6. [User Scenarios](#6-user-scenarios)
7. [Architecture](#7-architecture)
8. [Technical Specification](#8-technical-specification)
9. [MCP Tools API](#9-mcp-tools-api)
10. [Memory System Design](#10-memory-system-design)
11. [Development Phases](#11-development-phases)
12. [Testing & Validation Strategy](#12-testing--validation-strategy)
13. [Success Metrics](#13-success-metrics)
14. [Competitive Landscape](#14-competitive-landscape)
15. [Open Questions & Future Directions](#15-open-questions--future-directions)
16. [Decision Log](#16-decision-log)
17. [Changelog](#17-changelog)

---

## 1. Problem Statement

### The pain

Solo builders running multiple side projects across multiple AI tools face **context fragmentation**:

- **Cross-tool amnesia:** 2 hours of brainstorming in Claude app, switch to Claude Code — it knows nothing.
- **Repetitive re-explanation:** Every new session starts with "this project is X, tech stack is Y, we're at Z..."
- **Stale project references:** Claude's memory remembers "building 글뿌리" but doesn't know it's paused. No way to stop it from bringing it up.
- **Code state blindness:** AI knows decisions from conversations but not actual implementation state from GitHub.
- **Token overload:** Loading all context at once exceeds limits; loading none means no context.

### Why existing solutions fail

| Solution | Gap |
|----------|-----|
| Mem0 ($24M funded) | B2B infra for app developers, not personal use |
| Nowledge Mem (alpha) | Auto-captures everything (noisy), no project structure, no GitHub, no lifecycle |
| Claude Memory | Single platform, can't control what it remembers/forgets |
| ChatGPT Memory | Single platform, flat namespace, no API |
| Basic Memory | Markdown notes, Claude-centric, not multi-project structured |
| Copy-paste | What we do today. Painful, lossy, doesn't scale |

### Market context

Layer 3 of the AI memory market ("remember me across all my AI tools") is the most underserved. Torch Capital: "We need new tools that manage user memory across different AI applications."

Letta benchmark insight: a simple filesystem agent scored 74% on LOCOMO, beating Mem0's 68.5%. Simple infrastructure done right can outperform complex systems.

---

## 2. Target Persona

### Primary: Multi-project solo builder

**Name:** Ilwon (real user and creator)

**Profile:**
- Solo builder / indie hacker
- 5+ side projects simultaneously (AIDO, 글뿌리, Focus Knob, Ouri, Muninn...)
- 5+ AI tools daily (Claude app, Claude Code, ChatGPT, Codex, Cursor)
- Technically capable of CLI installation and configuration
- Builds own productivity tooling

**Core frustration:**
> "Every tool switch = context reset. Every session = re-explanation from scratch."

### Why this persona grows

- AI tools are specializing (coding AI, chat AI, research AI, design AI...)
- Within 1-2 years, using 5+ AI tools will be default behavior
- Solo builder / micro-SaaS trend = more people without teams, more dependent on AI
- More tools = more fragmentation = more demand for Muninn

### Honest market critique

- Market is small today (tens of thousands globally)
- Solo builders are notoriously cost-sensitive
- Nowledge Mem has a full-time team on similar problem
- BUT: as an open-source portfolio project with $0 cost, downside is near zero

---

## 3. Success Scenarios — Before / After / Wow

이 섹션은 Muninn이 성공했을 때 사용자의 일상이 어떻게 바뀌는지를 정의합니다. 기능 목록이 아니라 **결과**를 기준으로 합니다.

### Success 1: 브레인스토밍이 코드로 끊김 없이 연결된다

**Before (지금):**
Claude App에서 2시간 동안 글뿌리 게이미피케이션을 논의함. 스트릭 보너스 배율, MVP 포함/제외 기준, 테이블 구조까지 다 정함. Claude Code를 열면 — 백지. 대화 전체를 복사해서 붙여넣음. 2,000토큰 소모. 3분 낭비. 붙여넣은 내용이 길어서 Claude가 절반을 무시함.

**After (Muninn):**
Claude App에서 "이거 glpuri에 저장해" 한 마디. Claude Code를 열면 "글뿌리: 스트릭 보너스 3일=1.5x, 캐릭터 성장 MVP 제외" — 핵심만 로드. 바로 코딩 시작.

**Wow 결과:**
- 복붙 0회
- 맥락 셋업 시간: 3분 → 0초
- 낭비 토큰: 2,000 → 0
- 저장된 것은 AI가 요약한 핵심 결정사항이라 원본 대화보다 더 유용

### Success 2: GitHub 코드 상태와 대화 결정사항이 하나로 합쳐진다

**Before (지금):**
Cursor에서 인증 로직을 Supabase Auth로 리팩토링하고 GitHub에 푸시함. 다음 날 Claude App에서 "글뿌리 어디까지 됐지?" 하면 — Claude는 모름. "인증은 Firebase 기반이었죠?"라고 틀린 말을 함. 사용자가 직접 "아니, Supabase로 바꿨어"라고 수정해야 함.

**After (Muninn):**
`muninn_sync("glpuri")` → GitHub에서 최근 커밋, 오픈 이슈를 가져옴. recall하면:
- 대화 메모리: "게이미피케이션 결정사항, MVP 범위"
- GitHub 메모리: "최근 커밋: auth → Supabase Auth 리팩토링. 오픈 이슈: #12 XP 계산 버그"

**Wow 결과:**
- AI가 실제 코드 상태를 알고 있음 — 틀린 가정으로 시작하지 않음
- 결정(대화)과 실행(코드)이 한 트리에서 보임
- "어디까지 했지?"에 대한 답이 정확함

### Success 3: 과거 의사결정을 즉시 복귀할 수 있다

**Before (지금):**
3주 전에 AIDO의 기업 스코어링 알고리즘 가중치를 논의했음. "펀딩 단계 비중을 얼마로 했었지?" — 대화 기록을 스크롤해서 찾음. 못 찾으면 다시 논의. 같은 결정을 두 번 내림.

**After (Muninn):**
"aido에서 scoring 관련 저장한 거 찾아줘" → `muninn_search("scoring", project="aido")` → "스코어링 가중치: 펀딩 단계 0.3, 팀 규모 0.2, 기술 스택 0.3, 문화 0.2 (2026-02-10 결정)". 3초.

**Wow 결과:**
- 의사결정 검색 시간: 10분 스크롤 → 3초
- 같은 결정을 두 번 내리는 일이 없음
- 결정의 날짜와 맥락이 보존됨

### Success 4: 불필요한 프로젝트가 맥락을 오염시키지 않는다

**Before (지금):**
Claude에게 "뭘 도와줄까요?"하면 "글뿌리 프로젝트를 진행 중이시죠!"라고 함. 글뿌리는 3주 전에 멈췄음. "아니, 지금은 AIDO에 집중하고 있어"라고 매번 교정. 삭제하면 나중에 재개할 때 다 잃어버림.

**After (Muninn):**
`muninn_manage(action="set_status", project="glpuri", status="paused")`. 다음 세션부터 글뿌리는 recall에 안 나옴. 2주 후 다시 시작하고 싶으면 status를 active로 바꾸면 → 모든 메모리가 그대로 있음.

**Wow 결과:**
- 멈춘 프로젝트 교정 발언: 매 세션 → 0회
- 데이터 손실 없이 컨텍스트에서만 제거
- 5개 프로젝트 중 active 2개만 로드 → 토큰 절약 60%

### Success 5: 어떤 도구에서든 내 프로젝트 전체 현황을 한눈에 본다

**Before (지금):**
"지금 내가 뭐하고 있지?" — 머릿속으로 떠올림. Claude에게 물으면 기억나는 것만 불완전하게 답함. Notion이나 별도 문서를 따로 관리하지 않으면 전체 그림이 없음.

**After (Muninn):**
어떤 AI 도구에서든 `muninn_status()`:
```
muninn      🟢 active    오늘        memories: 15
aido        🟢 active    3일 전      memories: 8
glpuri      ⏸️ paused    2주 전      memories: 23
focus-knob  💤 idea      1개월 전    memories: 3
```

**Wow 결과:**
- 전체 포트폴리오 조감도가 3초 안에
- stale 경고(🟡)로 방치된 프로젝트 발견
- 어떤 도구에서든 동일한 뷰

---

### 성공의 한 줄 정의

> **Muninn이 성공하면, 솔로 빌더는 AI 도구를 바꿔도 맥락을 잃지 않고, 과거 결정을 즉시 찾을 수 있고, 코드 상태와 대화 결정이 하나로 합쳐지며, 관심 없는 프로젝트가 방해하지 않는다.**

---

## 4. Product Vision

### One-liner

A local MCP server that gives AI tools shared, project-structured memory across sessions and across tools.

### The core loop

```
1. Brainstorm in Claude app     → save key decisions to Muninn
2. Switch to Claude Code        → Muninn loads project context automatically
3. Code changes push to GitHub  → Muninn syncs code state
4. Research in ChatGPT          → save findings to Muninn
5. Background tasks in Codex    → results saved to Muninn
6. Come back next day           → everything is remembered
```

### What Muninn is NOT

- Not a B2B memory API (that's Mem0)
- Not an auto-capture-everything tool (that's Nowledge Mem)
- Not a note-taking app (that's Basic Memory)
- Not a GitHub client (that's the GitHub MCP server)

---

## 5. Core Philosophy

### "Human decides WHAT to remember. AI handles HOW to organize and retrieve."

| Human does | AI does |
|---|---|
| Decides what to save ("save this conversation") | Summarizes and structures when saving |
| Manages project status (active/paused) | Loads only active projects by default |
| Cleans up stale memories (via dashboard) | Shows freshness indicators |
| Prioritizes | Respects depth/token budgets when recalling |

### Design rationale

- Auto-capture creates noise — AI thinks something is important when it's not for the builder
- 20 curated memories > 100 noisy auto-captured ones
- The MCP client (Claude/ChatGPT) already IS an LLM — it summarizes before saving. Cost = $0
- Phase 1 starts manual. Hybrid approach (AI suggests, human approves) is a future direction, not a v1 requirement.

---

## 6. User Scenarios

### Scenario 1: Brainstorm to Code handoff (THE core use case)

```
[Claude App — 2 hours discussing gamification for 글뿌리]

User: "Save this conversation to glpuri"
Claude: muninn_save(project="glpuri", content="Gamification decisions:
  streak bonus 3 days=1.5x XP, character growth excluded from MVP,
  daily challenge system planned for v2",
  tags=["decision", "gamification"])
→ "Saved to glpuri."

[Switch to Claude Code]

User: "Let's implement glpuri gamification"
Claude Code: muninn_recall(project="glpuri")
→ "글뿌리: Korean vocab learning via Chinese character etymology.
  Flutter + Supabase. MVP 30 chars.
  Latest: streak bonus 3 days=1.5x XP, character growth excluded.
  Code state: auth complete, learning flow 70%."
```

Zero copy-paste. Zero re-explanation.

### Scenario 2: Paused project doesn't pollute context (the "글뿌리 problem")

```
[User pauses 글뿌리]
muninn_manage(action="set_status", project="glpuri", status="paused")

[Next session — no project specified]
muninn_recall()
→ Only active projects loaded. 글뿌리 NOT mentioned.

[2 weeks later — resume]
muninn_manage(action="set_status", project="glpuri", status="active")
muninn_recall(project="glpuri")
→ "글뿌리 last state: MVP 30 chars, learning flow 70%, paused 2 weeks ago."
```

Data preserved, but doesn't pollute active context.

### Scenario 3: ChatGPT research to Claude Code implementation

```
[ChatGPT — Deep Research on AI hiring market]

User: "Save this research to aido"
ChatGPT: muninn_save(project="aido",
  content="AI hiring market: 398 AI companies, Series A+ 42%,
  direct hiring vs agency 7:3, avg hiring cycle 45 days.
  Competitors: Hired, Wellfound, AI-Jobs.net — none have AI-specific matching",
  tags=["research", "market-analysis"])

[Switch to Claude Code]
muninn_recall(project="aido")
→ Market research + previous decisions all loaded.
```

ChatGPT's research capability + Claude Code's coding capability, Muninn bridges them.

### Scenario 4: Codex background task results

```
[Codex — async task: write tests]
Codex: muninn_save(project="aido",
  content="Test coverage added: auth module 85%, scoring module 72%.
  2 failing tests — edge case: null funding data in score calculation",
  depth=2, tags=["test", "coverage"])

[Next day in Claude App]
muninn_recall(project="aido", depth=1)
→ "aido: test coverage — auth 85%, scoring 72%.
   Unresolved: null funding score calculation error."
```

Background work visible from any tool.

### Scenario 5: Full day across 4 tools

```
09:00 [Claude App]  → brainstorm dashboard features → save to muninn
11:00 [ChatGPT]     → research UI libraries → save to muninn
14:00 [Claude Code]  → recall → implement with full context from morning
17:00 [Codex]       → recall → write tests, save results
```

4 tool switches, one continuous workflow.

### Scenario 6: Project portfolio overview

```
User: "Show me all my projects"
muninn_status()
→ muninn      🟢 active    updated: today     memories: 12
   aido        🟢 active    updated: 3 days    memories: 8
   glpuri      ⏸️ paused    updated: 2 weeks   memories: 23
   focus-knob  💤 idea      updated: 1 month   memories: 3
   ouri        💤 idea      updated: 1 month   memories: 5
```

### Scenario 7: Progressive depth loading

```
[Session start — lightweight]
muninn_recall()
→ depth 0-1, active projects only, ~2000 tokens
→ "muninn: Cross-tool memory MCP server. Phase 1 in progress.
   aido: AI job platform. 398 companies, competitive analysis 7/15."

[Need more detail]
"Tell me more about aido"
muninn_recall(project="aido", depth=2)
→ Scoring algorithm weights, API schema, Vertex AI credits info...
```

Always starts light, goes deeper on demand. No token waste.

---

## 7. Architecture

```
           Phase 1 (stdio)                          Phase 2 (+ Streamable HTTP)
  ┌──────────────────────────────┐      ┌────────────────────────────────────┐
  │ Claude Desktop (brainstorm)  │      │ Claude Web/Mobile (brainstorm)     │
  │ Claude Code   (coding)      │      │ ChatGPT Web/Desktop (research)     │
  │ Cursor        (editing)     │      │                                    │
  │ Codex         (bg tasks)    │      │                                    │
  └──────────────┬───────────────┘      └─────────────────┬──────────────────┘
                 │ stdio                                  │ Streamable HTTP
                 └──────────────────┬─────────────────────┘
                                    ▼
                          ┌──────────────────┐
                          │   Muninn Server  │  ← Python, runs locally
                          │                  │
                          │  muninn_save()   │  save conversation summary
                          │  muninn_recall() │  load project context
                          │  muninn_search() │  full-text search
                          │  muninn_status() │  projects overview
                          │  muninn_manage() │  project/memory management
                          │  muninn_sync()   │  GitHub sync (Phase 2)
                          └────────┬─────────┘
                                   │
                        ┌──────────┼──────────┐
                        ▼          ▼          ▼
                  ┌──────────┐ ┌────────┐ ┌──────────────┐
                  │ SQLite   │ │ GitHub │ │ Dashboard    │
                  │muninn.db │ │ REST   │ │ (Phase 3)    │
                  └──────────┘ │ API    │ └──────────────┘
                               └────────┘
```

### Transport strategy

Claude Desktop already supports stdio MCP servers via `claude_desktop_config.json`. This means the core use case ("brainstorm in Claude Desktop → code in Claude Code") works in Phase 1 with zero extra code.

ChatGPT and Claude Web/Mobile support remote MCP only via Streamable HTTP (SSE is deprecated). This requires adding a second transport to the server, which FastMCP supports natively.

| Phase | Transport | Clients covered |
|-------|-----------|----------------|
| Phase 1 | stdio | Claude Desktop, Claude Code, Cursor, Codex |
| Phase 2 | + Streamable HTTP | + Claude Web/Mobile, ChatGPT Web/Desktop |

### Client configuration

**Claude Code** (stdio):
```bash
claude mcp add muninn -- uvx muninn-mcp
```

**Claude Desktop** (stdio — `~/Library/Application Support/Claude/claude_desktop_config.json`):
```json
{
  "mcpServers": {
    "muninn": {
      "command": "uvx",
      "args": ["muninn-mcp"]
    }
  }
}
```

**Claude Web/Mobile** (Phase 2 — Streamable HTTP):
- Run `muninn --transport http --port 8787` locally
- Expose via ngrok/Cloudflare Tunnel for public HTTPS URL
- Add URL in claude.ai Settings > Integrations (syncs to mobile)

**ChatGPT** (Phase 2 — Streamable HTTP):
- Same HTTPS endpoint as Claude Web
- Add in ChatGPT Settings > Connectors > Create

---

## 8. Technical Specification

### Tech stack

```
Runtime:      Python 3.11+
MCP SDK:      mcp >= 1.25, < 2  (FastMCP high-level API)
Transport:    stdio (Phase 1) → + HTTP/SSE (Phase 3)
Database:     SQLite3 + FTS5 (full-text search)
GitHub:       PyGithub + Personal Access Token (Phase 2)
Search:       Tag matching + FTS5 (Phase 1) → + sqlite-vec + MiniLM (future)
Dashboard:    None (Phase 1) → React (Phase 2-3)
Cost:         $0/month
```

### Stack rationale

- **Python:** MCP SDK most mature, SQLite built-in, sentence-transformers native
- **SQLite:** Zero config, single-file backup, FTS5 built-in. Trivial scale for 5 projects
- **FastMCP:** Decorator-based tool definition, auto-generates JSON schema from type hints
- **uvx:** Becoming MCP server distribution standard. One command install
- **No vector DB in Phase 1:** Tag + FTS5 is enough. Add sqlite-vec later only if needed
- **No LLM API calls:** MCP client already IS an LLM. Tool descriptions instruct it to summarize. Cost = $0

### Data location

```
Default: ~/.local/share/muninn/muninn.db  (XDG Base Directory standard)
Override: MUNINN_DB_PATH environment variable
Backup:  Single file copy. `cp muninn.db muninn.db.bak`
```

The database file is created automatically on first run. Location follows XDG conventions for user data that should persist across sessions.

### Database schema

```sql
-- Enable WAL mode for concurrent read/write from multiple MCP client processes
PRAGMA journal_mode=WAL;
PRAGMA busy_timeout=5000;  -- 5 second retry on SQLITE_BUSY

CREATE TABLE projects (
    id TEXT PRIMARY KEY,                    -- "aido", "glpuri", "muninn"
    name TEXT NOT NULL,                     -- "AIDO"
    status TEXT DEFAULT 'active'
        CHECK(status IN ('active', 'paused', 'idea', 'archived')),
    summary TEXT,                           -- depth 0: one-line description
    github_repo TEXT,                       -- "ilwon/aido" (optional)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE memories (
    id TEXT PRIMARY KEY,                    -- UUID
    project_id TEXT NOT NULL REFERENCES projects(id),
    content TEXT NOT NULL,                  -- the actual memory content
    depth INTEGER DEFAULT 1
        CHECK(depth BETWEEN 0 AND 3),      -- 0=summary, 1=context, 2=detailed, 3=full
    source TEXT DEFAULT 'conversation'
        CHECK(source IN ('conversation', 'github', 'manual')),
    superseded_by TEXT,                          -- soft delete chain (no FK: uses '_deleted' sentinel)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tags as junction table (not JSON) for clean queries
CREATE TABLE memory_tags (
    memory_id TEXT NOT NULL REFERENCES memories(id) ON DELETE CASCADE,
    tag TEXT NOT NULL,
    PRIMARY KEY (memory_id, tag)
);
CREATE INDEX idx_memory_tags_tag ON memory_tags(tag);

-- Full-text search with triggers to stay in sync
CREATE VIRTUAL TABLE memories_fts USING fts5(
    content,
    content=memories,
    content_rowid=rowid,
    tokenize='porter'
);

-- FTS sync triggers
CREATE TRIGGER memories_ai AFTER INSERT ON memories BEGIN
    INSERT INTO memories_fts(rowid, content) VALUES (new.rowid, new.content);
END;
CREATE TRIGGER memories_ad AFTER DELETE ON memories BEGIN
    INSERT INTO memories_fts(memories_fts, rowid, content) VALUES('delete', old.rowid, old.content);
END;
CREATE TRIGGER memories_au AFTER UPDATE ON memories BEGIN
    INSERT INTO memories_fts(memories_fts, rowid, content) VALUES('delete', old.rowid, old.content);
    INSERT INTO memories_fts(rowid, content) VALUES (new.rowid, new.content);
END;

-- Schema version for future migrations
CREATE TABLE schema_version (
    version INTEGER PRIMARY KEY,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
INSERT INTO schema_version (version) VALUES (1);
```

### Concurrent access strategy

With stdio transport, each MCP client (Claude Code, Cursor, Codex) spawns its own server process. Multiple processes may access the same SQLite file simultaneously.

**Solution:**
- **WAL mode** — allows concurrent reads while one process writes
- **busy_timeout=5000** — retries on `SQLITE_BUSY` for up to 5 seconds instead of failing immediately
- **No connection pooling needed** — each process opens its own connection, SQLite handles locking

This is sufficient for the expected load (5 clients, low write frequency). No ORM or connection pool required.

### Schema migration strategy

`schema_version` table tracks the current schema version. On server startup, `store.py` checks the version and applies migrations sequentially:

```python
MIGRATIONS = {
    2: "ALTER TABLE projects ADD COLUMN ...",  # Phase 2 additions
}
```

Simple, linear, no Alembic dependency.

### Project structure

```
muninn/
├── src/
│   └── muninn/
│       ├── __init__.py          # version
│       ├── server.py            # MCP server entry point (FastMCP + stdio)
│       ├── tools.py             # MCP tool definitions
│       ├── store.py             # SQLite operations (CRUD, FTS, schema init)
│       ├── models.py            # Data classes (Project, Memory)
│       ├── github_sync.py       # GitHub API integration (Phase 2)
│       └── formatter.py         # Format memories for LLM context output
├── tests/
│   ├── test_store.py
│   ├── test_tools.py
│   └── test_formatter.py
├── docs/
│   └── PRD.md                   # This document
├── pyproject.toml
├── Dockerfile
├── README.md
├── LICENSE                      # MIT
└── CLAUDE.md                    # For AI tools to understand this project
```

---

## 9. MCP Tools API

### 8.1 `muninn_save` — Save to project memory

**Trigger:** User says "save this", "remember this", "store this to [project]"

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| project | string | yes | — | Project ID ("aido", "glpuri") |
| content | string | yes | — | What to save (AI summarizes before calling) |
| depth | int | no | 1 | 0=summary, 1=context, 2=detailed, 3=full |
| tags | string[] | no | [] | Categorization tags |

**Behaviors:**
- If project doesn't exist → create with status='active'
- Update project.updated_at on every save
- Return confirmation with memory ID

**Tool description for LLM:**
> "Save important information to a project's memory. Before calling, summarize the relevant conversation into key decisions, specifications, and open questions. Do NOT save raw conversation — distill into structured, reusable context."

### 8.2 `muninn_recall` — Load project context

**Trigger:** Session start, user mentions a project, user asks "what's the status of X"

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| project | string | no | null | Specific project. If null → all active projects |
| depth | int | no | 1 | 0=summaries, 1=context, 2=detailed, 3=full |
| max_chars | int | no | 8000 | Character budget (~2000 tokens). Truncate deeper depths first |
| tags | string[] | no | null | Filter by specific tags |

**Behaviors:**
- project=null → load ONLY active projects (not paused/idea/archived)
- Sort memories by updated_at (newest first within each depth)
- Respect max_chars budget by cutting deeper depths first (character-based, not token-based — honest about not having a tokenizer)
- Include GitHub code state if repo linked and synced (Phase 2)

**Depth aliases** (for human-facing interfaces):
| Depth | Alias | Content |
|-------|-------|---------|
| 0 | summary | One-liner per project |
| 1 | context | Key decisions + current state |
| 2 | detailed | Specs, API schemas, design docs |
| 3 | full | Code snippets, file-level details, commit history |

**Tool description for LLM:**
> "Load project context from Muninn memory. Call this at session start or when user mentions a project. If no project specified, loads all active projects at depth 0-1. This gives context without re-explanation."

### 8.3 `muninn_status` — Projects overview

**Trigger:** "What are my projects?", "Show me everything", "What am I working on?"

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| (none) | — | — | — | — |

**Returns:** All projects with status, last updated, memory count, freshness indicator.

```
🟢 active — recently updated
🟡 active — stale (>1 week since last update)
⏸️ paused
💤 idea
📦 archived
```

### 8.4 `muninn_manage` — Project & memory management

**Trigger:** Change project status, delete memories, update project info

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| action | string | yes | — | "set_status" / "delete_memory" / "update_memory" / "update_project" / "create_project" |
| project | string | yes | — | Project ID |
| status | string | conditional | — | For set_status: "active" / "paused" / "idea" / "archived" |
| memory_id | string | conditional | — | For delete_memory |
| field | string | conditional | — | For update_project: "summary" / "github_repo" / "name" |
| value | string | conditional | — | For update_project |

### 8.5 `muninn_search` — Search memories

**Trigger:** "What did I save about gamification?", "Find memories about auth", "Search for API decisions"

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| query | string | yes | — | Free-text search query |
| project | string | no | null | Limit search to specific project |
| tags | string[] | no | null | Filter by tags |

**Behaviors:**
- Uses FTS5 full-text search (Porter stemming) for content matching
- Optionally filters by project and/or tags
- Returns matching memories with project name, depth, tags, and snippet with highlighted matches
- Excludes superseded memories by default
- Sorted by relevance (FTS5 rank), then by updated_at

**Tool description for LLM:**
> "Search across all project memories by keyword. Use when the user asks about a specific topic across projects, or wants to find a previously saved memory. Returns matching memories with context."

**Why this is Phase 1:** FTS5 is already in the schema. Without search, users cannot find specific memories among dozens — they must recall everything and hope the LLM finds it. This is the difference between a structured memory tool and a dumb key-value store.

### 8.6 `muninn_sync` — GitHub repo sync (Phase 2)

**Trigger:** User asks about code state, or periodic refresh

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| project | string | yes | — | Project with linked github_repo |

**Behaviors:**
- Fetch recent 5 commits (messages + changed files)
- Fetch open issues/PRs
- Save as memories with source='github', auto-supersede previous github memories

---

## 10. Memory System Design

### Depth system

```
Depth 0 — Summary (always loaded)
  "AIDO: AI startup job platform solving the doom loop in recruiting"

Depth 1 — Context (default recall)
  "Target: 398 AI companies. Stack: Next.js + Supabase.
   Competitive analysis: 7/15 companies done."

Depth 2 — Detailed
  "Company scoring algorithm: weight by funding stage (0.3),
   team size (0.2), tech stack match (0.3), culture signals (0.2)."

Depth 3 — Full
  "Supabase RLS policy: companies visible to authenticated users only.
   File: src/lib/supabase/policies.sql lines 15-42."
```

### Character budget logic

Token counting requires a tokenizer dependency (tiktoken). Instead, we use character-based budgets with a ~4 chars/token heuristic. This is honest and predictable.

| Depth | Chars budget | ~Tokens | Use case |
|-------|-------------|---------|----------|
| 0-1 (default) | ~8,000 | ~2,000 | Session start, quick context |
| 0-2 (detailed) | ~20,000 | ~5,000 | Deep dive into one project |
| 0-3 (full) | ~40,000 | ~10,000 | Full project dump |

**Truncation algorithm:**
1. Collect all non-superseded memories up to requested depth
2. Sort: depth ASC (summaries first), then updated_at DESC (newest first within depth)
3. Accumulate until max_chars reached
4. Cut from the bottom (deepest + oldest dropped first)
5. If multiple active projects and no specific project requested, divide budget proportionally by memory count

### Project lifecycle states

```
active  → paused → active  (resume)
active  → archived        (done/abandoned)
idea    → active          (start building)
idea    → archived        (decided not to pursue)

Only 'active' projects auto-load in muninn_recall().
All others require explicit project name to access.
```

### Supersede chain (memory versioning)

Instead of hard delete, old memories point to their replacement via `superseded_by`. This keeps decision history traceable while keeping recall clean.

**Query behavior:**
- `muninn_recall` and `muninn_search` exclude memories where `superseded_by IS NOT NULL`
- Only the latest (non-superseded) version of a memory is returned
- No recursive CTE needed — single WHERE clause is sufficient since we only care about "is this memory current?"
- `muninn_manage(action="delete_memory")` sets `superseded_by` to a sentinel value `'_deleted'` rather than hard deleting
- Full chain history is available via future dashboard (Phase 2), not exposed in MCP tools

---

## 11. Development Phases

### Phase 1: Core — "saves and recalls" (Weekend MVP)

**Scope:** Phase 1 supports **stdio transport** — Claude Desktop, Claude Code, Cursor, and Codex. Claude Desktop already supports stdio MCP servers, so the core use case ("brainstorm in Claude Desktop → code in Claude Code with full context") works from day 1. Claude Web/Mobile and ChatGPT require Streamable HTTP (Phase 2).

**Day 1 (~5 hours):**
- [x] Project scaffolding: git init, pyproject.toml, directory structure, .gitignore
- [x] models.py — Project, Memory dataclasses
- [x] store.py — SQLite init (WAL mode, busy_timeout), CRUD, FTS5 with sync triggers, schema migration
- [x] tools.py — muninn_save, muninn_recall, muninn_search, muninn_status, muninn_manage
- [x] server.py — FastMCP stdio server entry point
- [x] test_store.py — CRUD operations, FTS sync, concurrent access, supersede chain
- [x] Smoke test: save a memory, recall it from Claude Code

**Day 2 (~5 hours):**
- [x] formatter.py — depth-aware memory formatting for LLM context
- [x] Project status filtering in recall (active only by default)
- [x] Character budget truncation in recall
- [x] test_tools.py — tool parameter validation, edge cases
- [x] Seed data: register own projects (ouri-app via Claude Desktop)
- [ ] pyproject.toml finalize + local `uvx` test
- [x] CLAUDE.md for the project itself
- [x] Begin dogfooding

**Post-MVP iteration (same weekend):**
- [x] Depth guidance in tool docstrings + server instructions
- [x] Universal depth semantics ("What is this?" / "To continue" / "To go deeper" / "Just in case")
- [x] `update_memory` action in muninn_manage
- [x] Character usage stats in recall response footer
- [x] `Literal[...]` enum for action parameter (Claude Desktop couldn't discover actions without it)
- [x] Memory IDs in recall/search output (needed for delete/update)
- [x] Prefix ID matching in delete_memory/update_memory (short IDs from save now work)
- [x] 87 tests passing

**Actual time:** ~8 hours across 2 days. Faster than estimated due to AI-assisted implementation.

**Success criteria — all met:**
- ✅ `muninn_recall("ouri-app")` returns useful context in Claude Desktop without any copy-paste
- ✅ `muninn_search(...)` finds relevant memories across projects via FTS5
- ✅ Save in Claude Desktop → recall with full depth hierarchy works seamlessly
- ✅ Delete and update memories via short IDs from Claude Desktop

### Phase 2: GitHub + Streamable HTTP + Polish (Week 2-3)

- [ ] **Streamable HTTP transport** — `muninn --transport http --port 8787`
- [ ] ngrok/Cloudflare Tunnel setup guide for Claude Web/Mobile + ChatGPT
- [ ] github_sync.py (PyGithub integration)
- [ ] muninn_sync tool
- [ ] Merge conversation + code memories in recall output
- [ ] test_formatter.py — formatter output validation
- [ ] README.md with demo GIF + pronunciation guide ("MOO-nin")
- [ ] PyPI publish (`uvx muninn-mcp` works)
- [ ] Awesome MCP Servers list submission

### Phase 3: Community + Scale (Month 2+)

- [ ] Semantic search (sqlite-vec + all-MiniLM-L6-v2)
- [ ] Docker distribution (pre-configured HTTP transport)
- [ ] GitHub Actions CI/CD for PyPI auto-publish
- [ ] Blog post: "Why I built a memory layer for AI tools"
- [ ] **Memory Control Dashboard** (React) — 상세 아래
- [ ] Cloud deployment option (Railway/Fly.io) for always-on remote access

### Dashboard — Memory Control Panel (Phase 3)

MCP 도구만으로는 메모리를 "관리"하기 어렵다. 대화 중에 "23개 메모리 목록 보여줘"는 비효율적. 시각적 패널이 필요한 작업들:

**Core Features:**

| 기능 | 설명 | 왜 필요한가 |
|------|------|-----------|
| **프로젝트 트리 뷰** | 프로젝트 → 메모리 계층 구조 시각화 | 어떤 메모리가 어디에 있는지 한눈에 |
| **상태 토글** | active/paused/idea/archived 원클릭 전환 | MCP 도구로 하면 번거로움 |
| **메모리 CRUD** | 메모리 보기, 편집, 삭제, depth 변경 | 잘못 저장된 내용 수정 |
| **Supersede 체인** | 어떤 메모리가 어떤 메모리를 대체했는지 시각화 | 의사결정 히스토리 추적 |
| **태그 필터** | 태그별 메모리 필터링/검색 | "decision" 태그만 모아보기 |
| **Freshness 뷰** | 오래된(stale) 메모리 하이라이트 | 정리해야 할 메모리 발견 |
| **Bulk 관리** | 여러 메모리 선택 → 일괄 삭제/이동/태그 | 대량 정리 |

**Tech Stack:**
- React + Vite (경량)
- Muninn 서버의 HTTP 엔드포인트를 API로 사용 (Streamable HTTP가 Phase 2에서 추가되므로)
- 로컬에서 실행 (localhost:3000 → localhost:8787)

**UI 참고:**
```
┌─ Muninn Dashboard ──────────────────────────────┐
│                                                  │
│  Projects          │  Memories (aido)             │
│  ─────────────     │  ──────────────              │
│  🟢 muninn    (15) │  [context] Scoring weights   │
│  🟢 aido      (8)  │    funding 0.3, team 0.2...  │
│  ⏸️ glpuri    (23) │    tags: decision, scoring    │
│  💤 focus-knob (3) │    2026-02-10 · depth 1       │
│  💤 ouri       (5) │                               │
│                    │  [context] Market analysis     │
│  [+ New Project]   │    398 AI companies...        │
│                    │    tags: research              │
│                    │    2026-02-08 · depth 1        │
│                    │                               │
│                    │  [detailed] API schema         │
│                    │    /companies, /scores...      │
│                    │    tags: spec, api             │
│                    │    2026-02-05 · depth 2        │
└──────────────────────────────────────────────────┘
```

**Phase 3인 이유:**
- Phase 1-2는 MCP 도구로 충분히 사용 가능 (save/recall/search/manage)
- 대시보드 없이도 dogfooding 가능
- Streamable HTTP (Phase 2)가 선행되어야 대시보드 API로 활용 가능
- 하지만 "메모리를 눈으로 보고 직접 관리"는 장기적으로 필수

---

## 12. Testing & Validation Strategy

### Level 1: Unit Tests (코드가 맞게 동작하는가)

pytest로 각 모듈을 독립적으로 검증. 테스트마다 임시 SQLite DB를 만들어서 격리 (`tmp_path` fixture).

**test_store.py (Phase 1 필수):**
- 프로젝트 CRUD (생성, 조회, 수정, 상태 변경)
- 메모리 저장 후 recall 왕복
- active만 recall, paused 제외 확인
- superseded 메모리 필터링
- FTS5 검색 (한글/영어)
- character budget 초과 시 truncation
- 동시 쓰기 (multiprocessing으로 2개 프로세스 동시 write)

**test_tools.py (Phase 1 필수):**
- 각 도구의 파라미터 검증 (필수 파라미터 누락 시 에러)
- 존재하지 않는 프로젝트 recall 시 동작
- 빈 결과 (메모리 0개) 처리
- 특수문자 포함 프로젝트 ID 처리

**test_formatter.py (Phase 2):**
- depth별 출력 포맷 검증
- 다중 프로젝트 recall 시 정렬 순서

### Level 2: MCP Protocol Test (서버가 MCP 표준대로 응답하는가)

**MCP Inspector — 공식 디버깅 도구:**
```bash
npx @modelcontextprotocol/inspector uvx muninn-mcp
```

브라우저에서 확인:
- 등록된 도구 목록 (muninn_save, recall, search, status, manage)
- 각 도구에 파라미터 입력 → 직접 호출 → 응답 JSON 확인
- 에러 케이스 (잘못된 파라미터, 없는 프로젝트)

**FastMCP 내장 테스트:**
```python
@pytest.mark.anyio
async def test_save_and_recall_roundtrip():
    save_result = await mcp.call_tool("muninn_save", {
        "project": "test", "content": "Test decision: use React"
    })
    recall_result = await mcp.call_tool("muninn_recall", {"project": "test"})
    assert "React" in recall_result
```

### Level 3: Real Client Integration (진짜 AI 도구에서 동작하는가)

구현 완료 후 수동으로 실행하는 체크리스트.

**Claude Code 연결 테스트:**
```
[ ] claude mcp add muninn -- python -m muninn.server 성공
[ ] "aido 프로젝트 만들어줘" → muninn_save 호출됨
[ ] "내 프로젝트 보여줘" → muninn_status 호출됨
[ ] "aido에 대해 알려줘" → muninn_recall 호출됨
[ ] "gamification 관련 저장한 거 찾아줘" → muninn_search 호출됨
[ ] "glpuri를 paused로 바꿔줘" → muninn_manage 호출됨
```

**Cross-tool 테스트 (Phase 1 핵심):**
```
[ ] Claude Desktop에서 save → Claude Code에서 recall → 같은 데이터 확인
[ ] Claude Code에서 save → Cursor에서 recall → 같은 데이터 확인
[ ] 두 도구 동시 실행 → 양쪽 다 정상 동작 (WAL 모드 검증)
```

**Cross-platform 테스트 (Phase 2):**
```
[ ] Streamable HTTP 서버 실행 → MCP Inspector로 연결
[ ] ngrok 터널 → Claude Web에서 연결 → save/recall 동작
[ ] 같은 터널 → ChatGPT에서 Connector 추가 → save/recall 동작
[ ] Claude Desktop (stdio) + Claude Web (HTTP) 동시 사용 → 같은 DB 공유
```

### Level 4: Dogfooding Validation (실제로 문제를 해결하는가)

1-2주간 본인이 직접 사용하며 측정.

**자동 사용 로그:**
```python
# store.py에 추가 — 도구 호출마다 기록
def log_usage(tool: str, project: str = None):
    entry = {"ts": time.time(), "tool": tool, "project": project}
    with open(DB_DIR / "usage.jsonl", "a") as f:
        f.write(json.dumps(entry) + "\n")
```

**1주일 후 로그 분석:**

| 질문 | 로그에서 확인 |
|------|-------------|
| 하루 recall 횟수 | `tool="muninn_recall"` 카운트 |
| 가장 많이 조회하는 프로젝트 | project별 그룹핑 |
| save vs recall 비율 | save가 극단적으로 적으면 저장 UX 문제 |
| search 사용 빈도 | 0이면 FTS5 구현이 불필요했던 것 |

**매일 주관 체크 (1분):**
```
[ ] 복붙 없이 작업 시작했는가?
[ ] 프로젝트 전환 시 재설명 없었는가?
[ ] recall 결과 유용도 (1-5점)
[ ] 빠진 정보가 있었는가? → 뭐가 빠졌는지 기록
```

### Level 5: Performance Benchmark (느리지 않은가)

MCP 도구 호출은 사용자가 기다리는 시간이므로 빨라야 함.

```python
def test_recall_under_100ms(store_with_seed):
    start = time.perf_counter()
    store.recall(project="aido", depth=1, max_chars=8000)
    assert time.perf_counter() - start < 0.1

def test_search_under_200ms(store_with_seed):
    start = time.perf_counter()
    store.search(query="gamification")
    assert time.perf_counter() - start < 0.2

def test_save_under_50ms(store_with_seed):
    start = time.perf_counter()
    store.save(project="aido", content="Test", depth=1, tags=["test"])
    assert time.perf_counter() - start < 0.05
```

5개 프로젝트 x 수백 개 메모리 규모에서 SQLite는 충분. 벤치마크 결과는 README에 활용.

### 테스트 실행 타이밍

| 순서 | 레벨 | 무엇을 증명 | 언제 |
|------|------|-----------|------|
| 1 | Unit (L1) | 코드 정확성 | 구현과 동시에 |
| 2 | MCP Inspector (L2) | 프로토콜 준수 | 서버 완성 직후 |
| 3 | Claude Code 연결 (L3) | 실제 동작 | Day 1 마무리 |
| 4 | Cross-tool (L3) | 크로스툴 증명 | Day 2 |
| 5 | Dogfooding (L4) | 실용성 증명 | Week 1-2 |
| 6 | Performance (L5) | 속도 증명 | Phase 1 완료 후 |

---

## 13. Success Metrics

### Dogfooding metrics (Week 1-2)

| Metric | Target | Note |
|--------|--------|------|
| Sessions where Muninn avoids re-explanation | > 80% | Within stdio clients (Claude Code, Cursor, Codex) |
| Average context setup time per session | < 5 sec (was ~3 min) | |
| Tokens wasted on re-explanation per session | ~0 (was ~2000) | |
| Cross-tool context transfers without copy-paste | 100% | Phase 1: Claude Desktop + Claude Code + Cursor + Codex. Phase 2: + Claude Web/Mobile + ChatGPT |

### Community metrics (Month 1-3)

| Metric | Target |
|--------|--------|
| GitHub stars | 500+ (month 3) |
| PyPI weekly downloads | 100+ |
| Awesome MCP Servers listed | Yes |
| HN/Reddit frontpage post | 1+ |

### Stretch goals

| Metric | Target |
|--------|--------|
| GitHub stars | 1,200+ (month 6) |
| Community contributors | 5+ |
| AI company interview/contact | 1+ |

---

## 14. Competitive Landscape

### Three-layer market structure

**Layer 1: "Memory for your app's users" (B2B)**
- Mem0 ($24M Series A) — market leader, 186M API calls/quarter
- Zep ($2.3M) — temporal knowledge graphs, enterprise
- Supermemory ($2.6M seed) — speed-first, multimodal

**Layer 2: "Remember me within this platform" (Built-in)**
- ChatGPT Memory — auto-captures, single platform, ~1,200 word cap
- Claude Memory — on-demand, project-scoped, no cross-tool sync
- Gemini — most cautious, Google Workspace integration

**Layer 3: "Remember me across all my tools" (Cross-tool personal) ← Muninn's layer**
- Nowledge Mem (alpha, waitlist) — 13+ platforms, graph-based, auto-capture
- Mem0 OpenMemory MCP — coding tools only
- Basic Memory (bootstrapped) — markdown files, Claude-centric

### Muninn vs Nowledge Mem (closest competitor)

| | Nowledge Mem | Muninn |
|---|---|---|
| Cross-tool memory | 13+ platforms | Same goal |
| Graph-based | Yes | Future consideration |
| Local-first | Yes | Yes |
| GitHub repo integration | No (conversation-only) | Yes (code as living memory) |
| Project-level depth | No (flat) | Yes (L0-L3 progressive) |
| Token budget adaptation | No | Yes (per-client) |
| Project lifecycle | No | Yes (active/paused/idea/archived) |
| Memory curation | AI auto-captures | Human selects, AI organizes |
| Status | Alpha (waitlist) | In development |

---

## 15. Open Questions & Future Directions

### Open for Phase 2+

| Question | Current stance | Future direction |
|----------|---------------|-----------------|
| Hybrid curation (AI suggests, human approves) | Manual only in v1 | Worth exploring when usage patterns are clear |
| Semantic search | FTS5 + tags in v1 | sqlite-vec + MiniLM when tag search proves insufficient |
| Auto-recall on session start | Requires user/AI to call | CLAUDE.md instruction or MCP resources. Claude Desktop can use project instructions |
| Multi-user support | Single user | Out of scope unless demand appears |
| Cloud sync | Local only | Optional self-hosted, not SaaS |
| Memory conflict resolution | Last-write-wins | Supersede chain tracks history |

### Known risks

- MCP protocol changes could break client compatibility
- Claude App Remote MCP availability timeline unclear
- ChatGPT Actions MCP support is not guaranteed
- Small target market limits growth ceiling

---

## 16. Decision Log

Decisions made during design phase. Each entry records the debate and rationale.

| # | Decision | Alternatives considered | Rationale |
|---|----------|------------------------|-----------|
| D1 | "Human selects, AI organizes" | Full auto-capture (Nowledge Mem style) | Auto-capture = noise. 20 curated > 100 noisy. $0 LLM cost. Phase 1 simplicity. |
| D2 | Project lifecycle states | No lifecycle (flat list) | Solves the "글뿌리 problem" — paused projects don't pollute active context |
| D3 | Two memory sources (conversation + code) | Conversation only | Builders' truth is split between decisions (chat) and state (code). Neither alone is complete |
| D4 | Depth-based progressive loading | Load everything / load nothing | Token efficiency. Always starts light (~500 tokens), goes deeper on demand |
| D5 | Build custom vs use Mem0 + GitHub MCP | Combine existing tools | No existing tool provides "save to project X at depth 1" — that's the core function |
| D6 | Python over TypeScript | TypeScript (better npm distribution) | MCP Python SDK most mature, SQLite built-in, sentence-transformers native, uvx distribution |
| D7 | Distribution as open-source | Personal tool only | Growing target market, portfolio value, near-zero downside |
| D8 | Name "Muninn" | mem-based names, technical names | Norse mythology, zero conflicts, built-in brand story, starts with M |
| D9 | FastMCP over low-level Server | Low-level mcp.server | FastMCP: decorator-based, auto schema from type hints, much less boilerplate |
| D10 | mcp >= 1.25, < 2 | mcp >= 1.0.0 (from original spec) | v2 is pre-alpha with breaking changes. Pin to stable v1.x branch |
| D11 | Tags as junction table | JSON TEXT column | JSON in TEXT makes FTS index brackets/quotes, requires json_each() for queries. Junction table = clean SQL, proper indexing |
| D12 | Character budget (max_chars) | Token budget (max_tokens) | No tokenizer in tech stack. Characters with ~4 chars/token heuristic is honest and predictable. Avoids tiktoken dependency |
| D13 | WAL mode + busy_timeout | No concurrency strategy | stdio = each client spawns own process. Multiple processes hitting one SQLite file. WAL + 5s timeout handles this cleanly |
| D14 | muninn_search in Phase 1 | Phase 2 (deferred) | FTS5 already in schema. Without search, users can't find specific memories — must recall everything. Minimal extra implementation |
| D15 | Tests in Phase 1 | Phase 2 (deferred) | Data persistence tool without tests is a liability. test_store.py (CRUD, FTS sync, concurrent access) is non-negotiable |
| D16 | XDG data directory (~/.local/share/muninn/) | Unspecified | Data product needs explicit, standard data location. XDG is the convention. MUNINN_DB_PATH env var for override |
| D17 | schema_version table | No migration strategy | Phase 2 will modify schema. Without versioned migrations, Phase 2 becomes a rewrite. Simple version table + linear migrations |
| D18 | Claude Desktop in Phase 1 | Phase 3 (was "Claude App") | Claude Desktop already supports stdio MCP. Zero code change needed — config file only. Enables core brainstorm→code scenario in Phase 1 |
| D19 | Streamable HTTP in Phase 2 | Phase 3 (was HTTP/SSE) | ChatGPT and Claude Web/Mobile already support remote MCP via Streamable HTTP. FastMCP supports it natively. SSE is deprecated — skip it |
| D20 | Streamable HTTP over SSE | SSE transport | MCP spec deprecated SSE in favor of Streamable HTTP (March 2025). Both Claude and ChatGPT support Streamable HTTP. No reason to implement the deprecated option |

---

## 17. Changelog

### 2026-02-24 — Phase 1 Complete (v0.5)

- **Phase 1 marked complete** — all MVP features implemented and tested
- **6 commits**, 1,376 lines source + 1,126 lines tests, 87 tests passing
- **Post-MVP iteration** added during dogfooding:
  - Depth guidance in docstrings (Claude was ignoring depth without it)
  - Universal depth semantics (works for any project type, not just apps)
  - `update_memory` action added to `muninn_manage`
  - Character usage stats footer in recall output
  - `Literal[...]` enum on action parameter (critical for Claude Desktop discovery)
  - Memory IDs shown in recall/search output
  - Prefix ID matching for delete/update (6-8 char short IDs work)
- **Schema fix**: removed FK on `superseded_by` (incompatible with `'_deleted'` sentinel)
- **Key learning**: LLM tool use depends heavily on JSON schema quality. `str` → `Literal[...]` was the difference between Claude Desktop using or ignoring actions
- **Updated manage tool spec** to include `update_memory` action
- **Claude Desktop verified**: save, recall, search, status, delete, update all working
- **MCP platform compatibility table** researched: Claude iOS/Web need HTTP transport (Phase 2), ChatGPT Mac app has no MCP support yet

### 2026-02-23 — Success Scenarios & Testing Strategy (v0.4)

- **Added Section 3: Success Scenarios (Before/After/Wow)** — 5개 성공 시나리오 정의:
  1. 브레인스토밍 → 코드 끊김 없는 연결
  2. GitHub 코드 상태 + 대화 결정사항 통합
  3. 과거 의사결정 즉시 검색/복귀
  4. 불필요한 프로젝트 맥락 오염 방지
  5. 어떤 도구에서든 프로젝트 전체 현황 조회
- **Added Section 12: Testing & Validation Strategy** — 5단계 검증:
  - L1: Unit tests (pytest, 임시 DB 격리)
  - L2: MCP Inspector + FastMCP 프로토콜 테스트
  - L3: Real client integration 체크리스트 (Claude Code, Desktop, cross-tool)
  - L4: Dogfooding 사용 로그 + 주관 체크리스트
  - L5: Performance benchmark (recall <100ms, search <200ms, save <50ms)
- Section numbering fixed (1-17)

### 2026-02-23 — Transport strategy update (v0.3)

Updated based on MCP support research across Claude and ChatGPT platforms:

- **Claude Desktop added to Phase 1** — already supports stdio, zero code change needed. Core "brainstorm → code" scenario now works in Phase 1
- **Streamable HTTP moved to Phase 2** (was Phase 3) — both ChatGPT and Claude Web/Mobile already support it. FastMCP has native support. Enables true cross-tool memory much sooner
- **SSE transport dropped** — deprecated by MCP spec in favor of Streamable HTTP. No reason to implement
- **Architecture diagram updated** — shows Phase 1 (stdio) and Phase 2 (Streamable HTTP) clients separately
- **Client configuration examples added** — Claude Desktop, Claude Code, Claude Web/Mobile, ChatGPT
- **Phase 3 refocused** — community, scale, dashboard (no longer transport work)
- **Added decisions D18-D20** to decision log

### 2026-02-23 — Post-review update (v0.2)

Incorporated critical self-review feedback:

- **Added `muninn_search` tool** to Phase 1 scope (FTS5 already in schema, essential for finding specific memories)
- **Added concurrent access strategy** — WAL mode + busy_timeout=5000 for multi-client SQLite access
- **Changed tags from JSON TEXT to junction table** (`memory_tags`) for clean queries and proper indexing
- **Changed `max_tokens` to `max_chars`** — honest about not having a tokenizer, character-based with ~4 chars/token heuristic
- **Added FTS5 sync triggers** (INSERT/UPDATE/DELETE) to keep search index consistent
- **Added `schema_version` table** for future migrations without rewrites
- **Added data location spec** — `~/.local/share/muninn/muninn.db` (XDG standard), `MUNINN_DB_PATH` override
- **Moved tests to Phase 1** — test_store.py and test_tools.py are non-negotiable for a data persistence tool
- **Added supersede chain query behavior** — WHERE clause filtering, `_deleted` sentinel
- **Added CHECK constraints** to schema (status, depth, source)
- **Added Phase 1 transport limitation disclaimer** — stdio only = Claude Code + Cursor + Codex
- **Updated time estimate** — 10-12 hours realistic (was 8)
- **Added 7 new decisions** to decision log (D11-D17)
- **Added truncation algorithm** — depth ASC, updated_at DESC, cut from bottom

### 2026-02-23 — Initial PRD (v0.1)

- Created from design discussion log and technical spec
- Consolidated all 8 design decisions with rationale
- Added user scenarios for all 5 target AI tools (Claude App, Claude Code, ChatGPT, Codex, Cursor)
- Updated MCP SDK dependency to v1.25+ (was v1.0.0)
- Added FastMCP as implementation approach (was low-level Server)
- Added depth aliases (summary/context/detailed/full)
- Added success metrics and competitive landscape
- Added open questions and future directions section

---

*This document is the single source of truth for Muninn's product direction. Update it as implementation reveals new insights.*
