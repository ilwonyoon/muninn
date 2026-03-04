# Muninn Auto-Save: 실행 스펙

## 대상

**Claude Code CLI 전용**. PostToolUse hook은 Claude Code SDK 기능이므로 다른 클라이언트에는 적용되지 않는다.

| 클라이언트 | Hook 트리거 (접근법 B) | Instructions 규칙 (접근법 A) |
|-----------|----------------------|---------------------------|
| Claude Code CLI | ✅ 적용 | ✅ 적용 |
| ChatGPT Mac App | ❌ 미지원 | ✅ 적용 (수동 트리거) |
| Claude Desktop | ❌ 미지원 | ✅ 적용 (수동 트리거) |
| Codex CLI | ❌ 미지원 (2026.03 기준 hook "in development") | ❌ AGENTS.md 별도 작성 필요 |

### 전제조건

- `jq` 설치 필요 (hook 스크립트가 JSON 파싱에 사용)
- `.claude/settings.local.json` — 현재 존재하지 않음, 새 파일 생성
- `.claude/hooks/` — 현재 존재하지 않음, 새 디렉토리 생성

## 배경

AI 도구로 작업 후 Muninn에 수동으로 `muninn_save`를 호출해야 한다. 깜빡하면 누락. 세션을 안 끄므로 "세션 종료 시 저장" 규칙도 작동하지 않는다.

**목표**: `git commit` 시점에 자동으로 Muninn 프로젝트 문서를 업데이트한다.

### 저장 기준: git에 없는 정보만

| 저장함 | 저장 안 함 |
|--------|-----------|
| **Why** — 왜 이 결정을 했는지 (동기, 트레이드오프) | 코드 변경 내용 (git diff에 있음) |
| **Topology** — 시스템 연결 구조 (배포, 인프라) | 구체적 파일명, 라인 번호 |
| **Ops knowledge** — 운영 지식 | 테스트 결과, 빌드 로그 |
| **State** — 현재 기능 현황 (전체 그림) | 버그 수정 내용 |

### 실제 예시 (이번 세션 기준)

| 한 일 | git에 있나 | Muninn에 저장 | 이유 |
|-------|-----------|-------------|------|
| libsql → sqlite3 import 교체 | ✅ | ❌ | 코드 보면 알 수 있음 |
| "Turso가 불안정해서 로컬 SQLite로 갔다" | ❌ | ✅ | **왜** 바꿨는지는 git에 없음 |
| 아키텍처가 3-tier에서 2-tier로 바뀜 | ❌ | ✅ | 코드만 봐선 이전 구조를 모름 |
| Dashboard가 Vercel→localhost로 전환 | ❌ | ✅ | 배포 토폴로지는 코드에 없음 |
| ChatGPT 재연결 필요 (OAuth 세션 초기화) | ❌ | ✅ | 운영 지식, 코드에 없음 |

---

## 구현: 두 레이어 조합

| 레이어 | 역할 | 파일 |
|--------|------|------|
| **Hook (트리거)** | commit 시 자동 발동, 조건 충족 시 프롬프트 주입 | `.claude/hooks/post-commit-muninn.sh`, `.claude/settings.local.json` |
| **Instructions (규칙)** | 무엇을/어떻게 저장할지 가이드 | `~/.local/share/muninn/instructions.md`, `CLAUDE.md` |

---

## Task 1: Instructions 업데이트

### 파일: `~/.local/share/muninn/instructions.md`

기존 `## Output Rules` 섹션 아래, `## What NOT to save` 위에 다음 섹션 추가:

