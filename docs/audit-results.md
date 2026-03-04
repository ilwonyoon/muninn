# Muninn 전수 조사 결과

> 조사일: 2026-03-04
> 방법: 4개 축 병렬 Codex 감사 (read-only)
> 계획 문서: [audit-plan.md](./audit-plan.md)

---

## 총괄 요약

| 축 | CRITICAL | HIGH | MEDIUM | LOW |
|---|---|---|---|---|
| 안정성 | 2 | 4 | 4 | 2 |
| 보안 | 1 | 2 | 4 | 2 |
| 퍼포먼스 | 1 | 5 | 8 | 3 |
| **합계** | **4** | **11** | **16** | **7** |

SQL injection, XSS/CSRF — 취약점 미발견 (parameterized query 사용, 쿠키 기반 auth 없음).
의존성 CVE — `npm audit`/`pip-audit` 환경 제약으로 자동 스캔 불가. locked 버전 수동 확인 시 알려진 취약점 없음.

---

## 1. 안정성 (Stability & Reliability)

### CRITICAL

**S-1. 스키마 마이그레이션 건너뛸 수 있음**
- 파일: `store.py:233-236`
- `schema_version` 테이블이 없을 때 마이그레이션이 스킵되어 데이터 무결성 위험
- Fix: 마이그레이션 실패 시 hard error로 서버 시작 차단

**S-2. 다중 SQL문 쓰기에 rollback 없음**
- 파일: `store.py` 전반 (쓰기 메서드)
- multi-statement write 중간 실패 시 partial commit 가능
- Fix: 쓰기 경로에 `BEGIN/COMMIT/ROLLBACK` 트랜잭션 래핑

### HIGH

**S-3. 마이그레이션 에러 swallow**
- 파일: `store.py` 마이그레이션 경로
- 에러를 로깅만 하고 계속 진행 → 조용한 데이터 불일치
- Fix: 실패 시 startup abort

**S-4. commit-before-sync 데이터 유실 가능**
- 파일: `store.py` 쓰기 메서드
- 로컬 commit 후 Turso sync 실패 시 로컬에만 데이터 존재
- Fix: 재시도 + 실패 알림 메커니즘

**S-5. 읽기 가용성이 sync에 의존**
- 파일: `store.py` 읽기 메서드
- `_sync_if_needed()` 실패 시 stale data 반환 또는 에러
- Fix: graceful degradation + staleness indicator

**S-6. API 에러 매핑 불일치**
- 파일: `api.py`, `web/src/app/api/*/route.ts`
- 내부 에러가 그대로 클라이언트에 전달
- Fix: 표준 에러 포맷 + 내부 상세 제거

### MEDIUM

**S-7.** FTS5 트리거 부분 실패 시 불일치
**S-8.** 동시 쓰기 시 WAL busy_timeout 부족 가능성
**S-9.** 대시보드 API 에러 응답 일관성 부족
**S-10.** Turso 토큰 만료 시 복구 경로 없음

### LOW

**S-11.** MCP 도구 함수에서 예외 삼키고 빈 문자열 반환 (디버깅 어려움)
**S-12.** 서버 재시작 없이 instructions.md 변경 반영 불가

---

## 2. 보안 (Security)

### CRITICAL

**SEC-1. Python `/api/*` 라우트 인증 없음** [A01 Broken Access Control]
- 파일: `auth.py:30-31`, `server.py:231/264/274`
- Bearer auth middleware가 `/api/*`를 명시적으로 우회
- 공격: localhost 외부 노출 시 데이터 전체 읽기/수정/삭제 가능
- Fix: `/api/*`에도 동일 auth middleware 적용 또는 loopback-only 바인딩 강제

### HIGH

**SEC-2. Dashboard API key가 `NEXT_PUBLIC_*`으로 브라우저 노출** [A02 Cryptographic Failures]
- 파일: `web/src/lib/api.ts:19`, `web/src/middleware.ts:4`
- 클라이언트 JS/네트워크에서 key 추출 가능
- Fix: 서버사이드 세션/쿠키 auth로 전환, `NEXT_PUBLIC_*` 제거

**SEC-3. OAuth PIN brute-force 가능** [A07 Authentication Failures]
- 파일: `server.py:185`, `oauth_login.py:24`, `oauth_provider.py:518`
- rate limit/lockout/감사 로그 없음
- Fix: strict rate limiting + lockout + high-entropy secret

