#!/bin/bash
# PostToolUse:Bash hook — git commit 감지 시 Muninn 업데이트 프롬프트 주입
#
# 동작:
# 1. stdin에서 hook input (JSON) 읽기
# 2. 실행된 명령어가 git commit인지 확인
# 3. 마지막 commit 메시지의 prefix가 feat: 또는 refactor:인지 확인
# 4. 조건 충족 시 JSON additionalContext로 프롬프트 출력 → Claude Code에 주입됨
#
# 중요: PostToolUse hook은 plain stdout이 아닌 JSON hookSpecificOutput.additionalContext로
#       출력해야 model context에 주입됩니다.

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

# cwd 추출 (hook JSON에 포함됨), fallback으로 현재 디렉토리
HOOK_CWD=$(echo "$INPUT" | jq -r '.cwd // ""' 2>/dev/null)
if [ -n "$HOOK_CWD" ] && [ -d "$HOOK_CWD" ]; then
  cd "$HOOK_CWD"
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

# 프롬프트 텍스트 구성
PROMPT="[MUNINN AUTO-SAVE] commit detected: \"$COMMIT_MSG\" ($FILES_CHANGED files changed)

이 커밋은 feat/refactor이므로 Muninn 프로젝트 문서를 업데이트하세요:

1. muninn_recall(project=\"$PROJECT\")로 현재 문서 로드
2. 이번 변경에서 git에 없는 정보만 추출:
   - 왜 이 변경을 했는지 (동기/트레이드오프)
   - 아키텍처/인프라 구조 변경
   - 운영 시 알아야 할 사항
   - 기능 현황 업데이트 (현재 상태로 교체, 히스토리 아님)
3. 기존 문서의 해당 섹션을 수정/추가 (같은 주제면 교체)
4. muninn_save(project=\"$PROJECT\", content=\"<머지된 전체 문서>\")

반영하지 않을 것: 코드 diff, 파일명, 테스트 결과, 빌드 로그"

# JSON additionalContext로 출력 (stdout에 JSON만 출력해야 함)
jq -n --arg ctx "$PROMPT" '{
  "hookSpecificOutput": {
    "hookEventName": "PostToolUse",
    "additionalContext": $ctx
  }
}'