```markdown
## Auto-Save Rules

### 트리거
git commit 완료 직후, commit 메시지가 다음 prefix에 해당하면 프로젝트 문서 업데이트:
- feat: (새 기능)
- refactor: (대규모 구조 변경)

스킵하는 커밋:
- fix:, docs:, test:, chore:, ci:, perf:

### 업데이트 절차
1. muninn_recall(project="xxx") — 현재 문서 로드
2. 아래 기준으로 반영할 내용 판단
3. 기존 문서의 해당 섹션을 수정/추가 (전체 교체가 아님)
4. muninn_save(project="xxx", content="<머지된 전체 문서>")

### 반영하는 것 (git에 없는 정보만)
- 아키텍처/스택 변경과 그 이유
- 시스템 연결 구조 변경 (배포, 인프라, 외부 서비스)
- 운영 시 알아야 할 사항
- 기능 현황 업데이트 (현재 상태 기준, 히스토리 아님)

### 반영하지 않는 것
- 코드 변경 내용 (git diff에 있음)
- 구체적 파일명, 라인 번호
- 테스트 결과, 빌드 로그
- 버그 수정 내용

### 문서 머지 원칙
- 같은 주제 섹션이 이미 있으면 내용을 교체 (append 아님)
- 예: "## Tech Stack"에 이미 "SQLite + Turso"라고 적혀있으면 → "SQLite (순수 로컬)"로 교체
- 새로운 주제면 적절한 위치에 섹션 추가
- 사라진 기능/구조는 문서에서 제거
```

### 파일: `CLAUDE.md`

`## Coding Conventions` 섹션 위에 다음 추가:

```markdown
## Muninn Auto-Save

git commit 후 commit 메시지가 `feat:` 또는 `refactor:`이면:
1. `muninn_recall(project="muninn")` → 현재 문서 확인
2. git에 없는 정보(why, topology, ops, state)만 문서에 머지
3. `muninn_save(project="muninn", content="<머지된 문서>")`로 업데이트

세부 규칙은 Muninn MCP instructions 참조.
```

### 검증

변경 후 instructions 내용 확인:
```bash
cat ~/.local/share/muninn/instructions.md
```
`## Auto-Save Rules` 섹션이 존재하는지 확인.

---

## Task 2: Hook 스크립트 생성

### 파일: `.claude/hooks/post-commit-muninn.sh` (새 파일)

```bash
#!/bin/bash
# PostToolUse:Bash hook — git commit 감지 시 Muninn 업데이트 프롬프트 주입
#
# 동작:
# 1. stdin에서 hook input (JSON) 읽기
# 2. 실행된 명령어가 git commit인지 확인
# 3. 마지막 commit 메시지의 prefix가 feat: 또는 refactor:인지 확인
# 4. 조건 충족 시 stdout으로 프롬프트 출력 → Claude Code에 주입됨

set -euo pipefail

# stdin으로 hook input 받기
INPUT=$(cat)

# tool_input.command 추출
TOOL_INPUT=$(echo "$INPUT" | jq -r '.tool_input.command // ""' 2>/dev/null)
if [ -z "$TOOL_INPUT" ]; then
  exit 0
fi

# git commit이 포함된 명령어가 아니면 스킵
if ! echo "$TOOL_INPUT" | grep -q "git commit"; then
  exit 0
fi

# tool_output.stdout에서 commit 성공 여부 확인 (선택적)
TOOL_OUTPUT=$(echo "$INPUT" | jq -r '.tool_output.stdout // ""' 2>/dev/null)
# commit이 실패했으면 (exit code != 0) 스킵
EXIT_CODE=$(echo "$INPUT" | jq -r '.tool_output.exit_code // "0"' 2>/dev/null)
if [ "$EXIT_CODE" != "0" ]; then
  exit 0
fi

# 마지막 commit 메시지 가져오기
COMMIT_MSG=$(git log -1 --pretty=format:"%s" 2>/dev/null || true)
if [ -z "$COMMIT_MSG" ]; then
  exit 0
fi

# feat: 또는 refactor: prefix가 아니면 스킵
if ! echo "$COMMIT_MSG" | grep -qE "^(feat|refactor):"; then
  exit 0
fi

# git remote URL에서 프로젝트명 추출 (fallback: 디렉토리명)
PROJECT=""
REMOTE=$(git remote get-url origin 2>/dev/null || true)
if [ -n "$REMOTE" ]; then
  PROJECT=$(basename "$REMOTE" .git | tr '[:upper:]' '[:lower:]')
fi
if [ -z "$PROJECT" ]; then
  PROJECT=$(basename "$(pwd)" | tr '[:upper:]' '[:lower:]')
fi

# 변경 파일 수 (참고 정보)
FILES_CHANGED=$(git diff --name-only HEAD~1 HEAD 2>/dev/null | wc -l | tr -d ' ')

# 프롬프트 주입 (stdout으로 출력)
cat <<EOF
[MUNINN AUTO-SAVE] commit detected: "$COMMIT_MSG" ($FILES_CHANGED files changed)

이 커밋은 feat/refactor이므로 Muninn 프로젝트 문서를 업데이트하세요:

1. muninn_recall(project="$PROJECT")로 현재 문서 로드
2. 이번 변경에서 git에 없는 정보만 추출:
   - 왜 이 변경을 했는지 (동기/트레이드오프)
   - 아키텍처/인프라 구조 변경
   - 운영 시 알아야 할 사항
   - 기능 현황 업데이트 (현재 상태로 교체, 히스토리 아님)
3. 기존 문서의 해당 섹션을 수정/추가 (같은 주제면 교체)
4. muninn_save(project="$PROJECT", content="<머지된 전체 문서>")

반영하지 않을 것: 코드 diff, 파일명, 테스트 결과, 빌드 로그
EOF
```