### MEDIUM

**SEC-4.** OAuth redirect에서 `state` 미인코딩 (parameter injection) [A03 Injection]
- 파일: `oauth_login.py:46/48/52`
- Fix: `urllib.parse.urlencode` 사용

**SEC-5.** OAuth token 평문 저장 + refresh 시 scope escalation 가능 [A02]
- 파일: `oauth_provider.py:64/389/390`
- Fix: token hash 저장, `requested_scopes ⊆ original_scopes` 강제

**SEC-6.** 입력 크기 검증 부족 (DoS/storage abuse) [A04 Insecure Design]
- 파일: `models.py:91/97`, `api.py:146/260`
- Fix: max content length, max tag count/length, request body limit

**SEC-7.** `MUNINN_API_KEY` 미설정 시 middleware fail-open [A05 Misconfiguration]
- 파일: `web/src/middleware.ts:6`
- Fix: dev mode 외에는 fail-closed, 시작 시 필수 env var 검증

### LOW

**SEC-8.** 에러 문자열이 클라이언트에 그대로 전달 (내부 정보 노출) [A05]
- 파일: `tools.py:117`, `web/src/app/api/stats/route.ts:10`, `web/src/app/api/memories/route.ts:30`

**SEC-9.** CORS 정책 미설정 (Python dashboard API) [A05]
- 파일: `server.py:196/201`

**검증 완료 (이슈 없음)**
- SQL injection: `store.py`, `db.ts` 모든 쿼리 parameterized
- XSS/CSRF: markdown 렌더링 경로 안전, 쿠키 기반 auth 없음
- 의존성 CVE: locked 버전 (`next 16.1.6`, `mcp 1.26.0`, `starlette 0.52.1` 등) 수동 확인 시 활성 취약점 없음

---

## 3. 퍼포먼스 (Performance)

> 검증 환경: `~/.local/share/muninn/muninn.db` (11 projects, 0 memories). `EXPLAIN QUERY PLAN` 기반 분석.

### CRITICAL

**P-1. recall이 전체 결과셋 로드 후 truncation**
- 파일: `store.py:763/783`, `db.ts:376/388`
- `SELECT *` 후 Python/TS에서 `max_chars` 적용 → 대규모 데이터에서 메모리 폭발
- Fix: SQL 레벨 pagination/cursor, 필요한 row만 fetch
- 개선 폭: ~70-95% 메모리/쿼리 비용 감소

### HIGH

**P-2. Dashboard API pagination 없음**
- 파일: `api.py:145/156`, `web/src/app/api/projects/[id]/memories/route.ts:21/33`
- `max_chars` 500k까지 한 번에 반환
- Fix: cursor pagination + lightweight list projection
- 개선 폭: payload >80% 감소

**P-3. Supersede chain N+1 쿼리**
- 파일: `store.py:1058/1076`, `db.ts:594/611`
- per-node loop으로 개별 쿼리
- Fix: recursive CTE (단일 쿼리)
- 개선 폭: 60-95% latency 감소 (remote DB)

**P-4. Turso sync amplification (batch supersede)**
- 파일: `github_sync.py:250`, `store.py:277/281`
- 건당 commit + sync → k개 supersede 시 k+1회 sync
- Fix: 트랜잭션 래핑 후 1회 sync
- 개선 폭: ~90%+ sync overhead 감소

**P-5. 프로젝트 리스트 중복 fetch**
- 파일: `web/src/lib/store.ts:15`, `sidebar.tsx:133`, `page.tsx:30`, `search/page.tsx:40`, `command-palette.tsx:38`
- sidebar/page/palette에서 각각 `/api/projects` 호출
- Fix: 캐시/TTL 중앙화 (SWR/React Query 또는 zustand timestamp guard)
- 개선 폭: 2-4x API 호출 감소

**P-6. 프로젝트 상세 refetch fan-out**
- 파일: `use-project-memories.ts:34`, `project-progress-view.tsx:24`, `memory-detail-panel.tsx:53/97`
- 한 UI 액션에 5-6개 overlapping fetch
- Fix: normalized state + targeted invalidation
- 개선 폭: 40-70% API chatter 감소

### MEDIUM

