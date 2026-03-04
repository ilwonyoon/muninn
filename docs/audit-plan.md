# Muninn 전수 조사 계획

4개 축에 대해 각각 독립적으로 Codex에 위임. 결과를 종합하여 우선순위 액션 아이템 도출.

---

## 1. 안정성 (Stability & Reliability)

**조사 범위:**
- 에러 핸들링 패턴: 모든 try/except에서 에러가 적절히 처리/보고되는지
- Turso 연결 복원력: 네트워크 끊김, 토큰 만료, sync 실패 시 복구
- DB 스키마 마이그레이션: 버전 업그레이드 시 데이터 유실 가능성
- MCP 도구 함수: 예외를 삼키고 빈 문자열 반환하는 패턴의 적절성
- concurrent access: 여러 MCP 클라이언트 동시 접근 시 WAL/busy_timeout 충분한지
- FTS5 sync triggers: INSERT/UPDATE/DELETE 트리거 정합성
- 대시보드 API: 에러 응답 일관성, edge case 처리

**산출물:** 안정성 이슈 목록 (severity: critical/high/medium/low)

---

## 2. 보안 (Security)

**조사 범위:**
- SQL injection: 모든 DB 쿼리에서 parameterized query 사용 여부
- Auth: Bearer token middleware 우회 가능성
- OAuth 2.0: 토큰 저장, 갱신, 폐기 플로우
- 환경변수: 시크릿 노출 경로 (로그, 에러 메시지, 클라이언트 응답)
- CORS/origin: HTTP transport에서의 접근 제어
- 입력 검증: content, project_id, tags 등의 sanitization
- 의존성: 알려진 CVE가 있는 패키지
- Next.js 대시보드: XSS, CSRF, API route 인증
- Turso 토큰: 권한 범위, 만료 정책

**산출물:** 보안 취약점 목록 (OWASP 분류 + severity)

---

## 3. 퍼포먼스 (Performance)

**조사 범위:**
- DB 쿼리 효율: N+1 쿼리, 불필요한 full table scan
- 인덱스 활용: 기존 인덱스가 실제 쿼리 패턴을 커버하는지
- FTS5 성능: 큰 데이터셋에서의 검색 속도
- 메모리 사용: 큰 summary/content 처리 시 메모리 패턴
- Turso sync 최적화: 방금 적용한 persistent connection이 충분한지
- 대시보드 API: 페이지네이션 없는 엔드포인트, 큰 응답
- Next.js: 불필요한 re-render, 번들 사이즈, API 호출 패턴
- 서버 시작 시간: 스키마 마이그레이션 + 초기 sync 시간

**산출물:** 성능 병목 목록 + 개선 제안 (예상 효과 포함)

---

## 4. 제품 가치 (Product Value)

**조사 범위:**
- Document-first 아키텍처의 한계와 개선 방향
- MCP instructions의 효과: LLM 클라이언트가 실제로 잘 따르는지
- 검색 기능: FTS5 기반 검색의 정확도와 한계
- 멀티 클라이언트 경험: Claude/ChatGPT/Codex 간 문서 공유 UX
- 대시보드 UX: 핵심 워크플로우 (문서 편집, 프로젝트 관리)의 완성도
- 빠진 기능: 경쟁 제품 대비 누락된 핵심 기능
- 데이터 모델: 현재 스키마가 향후 기능 확장을 지원하는지
- GitHub sync: 실사용 가치와 개선점
- 온보딩: 새 사용자가 처음 설치~첫 문서 저장까지의 마찰

**산출물:** 제품 개선 로드맵 제안 (must-have / nice-to-have / future)

---

## 실행 방법

4개 축을 Codex에 **병렬로 위임** (각각 read-only 모드):

```
codex-collab run "Audit 1: Stability..." -s read-only
codex-collab run "Audit 2: Security..." -s read-only
codex-collab run "Audit 3: Performance..." -s read-only
codex-collab run "Audit 4: Product Value..." -s read-only
```

결과 취합 후 Claude가 우선순위 정리 → 액션 아이템 도출.
