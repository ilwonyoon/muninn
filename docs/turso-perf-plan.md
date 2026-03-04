# Turso Sync Performance Optimization Plan

## Problem

MCP 서버의 응답 속도가 로컬 SQLite 대비 현저히 느림. 원인: 매 DB 메서드 호출마다 `libsql.connect()` + `conn.sync()` 네트워크 왕복 발생.

### 현재 패턴 (store.py)

```python
def some_method(self):
    conn = self._get_connection()   # connect() + sync() → 2 network round-trips
    try:
        conn.execute(...)
        conn.commit()
        self._sync(conn)            # sync() → 1 more round-trip
    finally:
        conn.close()
```

- `_get_connection()` 호출: **25회** (매 메서드마다)
- `_sync()` 호출: **12회** (쓰기 메서드마다)
- 매 MCP tool 호출 시 최소 2-3회 네트워크 왕복

### 성능 영향

| 작업 | 로컬 SQLite | 현재 (Turso sync) |
|------|------------|-----------------|
| connect | <1ms | ~100-300ms (TCP + TLS + sync) |
| sync | N/A | ~100-200ms per call |
| muninn_recall | <5ms | ~300-500ms |
| muninn_save | <10ms | ~500-1000ms |

## Solution: Persistent Connection + Lazy Sync

### Core Idea

1. **연결 1회 생성, 재사용** — MCP 서버는 장시간 실행 프로세스. `__init__`에서 한 번 connect하고 `self._conn`에 유지.
2. **읽기 전 sync (pull)** — 다른 클라이언트가 쓴 최신 데이터 반영. 단, 빈도 제한.
3. **쓰기 후 sync (push)** — 로컬 변경을 클라우드로 전파.
4. **sync 쿨다운** — 마지막 sync 후 N초 이내 재요청은 스킵.

### 변경 대상

**파일:** `src/muninn/store.py` (1개 파일만 수정)

### 상세 설계

#### 1. Persistent Connection

```python
class MuninnStore:
    def __init__(self, db_path=None):
        self._db_path = _resolve_db_path(db_path)
        self._turso_url = os.environ.get("TURSO_DATABASE_URL")
        self._turso_token = os.environ.get("TURSO_AUTH_TOKEN")

        Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)

        # Single persistent connection
        self._conn = self._create_connection()
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA busy_timeout=5000")
        self._conn.execute("PRAGMA foreign_keys = ON")
        _execute_statements(self._conn, _SCHEMA_STATEMENTS)
        self._run_migrations(self._conn)
        self._conn.commit()
        self._do_sync()  # initial sync

        # Sync throttle state
        self._last_sync_time = 0.0
```

#### 2. Connection Factory → Direct Access

기존 `_get_connection()` + `conn.close()` 패턴을 제거하고, 모든 메서드에서 `self._conn`을 직접 사용.

```python
# Before (매번 connect/close)
def get_project(self, id):
    conn = self._get_connection()
    try:
        cursor = conn.execute("SELECT ...", (id,))
        ...
    finally:
        conn.close()

# After (persistent connection)
def get_project(self, id):
    self._sync_if_needed()  # throttled pull
    cursor = self._conn.execute("SELECT ...", (id,))
    ...
```

#### 3. Sync Throttle

```python
_SYNC_COOLDOWN = 2.0  # seconds

def _sync_if_needed(self):
    """Pull from Turso if cooldown has elapsed (read path)."""
    if not self._turso_url:
        return
    now = time.monotonic()
    if now - self._last_sync_time >= _SYNC_COOLDOWN:
        self._do_sync()

def _sync_after_write(self):
    """Push to Turso immediately after writes."""
    if not self._turso_url:
        return
    self._do_sync()

def _do_sync(self):
    """Execute sync and update timestamp."""
    try:
        self._conn.sync()
        self._last_sync_time = time.monotonic()
    except Exception as exc:
        import logging
        logging.getLogger("muninn").error("Turso sync failed: %s", exc)
        raise
```

#### 4. 메서드별 적용 규칙

| 메서드 유형 | sync 전략 |
|-----------|----------|
| **읽기** (get_project, list_projects, recall, search) | `_sync_if_needed()` (throttled) |
| **쓰기** (create, update, delete) | commit 후 `_sync_after_write()` |
| **초기화** (__init__) | `_do_sync()` (무조건) |

### 예상 성능 개선

| 작업 | 현재 | 개선 후 |
|------|------|--------|
| muninn_recall | ~300-500ms | ~5-200ms (sync 스킵 시 로컬 속도) |
| muninn_save | ~500-1000ms | ~200-400ms (sync 1회만) |
| 연속 작업 (recall → save) | ~800-1500ms | ~200-400ms (sync 쿨다운) |

### 리스크

1. **연결 끊김** — 장시간 idle 후 연결이 죽을 수 있음. `_do_sync()`에서 예외 발생 시 재연결 로직 추가.
2. **동시 접근** — MCP 서버가 stdio라 single-threaded. WAL + busy_timeout이면 충분.
3. **데이터 지연** — sync 쿨다운 2초 동안 다른 클라이언트의 변경이 안 보일 수 있음. 수용 가능.

### 테스트

- 기존 250개 테스트 모두 통과해야 함 (테스트는 로컬 SQLite만 사용하므로 sync 경로는 미실행)
- 수동 E2E: `muninn_recall` → `muninn_save` → Turso 클라우드 검증

### 구현 체크리스트

- [ ] `_get_connection()` → `_create_connection()` 으로 이름 변경 (초기화 전용)
- [ ] `__init__`에서 `self._conn` persistent 연결 생성
- [ ] `_sync_if_needed()`, `_sync_after_write()`, `_do_sync()` 메서드 추가
- [ ] 모든 메서드에서 `conn = self._get_connection()` / `conn.close()` 제거
- [ ] 읽기 메서드: `self._sync_if_needed()` + `self._conn` 직접 사용
- [ ] 쓰기 메서드: `self._conn.commit()` + `self._sync_after_write()`
- [ ] 재연결 로직: `_do_sync()` 실패 시 `self._conn` 재생성 시도
- [ ] 테스트 실행: `.venv/bin/python -m pytest tests/ -x -q`