**P-7.** `list_projects` correlated subquery + table scan ordering
- 파일: `store.py:507`, `db.ts:140`
- Fix: `LEFT JOIN GROUP BY` + sort/filter index → 2-10x 개선

**P-8.** 메모리 리스트 composite index 누락
- 파일: `store.py:765`, `db.ts:376`
- Fix: `(project_id, superseded_by, updated_at DESC)` index → 30-80% 개선

**P-9.** 프로젝트 문서 검색 full scan (`LOWER(summary) LIKE '%...%'`)
- 파일: `store.py:1113/1114`
- Fix: FTS5 table for project summaries

**P-10.** FTS search temp-sort + post-filter 비용
- 파일: `store.py:827/852`, `db.ts:654/672`
- Fix: two-phase retrieval → 20-60% 개선

**P-11.** TS layer write 시 tag INSERT 루프 (N round-trips)
- 파일: `db.ts:474/486/533/553`
- Fix: batch statements/transaction → 2-6 round-trip 절감

**P-12.** API route 불필요한 existence-check 쿼리
- 파일: `web/src/app/api/projects/[id]/memories/route.ts:11`, `memories/route.ts:17`
- Fix: write path에서 existence 강제 → per-request 1 query 절감

**P-13.** Command palette + markdown renderer 번들 크기
- 파일: `providers.tsx:10`, `command-palette.tsx:5`, `markdown-content.tsx:3`
- Fix: lazy-load → 초기 JS 수십~수백 KB 절감

**P-14.** Summary highlight에서 반복 markdown parsing
- 파일: `project-document-view.tsx:132/146`
- Fix: 단일 markdown pass + inline highlighting → 30-70% CPU 감소

### LOW

**P-15.** Formatter 대용량 중간 문자열 할당 (`formatter.py:118/129`) → stream/chunk
**P-16.** Snippet extraction 전체 lowercase 복사 (`formatter.py:75/77`) → bounded window search
**P-17.** Startup schema check + 초기 Turso sync (`store.py:233/236`, `server.py:294`) → deferred sync
**P-18.** Tool usage logging 동기 파일 append (`tools.py:54/66`) → buffered/async

---

## 4. 제품 가치 (Product Value)

### Must-have (즉시)

**V-1. Document overwrite 위험**
- 전체 교체 방식 → 동시 편집 시 데이터 유실
- 개선: optimistic concurrency (version check) + append-only revision history

**V-2. MCP instructions 효과 부족**
- 트리거 모호 ("session end" 등), 클라이언트별 행동 차이
- 개선: deterministic trigger matrix + positive/negative 예시

**V-3. MCP search가 FTS5가 아님**
- `muninn_search`는 `LIKE` over summaries (`store.py:1100`), API search는 FTS5
- multi-term/operator 패턴 실패 (항상 quote-wrapped phrase)
- 개선: summaries + memories 통합 FTS5 검색

**V-4. 멀티 클라이언트 일관성**
- Last-write-wins, ID 정규화 없음, dashboard ↔ MCP split-brain 가능
- 개선: canonical project ID policy + version check

**V-5. 대시보드 UX 결함**
- 깨진 네비게이션 (command palette → 존재하지 않는 memory route)
- 미구현 shortcuts (settings 페이지에 표시만)
- Instructions UI가 Turso DB에 쓰는데 MCP는 파일에서 읽음
- 개선: 네비게이션 수정 + instruction 단일 소스 통합

### High (조기)

**V-6. GitHub sync가 MCP recall에 노출 안됨**
- sync 데이터가 memories에만 저장, document recall/search에서 미표출
- `github_repo` 설정도 MCP tools로 불가
- 개선: MCP tools에 `github_repo` 관리 + recall 경로에 sync 데이터 주입

**V-7. 온보딩 문서 drift**
- README 내용과 실제 동작 불일치 (tool params, semantic search 주장, 아키텍처 설명)
- 개선: README를 현재 동작에 맞게 재작성 + 5분 quickstart 스크립트

**V-8. Power user 기능 부족**
- provenance 메타데이터 없음 (saved_by_client, source)
- dedupe/similarity guardrail 없음
- 개선: provenance 필드 + 중복 검사

### Medium (계획적)

**V-9. 데이터 모델 확장성**
- `embedding` 컬럼 미사용, summary revision 1개만 보관, category 미활용
- 개선: full revision history + project aliases table