### 실행 권한 부여

```bash
mkdir -p .claude/hooks
chmod +x .claude/hooks/post-commit-muninn.sh
```

---

## Task 3: settings.local.json에 hook 등록

### 파일: `.claude/settings.local.json` (새 파일 생성 — 기존 파일 없음, 병합 불필요)

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "bash .claude/hooks/post-commit-muninn.sh"
          }
        ]
      }
    ]
  }
}
```

**참고**: 이 파일은 프로젝트 레벨 설정. 글로벌 `~/.claude/settings.json`의 hooks와 병합되어 동작.

---

## Task 4: 검증

### 4a. Hook 트리거 테스트 (feat: commit)

```bash
# 아무 파일에 공백 추가
echo "" >> README.md
git add README.md
git commit -m "feat: test auto-save hook"
```

**기대 결과**: commit 후 Claude Code에 `[MUNINN AUTO-SAVE]` 프롬프트가 주입되고, AI가 `muninn_recall` → `muninn_save` 플로우를 실행.

### 4b. Hook 스킵 테스트 (fix: commit)

```bash
echo "" >> README.md
git add README.md
git commit -m "fix: test hook skip"
```

**기대 결과**: hook이 스킵되어 프롬프트 주입 없음.

### 4c. Hook 스크립트 단독 테스트

```bash
echo '{"tool_input":{"command":"git commit -m \"feat: test\""},"tool_output":{"exit_code":"0","stdout":"[main abc1234] feat: test"}}' | bash .claude/hooks/post-commit-muninn.sh
```

**기대 결과**: `[MUNINN AUTO-SAVE]` 프롬프트가 stdout으로 출력됨.

### 4d. instructions 확인

```bash
grep "Auto-Save Rules" ~/.local/share/muninn/instructions.md
```

**기대 결과**: 매칭되는 줄 출력.

---

## 동작 흐름 (완성 후)

```
사용자: "커밋해줘"
  ↓
Claude Code: git commit -m "feat: remove Turso, simplify to SQLite"
  ↓
PostToolUse:Bash hook 발동
  ↓
post-commit-muninn.sh 실행:
  - "git commit" 포함? → ✅
  - exit_code == 0? → ✅
  - commit msg prefix "feat:"? → ✅
  - stdout으로 프롬프트 출력
  ↓
Claude Code가 주입된 프롬프트 처리:
  1. muninn_recall(project="muninn") → 현재 문서 로드
  2. git에 없는 정보 추출 (why, topology, ops, state)
  3. 기존 문서에 머지 (같은 섹션이면 교체)
  4. muninn_save(project="muninn", content="<머지된 문서>")
  ↓
완료 — Dashboard에서 업데이트된 문서 확인 가능
```

---

## 향후 확장 (이번 구현 범위 아님)

- 멀티 프로젝트 자동 감지 고도화 (monorepo 지원)
- Dashboard Progress 탭에 auto-save 이력 표시
- Memory `title` 필드를 topic으로 활용한 upsert 패턴
- ChatGPT/Claude Desktop에도 유사 auto-save (server-side hook)
- 커밋 없이도 의미 있는 변경 감지 (대화 기반 트리거)
