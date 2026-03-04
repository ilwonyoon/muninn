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

## 권장 액션 로드맵

### Phase 1: 안정성 + 보안 기반 (즉시)

| ID | 항목 | 관련 이슈 |
|---|---|---|
| A-1 | `/api/*` auth 적용 | SEC-1 |
| A-2 | 스키마 마이그레이션 실패 시 hard error | S-1, S-3 |
| A-3 | 쓰기 경로 트랜잭션 래핑 | S-2 |
| A-4 | `NEXT_PUBLIC_*` API key 제거 → 서버사이드 auth | SEC-2 |
| A-5 | middleware fail-closed (env var 필수) | SEC-7 |

### Phase 2: 핵심 퍼포먼스 (1-2주)

| ID | 항목 | 관련 이슈 |
|---|---|---|
| B-1 | recall SQL pagination | P-1 |
| B-2 | supersede chain → recursive CTE | P-3 |
| B-3 | batch sync (트랜잭션 1회) | P-4 |
| B-4 | composite index 추가 | P-8 |
| B-5 | 대시보드 fetch 중앙화 + 캐시 | P-5, P-6 |

### Phase 3: 제품 완성도 (2-4주)

| ID | 항목 | 관련 이슈 |
|---|---|---|
| C-1 | MCP search → FTS5 통합 | V-3 |
| C-2 | Document versioning (conflict-safe save) | V-1 |
| C-3 | 대시보드 네비게이션/shortcut 수정 | V-5 |
| C-4 | Instruction 단일 소스 통합 | V-10 |
| C-5 | README 재작성 | V-7 |
| C-6 | GitHub sync → MCP recall 통합 | V-6 |

### Backlog (필요 시)

Over-engineering으로 분류된 항목 및 LOW 이슈. 실사용에서 문제가 되면 재평가.