**V-10. Instructions 이원화**
- `~/.local/share/muninn/instructions.md` (MCP) vs Turso DB instructions table (dashboard)
- 개선: 단일 소스 + reload status endpoint

---

## Over-engineering 판정

개인용 MCP 서버 맥락에서 투자 대비 가치가 낮은 항목. 이슈 목록에는 남기되 로드맵에서 제외.

| ID | 항목 | 이유 |
|---|---|---|
| D-3 | 멀티 클라이언트 CRDT merge | 1인 사용자, last-write-wins로 충분 |
| D-5 | OAuth rate limit + token hash | 로컬/개인용, 공격 표면 극히 작음 |
| SEC-3 | OAuth PIN brute-force 방어 | 동일 |
| SEC-5 | Token 평문 → hash | 동일 |
| D-1 | Semantic search (embedding) | FTS5로 충분, embedding 인프라 과잉 |
| D-4 | 온보딩 wizard / `muninn doctor` | 사용자 본인뿐 |
| P-13 | Command palette lazy-load | 번들 최적화 우선순위 낮음 |
| P-14 | Summary highlight 반복 parsing | 체감 안 될 수준 |
| V-8 | Provenance metadata + dedupe | 1인 사용, 추적 필요성 낮음 |
| S-8 | WAL busy_timeout 확대 | stdio single-threaded, 경합 거의 없음 |

---

## 실행 스펙 (Codex 위임용)

### Phase 1: 안정성 + 보안 기반

---

#### A-1. `/api/*` auth 적용 [SEC-1]

**현재 코드:**
`auth.py:30-32` — `request.url.path.startswith("/api/")` 이면 무조건 bypass.

**변경 스펙:**
- `src/muninn/auth.py`: `/api/` prefix bypass 제거. `/api/*` 요청에도 Bearer token 검증 수행.
- 단, `MUNINN_API_KEY` 환경변수가 없으면 (로컬 개발) bypass 유지. 있으면 `x-api-key` 헤더 또는 `Authorization: Bearer` 검증.
- OAuth 관련 경로 (`/oauth/*`)와 정적 리소스는 기존대로 bypass.

**수정 파일:** `src/muninn/auth.py`
**건드리지 말 것:** `server.py`의 route mount, `api.py`의 엔드포인트 로직

**수용 기준:**
- `MUNINN_API_KEY` 설정 시: `/api/projects` 호출에 유효 key 없으면 401
- `MUNINN_API_KEY` 미설정 시: 기존처럼 모든 `/api/*` 접근 가능
- 기존 `tests/test_auth.py` 통과 + `/api/` 경로 auth 테스트 추가 (최소 2개: 401 케이스, 200 케이스)
- `.venv/bin/python -m pytest tests/ -x -q` 전체 통과

---

#### A-2. 스키마 마이그레이션 실패 시 hard error [S-1, S-3]

**현재 코드:**
`store.py:303-308` — `_run_migrations()` 내 각 ALTER 문이 try/except로 감싸여 있고, 예외 시 `pass`로 무시.
`store.py:79-82` — 초기 `schema_version` INSERT가 version 6으로 하드코딩 (현재 최신은 8).

**변경 스펙:**
- `_run_migrations()` 내 `except: pass` 패턴 제거. ALTER 문 실패 시 (이미 존재하는 컬럼 제외) 예외를 상위로 전파.
- "column already exists" 에러만 무시 (SQLite 에러 메시지로 판별). 그 외 에러는 raise.
- `__init__`에서 `_run_migrations()` 호출을 try/except로 감싸고, 실패 시 `RuntimeError("Schema migration failed")` raise.
- 초기 INSERT version을 현재 최신 버전(8)으로 변경.

**수정 파일:** `src/muninn/store.py` (`_run_migrations` 메서드 + `_SCHEMA_STATEMENTS`)
**건드리지 말 것:** 마이그레이션 SQL 자체의 로직, 다른 메서드

**수용 기준:**
- 정상 DB: 기존처럼 마이그레이션 통과
- 손상된 마이그레이션: `RuntimeError` 발생하여 서버 시작 차단
- `.venv/bin/python -m pytest tests/ -x -q` 전체 통과

---

#### A-3. 쓰기 경로 트랜잭션 래핑 [S-2]

**현재 코드:**
multi-statement 쓰기 메서드들이 개별 `execute()` 후 마지막에 `self._conn.commit()` 한 번만 호출. 중간 실패 시 rollback 없음.

**대상 메서드 (모두 `store.py`):**
| 메서드 | 라인 | 설명 |
|---|---|---|
| `update_project()` | 533-593 | DELETE revision + INSERT revision + UPDATE project |
| `delete_project()` | 595-634 | 4개 DELETE (tags, memories, revisions, project) |
| `save_memory()` | 661-717 | INSERT memory + N개 tag INSERT + UPDATE project |
| `update_memory()` | 912-981 | DELETE tags + INSERT tags + UPDATE memory + UPDATE project |
| `reset_data()` | 1124-1138 | 4개 DELETE/UPDATE |

**변경 스펙:**
- 위 5개 메서드에 `self._conn.execute("BEGIN")` / `self._conn.commit()` / `self._conn.rollback()` 패턴 적용.
- try/except 구조: BEGIN → 로직 → COMMIT. except에서 ROLLBACK → re-raise.
- 단일 INSERT만 하는 메서드 (`create_project`, `supersede_memory`, `delete_memory`, `clear_summary_revision`)는 현행 유지.

**수정 파일:** `src/muninn/store.py`
**건드리지 말 것:** 메서드의 비즈니스 로직, SQL 쿼리 자체, `_sync_after_write()` 호출 위치

**수용 기준:**
- 정상 경로: 기존과 동일 동작
- 중간 실패 시: 부분 커밋 없이 전체 롤백
- `.venv/bin/python -m pytest tests/ -x -q` 전체 통과

---

#### A-4. `NEXT_PUBLIC_*` API key 제거 [SEC-2]

**현재 코드:**
`web/src/lib/api.ts:19` — `process.env.NEXT_PUBLIC_MUNINN_API_KEY` 를 읽어 `x-api-key` 헤더로 전송. `NEXT_PUBLIC_*` prefix라 클라이언트 번들에 포함됨.

**변경 스펙:**
- `web/src/lib/api.ts`: `NEXT_PUBLIC_MUNINN_API_KEY` → `MUNINN_API_KEY`로 변경.
- 이 파일의 `fetchJSON()`은 Next.js API route handler에서만 호출됨 (서버사이드). 클라이언트 컴포넌트는 `/api/*` Next.js route를 통해 간접 호출. 따라서 `NEXT_PUBLIC_` prefix 불필요.
- 만약 클라이언트에서 직접 호출하는 곳이 있다면, Next.js API route를 통하도록 변경.

**수정 파일:** `web/src/lib/api.ts`
**건드리지 말 것:** `web/src/middleware.ts` (이미 `MUNINN_API_KEY` 사용), API route 로직

**수용 기준:**
- `MUNINN_API_KEY` 환경변수로 대시보드 API 인증 동작
- 브라우저 DevTools에서 API key가 노출되지 않음 (번들에 미포함)
- `cd web && npm run build` 성공

---

#### A-5. middleware fail-closed [SEC-7]

**현재 코드:**
`web/src/middleware.ts:7-8` — `MUNINN_API_KEY` 미설정 시 `NextResponse.next()` 반환 (모든 요청 허용).

**변경 스펙:**
- `NODE_ENV === "development"` 일 때만 key 없이 통과 허용.
- production에서 `MUNINN_API_KEY` 미설정 시 모든 `/api/*` 요청에 500 반환 + 에러 메시지: `"MUNINN_API_KEY not configured"`.

**수정 파일:** `web/src/middleware.ts`
**건드리지 말 것:** matcher 설정, 인증 성공/실패 로직

**수용 기준:**
- `NODE_ENV=development` + key 없음: 기존처럼 통과
- `NODE_ENV=production` + key 없음: 500 반환
- `NODE_ENV=production` + key 설정: 정상 인증 동작
- `cd web && npm run build` 성공

---

### Phase 2: 핵심 퍼포먼스

---

#### B-1. recall SQL pagination [P-1]

**현재 코드:**
`store.py:764-803` — `SELECT * FROM memories WHERE project_id IN (...) AND superseded_by IS NULL ORDER BY updated_at DESC` 로 전체 row fetch 후 Python에서 `max_chars` 예산으로 truncation. `continue`로 예산 초과 row도 전부 순회 (dropped count 집계).

**변경 스펙:**
- SQL에 `LIMIT` 추가. 초기 batch 크기 = 50 (충분히 크면서 전체 fetch 방지).
- Python 루프에서 `max_chars` 예산 소진 시 `break` (더 이상 순회 불필요).
- dropped count는 별도 COUNT 쿼리로 대체하거나, "일부 생략됨" 메시지만 표시.
- `db.ts:376-413`의 TS 쪽도 동일 패턴 적용 (LIMIT + break).

**수정 파일:** `src/muninn/store.py` (recall 메서드), `web/src/lib/db.ts` (listMemories)
**건드리지 말 것:** 반환 포맷, formatter.py, API route 시그니처

**수용 기준:**
- recall 결과가 기존과 동일 (예산 내 동일 row 반환)
- SQL에 LIMIT 존재
- `.venv/bin/python -m pytest tests/ -x -q` 전체 통과
- `cd web && npm run build` 성공

---

#### B-2. supersede chain → recursive CTE [P-3]

**현재 코드:**
`store.py:1054-1081` — BFS 루프에서 노드당 2개 쿼리 (forward: `SELECT superseded_by`, backward: `SELECT id WHERE superseded_by = ?`).
`db.ts:594-622` — 동일 패턴.

**변경 스펙:**
- Python: BFS 루프를 단일 recursive CTE로 대체.
```sql
WITH RECURSIVE chain(id) AS (
    SELECT id FROM memories WHERE id = ?
    UNION
    SELECT m.id FROM memories m JOIN chain c ON m.superseded_by = c.id
    UNION
    SELECT m.superseded_by FROM memories m JOIN chain c ON m.id = c.id
    WHERE m.superseded_by IS NOT NULL AND m.superseded_by != '_deleted'
)
SELECT DISTINCT id FROM chain
```
- 결과 ID 목록으로 한 번에 full record + tags fetch.
- TS (`db.ts`): 동일 CTE 적용.

**수정 파일:** `src/muninn/store.py` (`get_supersede_chain`), `web/src/lib/db.ts` (`getMemoryChain`)
**건드리지 말 것:** 반환 타입, chain의 정렬 순서

**수용 기준:**
- 체인 결과가 기존과 동일 (동일 ID set 반환)
- DB 쿼리 수: 체인 길이와 무관하게 2-3개 (CTE + record fetch + tags)
- `.venv/bin/python -m pytest tests/ -x -q` 전체 통과
- `cd web && npm run build` 성공

---

#### B-3. batch sync [P-4]

**현재 코드:**
`github_sync.py:250-251` — `for old_id in superseded_ids: store.supersede_memory(old_id, new_memory.id)` 루프. 각 호출이 `commit()` + `_sync_after_write()`.

**변경 스펙:**
- `store.py`에 `batch_supersede(old_ids: list[str], new_id: str)` 메서드 추가.
- 단일 트랜잭션: `UPDATE memories SET superseded_by = ?, updated_at = ? WHERE id IN (...) AND superseded_by IS NULL`.
- `commit()` 1회 + `_sync_after_write()` 1회.
- `github_sync.py`에서 루프 대신 `store.batch_supersede(superseded_ids, new_memory.id)` 호출.

**수정 파일:** `src/muninn/store.py` (새 메서드), `src/muninn/github_sync.py` (호출부)
**건드리지 말 것:** `supersede_memory()` 기존 메서드 (다른 곳에서 단건 사용), sync 로직

**수용 기준:**
- GitHub sync 시 supersede 작업이 단일 트랜잭션 + 1회 sync
- 기존 `supersede_memory()` 단건 호출은 변경 없음
- `.venv/bin/python -m pytest tests/ -x -q` 전체 통과

---

#### B-4. composite index 추가 [P-8]

**현재 코드:**
`store.py:58-60` — 개별 인덱스: `idx_memories_project_id`, `idx_memories_superseded_by`. recall 쿼리 `WHERE project_id IN (...) AND superseded_by IS NULL ORDER BY updated_at DESC`를 커버 못함.

**변경 스펙:**
- `_SCHEMA_STATEMENTS`에 추가:
```sql
CREATE INDEX IF NOT EXISTS idx_memories_recall
ON memories(project_id, superseded_by, updated_at DESC)
```
- 기존 `idx_memories_project_id`는 제거 (새 composite index가 커버).
- `idx_memories_superseded_by`는 유지 (supersede chain 등 다른 쿼리에서 사용).

**수정 파일:** `src/muninn/store.py` (`_SCHEMA_STATEMENTS`)
**건드리지 말 것:** 쿼리 로직, 마이그레이션 버전

**수용 기준:**
- `EXPLAIN QUERY PLAN`에서 recall 쿼리가 새 index 사용 (SEARCH + no TEMP B-TREE)
- `.venv/bin/python -m pytest tests/ -x -q` 전체 통과

---

#### B-5. 대시보드 fetch 중앙화 + 캐시 [P-5, P-6]

**현재 코드:**
- `web/src/lib/store.ts:15` — zustand store에 `fetchProjects()` 있지만 TTL/캐시 없음.
- `sidebar.tsx:133`, `page.tsx:30`, `search/page.tsx:40`, `command-palette.tsx:38` — 각각 `fetchProjects()` 호출.
- `use-project-memories.ts:34` — `getProject(projectId)` 별도 호출 (zustand에 이미 있는 데이터).

**변경 스펙:**
- `web/src/lib/store.ts`의 `fetchProjects()`에 TTL guard 추가: 마지막 fetch 후 5초 이내 재호출 시 캐시 반환.
```typescript
fetchProjects: async (force = false) => {
  const { lastFetchedAt } = get()
  if (!force && lastFetchedAt && Date.now() - lastFetchedAt < 5000) return
  // ... 기존 fetch 로직
  set({ projects, loading: false, lastFetchedAt: Date.now() })
}
```
- `useProjectMemories`에서 `getProject(projectId)` 대신 zustand store의 `projects.find(p => p.id === projectId)` 사용. 없으면 fallback으로 API 호출.
- 호출부(`sidebar`, `page`, `search`, `command-palette`)는 변경 불필요 (store 내부에서 throttle).

**수정 파일:** `web/src/lib/store.ts`, `web/src/lib/use-project-memories.ts`
**건드리지 말 것:** API route, db.ts, 컴포넌트 렌더 로직

**수용 기준:**
- 페이지 이동 시 `/api/projects` 호출이 5초 내 1회로 제한됨
- 프로젝트 상세 진입 시 불필요한 `getProject()` API 호출 제거
- `cd web && npm run build` 성공

---

### Phase 3: 제품 완성도

---

#### C-1. MCP search → FTS5 통합 [V-3]

**현재 코드:**
`store.py:1100-1114` — `muninn_search`가 `LOWER(summary) LIKE '%query%'`로 프로젝트 summary만 검색. API search (`store.py:814-852`)는 FTS5로 memories 검색.

**변경 스펙:**
- `search_projects()` 메서드를 FTS5 기반으로 변경. `projects_fts` FTS5 virtual table 추가 (summary 필드).
- 또는 기존 `search()` (memories FTS5)와 `search_projects()`를 합쳐서 MCP `muninn_search`가 summaries + memories 모두 검색.
- MCP search 결과에 매칭 snippet 포함.

**수정 파일:** `src/muninn/store.py`, `src/muninn/tools.py` (muninn_search)
**건드리지 말 것:** API search 엔드포인트, 대시보드 검색

**수용 기준:**
- `muninn_search("auth")` 호출 시 summary에 "auth" 포함된 프로젝트 반환
- multi-term 검색 동작 (`auth oauth` → 두 단어 모두 포함하는 결과)
- `.venv/bin/python -m pytest tests/ -x -q` 전체 통과

---

#### C-2. Document versioning [V-1]

**현재 코드:**
`store.py:567-579` — summary 업데이트 시 이전 revision 1개만 보관 (`DELETE` 후 `INSERT`).

**변경 스펙:**
- `project_summary_revisions` 테이블에서 `DELETE` 제거. INSERT만 수행하여 전체 이력 보관.
- 최대 10개 revision 유지 (초과 시 가장 오래된 것 삭제).
- 대시보드 API에 revision 목록 조회 엔드포인트 추가 (이미 `GET /api/projects/[id]/summary-revision` 존재 — 복수 반환으로 변경).

**수정 파일:** `src/muninn/store.py` (`update_project`), `web/src/lib/db.ts`, `web/src/app/api/projects/[id]/summary-revision/route.ts`
**건드리지 말 것:** MCP tools, project 모델

**수용 기준:**
- summary 10회 업데이트 후 10개 revision 조회 가능
- 11번째 업데이트 시 가장 오래된 revision 삭제
- `.venv/bin/python -m pytest tests/ -x -q` 전체 통과

---

#### C-3. 대시보드 네비게이션/shortcut 수정 [V-5]

**현재 코드:**
- `command-palette.tsx:116` — memory 결과 클릭 시 `/projects/${project_id}/${memory_id}` 라우트로 이동 (해당 route 삭제됨).
- `settings/page.tsx:64` — keyboard shortcuts 표시하지만 미구현.

**변경 스펙:**
- `command-palette.tsx`: memory 검색 결과 클릭 시 `/projects/${project_id}` 로 이동 (memory detail route 삭제되었으므로).
- `settings/page.tsx`: 미구현 shortcuts 섹션 제거 또는 "Coming soon" 표시.

**수정 파일:** `web/src/components/layout/command-palette.tsx`, `web/src/app/settings/page.tsx`
**건드리지 말 것:** command-palette의 프로젝트 검색, 다른 설정 항목

**수용 기준:**
- command palette에서 memory 결과 클릭 시 404 없이 프로젝트 페이지 이동
- `cd web && npm run build` 성공

---

#### C-4. Instruction 단일 소스 통합 [V-10]

**현재 코드:**
- MCP: `server.py:40/104` — `~/.local/share/muninn/instructions.md` 파일에서 읽음.
- Dashboard: `web/src/app/api/instructions/route.ts` — Turso DB `instructions` 테이블에서 읽기/쓰기.
- 두 소스가 독립적이라 대시보드에서 수정해도 MCP에 반영 안 됨.

**변경 스펙:**
- DB를 단일 소스로 통합. `instructions` 테이블을 canonical로 사용.
- `server.py`: instructions 로딩을 파일 대신 `store.get_instructions()` 호출로 변경.
- `store.py`: `get_instructions()`, `update_instructions()` 메서드 추가.
- 파일 기반 로딩은 fallback으로 유지 (DB에 없을 때 파일에서 읽어 DB에 seed).

**수정 파일:** `src/muninn/store.py`, `src/muninn/server.py`
**건드리지 말 것:** `web/src/app/api/instructions/route.ts` (이미 DB 사용), instruction 내용 자체

**수용 기준:**
- 대시보드에서 instruction 수정 → MCP 서버 재시작 없이 다음 호출에서 반영
- 파일만 있고 DB 비어있을 때 → 파일 내용으로 DB seed
- `.venv/bin/python -m pytest tests/ -x -q` 전체 통과

---

#### C-5. README 재작성 [V-7]

**변경 스펙:**
- README.md를 현재 동작에 맞게 재작성.
- 수정 필요 항목: tool 파라미터 (현재 document-first), "semantic search" 주장 제거, 아키텍처 설명 업데이트.
- 5분 quickstart 섹션 추가: install → config → first save/recall.

**수정 파일:** `README.md`
**건드리지 말 것:** 라이선스, 기여 가이드

**수용 기준:**
- README 내 모든 tool 설명이 실제 `tools.py` 시그니처와 일치
- "semantic search" 등 미구현 기능 주장 없음
- quickstart 따라하면 실제로 동작

---

#### C-6. GitHub sync → MCP recall 통합 [V-6]

**현재 코드:**
- `github_sync.py`: sync 결과를 memories 테이블에 저장.
- `tools.py`의 `muninn_recall`: project summary만 반환. memories (sync 포함) 미포함.

**변경 스펙:**
- `muninn_recall` 결과에 GitHub sync summary 포함. 가장 최근 sync memory의 content를 project document 아래에 append.
- `muninn_manage`에 `set_github_repo` action 추가하여 MCP에서 `github_repo` 설정 가능.

**수정 파일:** `src/muninn/tools.py`, `src/muninn/store.py` (sync 데이터 조회 메서드)
**건드리지 말 것:** `github_sync.py` 내부 로직, sync 데이터 저장 방식

**수용 기준:**
- `muninn_recall("project-x")` 결과에 최근 GitHub sync 요약 포함
- `muninn_manage(action="set_github_repo", ...)` 동작
- `.venv/bin/python -m pytest tests/ -x -q` 전체 통과

---

### Backlog (필요 시)

Over-engineering으로 분류된 항목 및 LOW 이슈. 실사용에서 문제가 되면 재평가.
