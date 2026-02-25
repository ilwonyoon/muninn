# Muninn Dashboard — Phase 3 Design & Implementation Plan

> 작성일: 2026-02-25
> 상태: Planning

---

## 1. 개발자 대시보드 스타일 리서치

### 분석 대상 8개 대시보드

#### 1.1 Vercel Dashboard (Geist Design System)

| 항목 | 내용 |
|------|------|
| **비주얼** | Dark-first, 흑백 모노크롬 + 파랑/초록 accent. 극도로 절제된 색상 |
| **타이포그래피** | Geist Sans (본문) + Geist Mono (코드/데이터). Inter 영향받은 geometric sans |
| **레이아웃** | 좌측 사이드바 (2025 리디자인) + 콘텐츠 영역. 정보 계층 명확 |
| **핵심 패턴** | 프로젝트 카드 그리드, 배포 타임라인, 실시간 로그, 도메인 관리 테이블 |
| **개발자 친화** | Cmd+K 커맨드 팔레트, 모노스페이스 코드 블록, 배포 상태 실시간 |
| **디자인 시스템** | Geist (자체). Figma 공개, 42개 컴포넌트. shadcn/ui와 호환 구조 |
| **Muninn 적합도** | ★★★★★ — 프로젝트 목록 + 상세 뷰 패턴이 우리 프로젝트→메모리 계층과 정확히 매칭 |
| **약점** | 비공개 UI 라이브러리 (커뮤니티 클론만 존재). 모노크롬이 데이터 시각화에 불리 |

#### 1.2 Linear

| 항목 | 내용 |
|------|------|
| **비주얼** | Dark-first, 모노크롬 (기존 파랑→흑백으로 전환). 글래스모피즘, 복잡한 그래디언트 |
| **타이포그래피** | SF Pro + 자체 폰트. 굵은 제목, 높은 대비 |
| **레이아웃** | 좌측 사이드바 (축소 가능) + 탭 기반 콘텐츠. 시각적 노이즈 최소화 |
| **핵심 패턴** | 이슈 리스트, 칸반 보드, 사이클 타임라인, 필터 바 |
| **개발자 친화** | 키보드 퍼스트 (Cmd+K, `/` 필터, `E` 빠른 액션). 마우스 없이 모든 작업 가능 |
| **디자인 시스템** | Radix UI 프리미티브 + styled-components. 컴포넌트별 개별 NPM 패키지 |
| **Muninn 적합도** | ★★★★☆ — 리스트뷰/필터링 패턴 우수. 하지만 이슈 트래커 특화 |
| **약점** | 칸반/사이클 중심 → 메모리 관리와 직접 매칭 어려움 |

#### 1.3 Raycast

| 항목 | 내용 |
|------|------|
| **비주얼** | Dark-first, 반투명 패널, 블러 효과. 네이티브 macOS 느낌 |
| **타이포그래피** | SF Pro 기반, 콤팩트한 행 간격 |
| **레이아웃** | 커맨드 팔레트 중심 단일 인터페이스. 검색→결과→액션 흐름 |
| **핵심 패턴** | 커맨드 팔레트, 리스트+디테일 분할, 빠른 액션 바, 익스텐션 그리드 |
| **개발자 친화** | 검색 중심 인터랙션, 키보드 내비게이션 100%, 최소 클릭 |
| **Muninn 적합도** | ★★★☆☆ — 커맨드 팔레트 패턴 차용 가능. 하지만 데스크톱 앱 특화 |
| **약점** | 웹 대시보드와 패러다임 다름. 복잡한 데이터 뷰에 부적합 |

#### 1.4 GitHub (New UI)

| 항목 | 내용 |
|------|------|
| **비주얼** | Light/Dark 동등 지원. 2025년부터 더 많은 컬러 사용. Primer 디자인 시스템 |
| **타이포그래피** | -apple-system 스택 + Mona Sans. 모노스페이스 코드 뷰 |
| **레이아웃** | 탑 네비 + 좌측 사이드바 (레포 내). 콘텐츠 밀도 높음 |
| **핵심 패턴** | 파일 트리, 이슈/PR 리스트, 탭 네비게이션, 배지/라벨 시스템, 타임라인 |
| **개발자 친화** | `.` → web editor, Cmd+K, 마크다운 네이티브, 코드 하이라이팅 |
| **디자인 시스템** | Primer (오픈소스). React 컴포넌트, CSS 토큰, Figma |
| **Muninn 적합도** | ★★★☆☆ — 라벨/태그 시스템 참고 가능. 트리뷰 패턴 유용 |
| **약점** | 과밀한 정보 → Muninn의 단순한 데이터 구조에 오버엔지니어링 |

#### 1.5 Supabase Dashboard

| 항목 | 내용 |
|------|------|
| **비주얼** | Dark-first, 진한 회색/검정 + 초록 accent. 세련된 개발자 콘솔 느낌 |
| **타이포그래피** | Inter + 모노스페이스 (SQL 에디터). 적절한 밀도 |
| **레이아웃** | 좌측 사이드바 (섹션별 아이콘) + 넓은 콘텐츠 영역. 테이블 에디터 중심 |
| **핵심 패턴** | 테이블 에디터 (스프레드시트), SQL 에디터 (Monaco), 스키마 시각화, 로그 뷰어 |
| **개발자 친화** | SQL 에디터, AI 쿼리 생성, 실시간 로그, API 문서 내장 |
| **디자인 시스템** | Radix UI + Tailwind CSS 기반 자체 UI 라이브러리 (오픈소스) |
| **Muninn 적합도** | ★★★★☆ — 테이블 에디터 패턴이 메모리 CRUD에 적합. SQL 뷰어 참고 가능 |
| **약점** | DB 관리 특화 → 프로젝트 개요/상태 대시보드 패턴은 부족 |

#### 1.6 Grafana

| 항목 | 내용 |
|------|------|
| **비주얼** | Dark-first, 오렌지/파랑 accent. 패널 그리드 기반 |
| **레이아웃** | 좌측 사이드바 + 드래그 가능한 패널 그리드. 사용자 커스터마이즈 |
| **핵심 패턴** | 시계열 차트, 패널 대시보드, 알림 규칙, 데이터소스 연결 |
| **Muninn 적합도** | ★★☆☆☆ — 모니터링/메트릭 특화. 메모리 관리와 패러다임 다름 |
| **약점** | 설정 복잡도 높음, 단순 CRUD에 과도함 |

#### 1.7 PostHog

| 항목 | 내용 |
|------|------|
| **비주얼** | Light-first (Dark 지원), 화이트 + 파랑/빨강 accent. 인포그래픽 스타일 |
| **레이아웃** | 좌측 사이드바 + 분석 캔버스. 퍼널/리텐션 차트 중심 |
| **핵심 패턴** | 이벤트 타임라인, 퍼널 시각화, SQL 쿼리, 세션 리플레이, A/B 테스트 |
| **Muninn 적합도** | ★★☆☆☆ — 분석 대시보드 특화. 태그 빈도/사용 패턴 시각화만 참고 가능 |
| **약점** | 분석 도구 → CRUD 관리와 맞지 않음 |

#### 1.8 Railway

| 항목 | 내용 |
|------|------|
| **비주얼** | Dark-first, 보라/분홍 accent. 캔버스 기반 시각적 배치 |
| **레이아웃** | 캔버스 (서비스 노드 배치) + 사이드 패널 (설정). 공간적 관계 표현 |
| **핵심 패턴** | 서비스 노드 그래프, 환경별 탭, 배포 로그, 메트릭 차트 |
| **개발자 친화** | YAML 옵셔널, 비주얼 인프라 관리, PR 프리뷰 환경 |
| **Muninn 적합도** | ★★★☆☆ — 캔버스 패턴이 Supersede 체인 시각화에 참고 가능 |
| **약점** | 인프라 배포 특화 → 메모리 관리와 직접 매칭 어려움 |

---

### 비교 매트릭스

| 대시보드 | Dark-first | 키보드 | 사이드바 | 커맨드팔레트 | 데이터밀도 | Muninn 적합 |
|----------|-----------|--------|---------|-------------|-----------|------------|
| **Vercel** | ✅ | ✅ | ✅ | Cmd+K | 중간 | ★★★★★ |
| **Linear** | ✅ | ✅✅ | ✅ | Cmd+K | 중간 | ★★★★☆ |
| **Raycast** | ✅ | ✅✅✅ | ✗ | 전체 | 낮음 | ★★★☆☆ |
| **GitHub** | ✅/✗ | ✅ | ✅ | Cmd+K | 높음 | ★★★☆☆ |
| **Supabase** | ✅ | ✅ | ✅ | ✗ | 높음 | ★★★★☆ |
| **Grafana** | ✅ | ✗ | ✅ | ✗ | 매우높음 | ★★☆☆☆ |
| **PostHog** | ✗ | ✗ | ✅ | ✗ | 높음 | ★★☆☆☆ |
| **Railway** | ✅ | ✗ | 캔버스 | ✗ | 낮음 | ★★★☆☆ |

---

## 2. 디자인 방향 결정

### 추천: "Vercel Structure + Supabase Color + Linear Interactions"

Vercel 스타일을 **레이아웃/구조** 베이스로 하되, Supabase의 **컬러 철학**과 Linear의 **키보드 인터랙션**을 차용하는 하이브리드 접근.

> **핵심 원칙:** Vercel의 순수 흑백은 배포 상태(빌드/실패)처럼 이진 상태에 최적화되어 있다.
> Muninn은 텍스트 중심, 다중 depth, 태그 기반의 복잡한 데이터를 다루므로 더 많은 컬러 시그널이 필요하다.
> Supabase의 "다크 + 단일 accent" 접근이 이 간극을 메운다.

**각 소스에서 가져올 것:**

| 소스 | 채택 패턴 |
|------|---------|
| **Vercel** | 사이드바 레이아웃, Geist 타이포그래피, 프로젝트-as-필터 패턴, 축소 가능 사이드바 |
| **Linear** | 8px 스페이싱 스케일, 키보드 퍼스트, LCH 컬러 스페이스, 커맨드 메뉴, 밀도 높은 리스트뷰 |
| **Supabase** | 다크퍼스트 + 단일 accent 컬러, 테이블 에디터 패턴, Radix Colors 토큰 기반 |
| **Raycast** | "팔레트 in 팔레트" 드릴다운 (프로젝트→메모리→상세), 키워드 퍼지 검색 |
| **GitHub** | 3-tier 기능적 컬러 토큰 (base→functional→component), 필터/소트 바 |
| **PostHog** | 폴더 기반 엔티티 관리, 커스터마이즈 가능한 사이드바 숏컷, 높은 데이터 밀도 |
| **Grafana** | stat 카드 (메모리 수, 마지막 활동, depth 분포) |

**Tradeoff:**
- 모노크롬 Vercel 스타일은 depth/status 시각적 구분에 불리 → status별 accent 컬러 추가 필요
- 3개 스타일 믹스는 일관성 유지가 과제 → 디자인 토큰으로 통제
- Vercel 에코시스템 의존성 → Next.js App Router에 묶이지만, 대시보드는 인증 뒤에 있으므로 초기 로드 시간보다 개발 속도가 중요

### Accent 컬러 선택

Supabase의 에메랄드 그린은 이미 점유됨. Muninn의 정체성("기억/지식")을 반영할 컬러:

- **추천: Muted Teal (`oklch(0.65 0.12 195)`)** — "지식/기억"의 차분함. 터미널 그린과 차별화
- 대안: Blue-Violet (`oklch(0.60 0.15 280)`) — 더 독특하지만 접근성 리스크

---

## 3. 디자인 시스템 구축

### 3.1 Tech Stack

| 선택 | 이유 |
|------|------|
| **Next.js 15 (App Router)** | Vercel 생태계 최적화, SSR/SSG, 파일 기반 라우팅. SvelteKit이 번들 크기는 작지만 shadcn/cmdk/TanStack 등 React 에코시스템이 압도적 |
| **shadcn/ui** | Vercel이 v0에서 공식 사용. Radix + Tailwind 기반. 복사→소유 패턴. Base UI 대체 프리미티브도 지원 시작 (Radix 유지보수 우려 대비) |
| **Tailwind CSS v4** | Geist 호환, 디자인 토큰 CSS 변수 네이티브 |
| **Geist Font** | Vercel 공식 폰트 패밀리 (Sans + Mono). `npm install geist` |
| **cmdk** | Linear/Raycast가 사용하는 커맨드 팔레트 라이브러리 (shadcn Command 컴포넌트 기반) |
| **Recharts** | shadcn/ui 차트 컴포넌트 기본 엔진 |
| **Zustand** | 경량 상태 관리 (프로젝트 선택, 필터 상태) |
| **TanStack Table** | 메모리 테이블 정렬/필터/페이지네이션 |
| **Lucide Icons** | shadcn/ui 기본 아이콘셋. 깔끔하고 일관성 있음 |

> **프레임워크 선택 근거:** SvelteKit은 번들 크기 우위지만, shadcn/ui, cmdk, TanStack Table, Tremor 모두 React-first.
> 솔로 빌더에게 React 에코시스템 깊이가 SvelteKit 성능 이점보다 중요. 대시보드는 인증 뒤에 있어 초기 로드 시간 < 개발 속도.
> Astro는 Islands 아키텍처라 인터랙티브 대시보드에 부적합.

### 3.2 디자인 토큰

```
Colors (Dark-first)
├── Background
│   ├── --bg-000: #000000    (page)
│   ├── --bg-100: #0a0a0a    (card)
│   ├── --bg-200: #1a1a1a    (elevated)
│   └── --bg-300: #262626    (hover)
├── Foreground
│   ├── --fg-000: #fafafa    (primary text)
│   ├── --fg-100: #a1a1a1    (secondary)
│   └── --fg-200: #666666    (muted)
├── Border
│   ├── --border-default: #262626
│   └── --border-hover: #333333
├── Status (Muninn-specific)
│   ├── --status-active: #00cc88   (🟢)
│   ├── --status-paused: #ffaa00   (⏸️)
│   ├── --status-idea: #8b5cf6     (💡)
│   └── --status-archived: #666666 (📦)
├── Depth (Muninn-specific)
│   ├── --depth-0: #00cc88    (overview — always loaded)
│   ├── --depth-1: #3b82f6    (context — default)
│   ├── --depth-2: #f59e0b    (detailed)
│   └── --depth-3: #666666    (archive)
└── Accent
    └── --accent: #0070f3     (Vercel blue)

Typography
├── Font Family
│   ├── --font-sans: 'Geist Sans', sans-serif
│   └── --font-mono: 'Geist Mono', monospace
├── Scale
│   ├── --text-xs:  12px / 16px
│   ├── --text-sm:  13px / 20px
│   ├── --text-base: 14px / 20px
│   ├── --text-lg:  16px / 24px
│   ├── --text-xl:  20px / 28px
│   └── --text-2xl: 24px / 32px
└── Weight
    ├── --font-normal: 400
    ├── --font-medium: 500
    └── --font-semibold: 600

Spacing (4px base)
├── --space-1: 4px
├── --space-2: 8px
├── --space-3: 12px
├── --space-4: 16px
├── --space-6: 24px
├── --space-8: 32px
└── --space-12: 48px

Radius
├── --radius-sm: 4px
├── --radius-md: 6px
├── --radius-lg: 8px
└── --radius-xl: 12px
```

### 3.3 핵심 컴포넌트 목록

```
Base (shadcn/ui)
├── Button, Badge, Input, Select
├── Dialog, Sheet, Popover
├── Table, Card, Separator
├── Command (Cmd+K)
├── Toast, Tooltip
└── Tabs, ScrollArea

Muninn-specific
├── ProjectCard        — 상태 인디케이터 + 메모리 수 + 마지막 업데이트
├── MemoryRow          — depth 컬러 바 + 콘텐츠 프리뷰 + 태그 + 액션
├── DepthBadge         — depth 0-3 시각 표시
├── StatusIndicator    — active/paused/idea/archived 도트
├── TagPill            — 태그 필터 칩
├── SupersedeChain     — 메모리 버전 히스토리 (타임라인)
├── FreshnessIndicator — 오래된 메모리 하이라이트 (7d/30d/90d)
├── CharBudgetBar      — recall 문자 예산 사용량 바
└── CommandPalette     — Cmd+K 글로벌 검색/액션
```

---

## 4. 정보 매핑 — Muninn 데이터 → UI

### 4.1 페이지 구조

```
/                          → Dashboard (전체 프로젝트 오버뷰)
/projects/:name            → 프로젝트 상세 (메모리 리스트)
/projects/:name/:id        → 메모리 상세 (편집, supersede 체인)
/search                    → 전역 검색 결과
/settings                  → 서버 설정, API 키, 연결 상태
```

### 4.2 Dashboard (메인 페이지)

```
┌─────────────────────────────────────────────────────────────┐
│  🧠 Muninn                          [Cmd+K Search]   [⚙️] │
├──────────┬──────────────────────────────────────────────────┤
│          │                                                  │
│ PROJECTS │  Overview                                        │
│ ──────── │  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐           │
│ All  (5) │  │ 54   │ │ 12   │ │ 3    │ │ 2    │           │
│          │  │ total │ │ fresh│ │ stale│ │ idea │           │
│ 🟢 Active│  └──────┘ └──────┘ └──────┘ └──────┘           │
│  muninn  │                                                  │
│  aido    │  Projects                    [Filter▾] [Sort▾]  │
│          │  ┌────────────────────────────────────────────┐  │
│ ⏸ Paused │  │ 🟢 muninn          15 memories   2h ago   │  │
│  glpuri  │  │    MCP memory server for solo builders     │  │
│          │  ├────────────────────────────────────────────┤  │
│ 💡 Ideas │  │ 🟢 aido             8 memories   1d ago   │  │
│  focus   │  │    AI startup scoring engine               │  │
│          │  ├────────────────────────────────────────────┤  │
│ 📦 Arch. │  │ ⏸️ glpuri           23 memories   5d ago  │  │
│  (none)  │  │    GLP-1 research tracker                  │  │
│          │  └────────────────────────────────────────────┘  │
│          │                                                  │
│ [+ New]  │                                                  │
└──────────┴──────────────────────────────────────────────────┘
```

**데이터 매핑:**
- `store.list_projects()` → 프로젝트 카드 리스트
- `ProjectStatus` → 사이드바 그룹핑 + StatusIndicator 컬러
- 메모리 수 → 카운트 배지
- `updated_at` → FreshnessIndicator + 상대 시간

### 4.3 Project Detail (프로젝트 상세)

```
┌─────────────────────────────────────────────────────────────┐
│  🧠 Muninn                          [Cmd+K Search]   [⚙️] │
├──────────┬──────────────────────────────────────────────────┤
│          │                                                  │
│ PROJECTS │  muninn  🟢 Active         [Edit] [Archive ▾]  │
│ ──────── │  MCP memory server for solo builders             │
│ 🟢 Active│  github: ilwonyoon/muninn                        │
│ ▸ muninn │                                                  │
│   aido   │  Memories (15)    [+ Save]  [Search] [Filter▾]  │
│          │                                                  │
│ ⏸ Paused │  Depth ── 0 │ 1 │ 2 │ 3 ──  Tags ── all ▾     │
│   glpuri │  ┌─────┬──────────────────────┬──────┬────────┐ │
│          │  │Depth│ Content              │ Tags │ Age    │ │
│ 💡 Ideas │  ├─────┼──────────────────────┼──────┼────────┤ │
│   focus  │  │ 🟢0 │ Cross-tool MCP mem...│ core │ 2h     │ │
│          │  │ 🔵1 │ Scoring weights: f...│ dec  │ 1d     │ │
│          │  │ 🔵1 │ Market analysis: 3...│ res  │ 3d     │ │
│          │  │ 🟡2 │ API schema: /comp...│ spec │ 5d     │ │
│          │  │ ⚫3 │ Raw interview note...│ raw  │ 12d ⚠ │ │
│          │  └─────┴──────────────────────┴──────┴────────┘ │
│          │                                                  │
│          │  Budget: ████████░░ 3,200 / 4,000 chars (80%)   │
│          │                                                  │
└──────────┴──────────────────────────────────────────────────┘
```

**데이터 매핑:**
- `store.recall(project, depth, max_chars)` → 메모리 테이블
- `memory.depth` → DepthBadge (컬러 코딩)
- `memory.content` → 텍스트 프리뷰 (truncated)
- `memory_tags` → TagPill 리스트
- `memory.created_at` → 상대 시간 + FreshnessIndicator
- `store.get_project()` → 프로젝트 헤더 (summary, status, github_repo)
- Character budget → CharBudgetBar (프로그레스 바)

### 4.4 Memory Detail (메모리 상세/편집)

```
┌─────────────────────────────────────────────────────────────┐
│  ← muninn / Memory Detail                    [Delete] [×]  │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ID: a1b2c3d4-...  (a1b2c3)         Created: 2026-02-10   │
│  Depth: 🔵 1 (Context)              Updated: 2026-02-20   │
│  Source: conversation                                       │
│  Tags: [decision] [scoring] [+ Add]                        │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Content                                    [Edit ✏️] │   │
│  │                                                     │   │
│  │ Scoring weights for startup evaluation:             │   │
│  │ - funding: 0.3                                      │   │
│  │ - team: 0.25                                        │   │
│  │ - market: 0.2                                       │   │
│  │ - product: 0.15                                     │   │
│  │ - traction: 0.1                                     │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  Supersede Chain                                            │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  ○ a1b2c3 (current)   2026-02-20                   │   │
│  │  │                                                   │   │
│  │  ○ f8e9d0 (superseded) 2026-02-15                   │   │
│  │  │  "Initial weights: equal 0.2 each"               │   │
│  │  │                                                   │   │
│  │  ● e3f4g5 (original)   2026-02-10                   │   │
│  │     "Need scoring system for evaluation"            │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**데이터 매핑:**
- `store.get_memory(id)` → 전체 메모리 상세
- `memory.superseded_by` 체인 추적 → SupersedeChain 타임라인
- `memory.source` → MemorySource 배지 (conversation/github/manual)
- 인라인 편집 → `store.update_memory()` 호출

### 4.5 Command Palette (Cmd+K)

```
┌───────────────────────────────────────┐
│ 🔍 Search memories, projects...      │
├───────────────────────────────────────┤
│ Recent                                │
│   muninn → Scoring weights...         │
│   aido → Market analysis...           │
│                                       │
│ Actions                               │
│   📝 Save new memory                  │
│   📁 Create new project               │
│   🔍 Search all memories              │
│   ⚙️ Toggle project status            │
│                                       │
│ Projects                              │
│   🟢 muninn (15)                      │
│   🟢 aido (8)                         │
│   ⏸️ glpuri (23)                      │
└───────────────────────────────────────┘
```

---

## 4A. 데이터 레이어 — SQLite 스키마 → UI 필드 매핑

대시보드가 렌더링하는 모든 데이터의 출처를 정확히 정의한다.

### DB 스키마 (Schema v2)

```sql
-- projects 테이블
projects (
  id          TEXT PK,        -- 프로젝트 식별자 (예: "muninn")
  name        TEXT NOT NULL,  -- 표시 이름 (예: "Muninn")
  status      TEXT DEFAULT 'active'  -- CHECK: active|paused|idea|archived
  summary     TEXT,           -- 프로젝트 한줄 요약 (nullable)
  github_repo TEXT,           -- "owner/repo" 형식 (nullable)
  created_at  TIMESTAMP,
  updated_at  TIMESTAMP
)

-- memories 테이블
memories (
  id             TEXT PK,        -- UUID hex (32자)
  project_id     TEXT FK→projects(id),
  content        TEXT NOT NULL,  -- 메모리 본문
  depth          INTEGER DEFAULT 1  -- CHECK: 0-3
  source         TEXT DEFAULT 'conversation'  -- CHECK: conversation|github|manual
  superseded_by  TEXT,           -- 다른 memory ID, '_deleted', 또는 NULL
  created_at     TIMESTAMP,
  updated_at     TIMESTAMP
)

-- memory_tags 정션 테이블
memory_tags (
  memory_id  TEXT FK→memories(id) ON DELETE CASCADE,
  tag        TEXT NOT NULL,
  PRIMARY KEY (memory_id, tag)
)

-- memories_fts (FTS5 가상 테이블, porter stemming)
-- schema_version (마이그레이션 추적)
```

### Frozen Dataclass → JSON 응답 매핑

```
Project (frozen dataclass)           →  대시보드 JSON
──────────────────────────────────────────────────────
id: str                              →  프로젝트 ID / URL 파라미터
name: str                            →  표시 이름
status: str                          →  StatusIndicator 컴포넌트
  "active"  → 🟢 --status-active
  "paused"  → ⏸️ --status-paused
  "idea"    → 💡 --status-idea
  "archived"→ 📦 --status-archived
summary: str | None                  →  프로젝트 카드 부제
github_repo: str | None              →  GitHub 링크 + Sync 버튼 표시 여부
created_at: str (ISO 8601)           →  "생성일" (relative_time 변환)
updated_at: str (ISO 8601)           →  "마지막 업데이트" + FreshnessIndicator
  7일 이상 → ⚠️ stale 하이라이트
memory_count: int (computed)         →  프로젝트 카드의 "N memories" 배지
```

```
Memory (frozen dataclass)            →  대시보드 JSON
──────────────────────────────────────────────────────
id: str (32자 hex)                   →  short_id = id[:8] (prefix matching)
                                        MemoryRow에서 monospace (Geist Mono)
project_id: str                      →  프로젝트 연결 / 브레드크럼
content: str                         →  메모리 본문 (프리뷰: 첫 100자 + truncate)
                                        상세뷰: 전체 텍스트 (인라인 편집 가능)
depth: int (0-3)                     →  DepthBadge 컴포넌트
  0 → "summary"   --depth-0 (#00cc88)
  1 → "context"   --depth-1 (#3b82f6)   ← 기본값
  2 → "detailed"  --depth-2 (#f59e0b)
  3 → "full"      --depth-3 (#666666)
source: str                          →  SourceBadge
  "conversation" → 💬
  "github"       → 🐙 (sync 아이콘)
  "manual"       → ✏️
tags: tuple[str, ...]                →  TagPill 컴포넌트 리스트
                                        필터 클릭 시 해당 태그로 필터링
superseded_by: str | None            →  SupersedeChain 시각화
  None       → 활성 메모리 (정상 표시)
  "_deleted" → 소프트 삭제 (UI에서 숨김)
  다른 ID   → 대체됨 (체인 추적 가능)
created_at: str                      →  생성일 표시
updated_at: str                      →  "N일 전" + stale 판단
```

### Store 메서드 → API 엔드포인트 → UI 페이지 매핑

| Store 메서드 | 반환 타입 | 사용하는 UI 페이지 | 주요 파라미터 |
|-------------|----------|-------------------|-------------|
| `list_projects(status?)` | `list[Project]` | Dashboard (메인), Sidebar | status로 그룹핑 |
| `get_project(id)` | `Project \| None` | Project Detail 헤더 | - |
| `recall(project_id?, depth, max_chars, tags?)` | `(dict[str, list[Memory]], stats)` | Project Detail 메모리 리스트 | depth 슬라이더, 태그 필터 |
| `search(query, project_id?, tags?, limit)` | `list[Memory]` | Search 페이지, Cmd+K 결과 | 실시간 검색 |
| `save_memory(project_id, content, depth, source, tags?)` | `Memory` | Save 다이얼로그 | - |
| `update_memory(memory_id, content?, depth?, tags?)` | `Memory \| None` | Memory Detail 인라인 편집 | prefix ID 지원 |
| `delete_memory(memory_id)` | `bool` | Memory Row 삭제 버튼, Bulk 삭제 | prefix ID 지원 |
| `update_project(id, **kwargs)` | `Project` | Project 설정 편집 | name, status, summary, github_repo |
| `create_project(id, name, summary?, github_repo?)` | `Project` | New Project 다이얼로그 | - |
| `supersede_memory(old_id, new_id)` | `bool` | SupersedeChain 시각화 (읽기 전용) | - |

### recall() 반환값 상세 — 대시보드 핵심 데이터

```python
# recall()은 두 값을 반환:
memories_by_project: dict[str, list[Memory]]  # project_id → 메모리 리스트
stats: dict[str, int] = {
    "chars_loaded": int,     # 로드된 총 문자 수 → CharBudgetBar 분자
    "chars_budget": int,     # max_chars 예산 → CharBudgetBar 분모
    "memories_loaded": int,  # 로드된 메모리 수 → "N memories loaded" 표시
    "memories_dropped": int, # 예산 초과로 빠진 수 → "N dropped" 경고
}
# 정렬: depth ASC, updated_at DESC
# 필터: superseded_by IS NULL (활성만), depth <= 요청값
```

### 대시보드에서 필요하지만 현재 Store에 없는 데이터

| 필요한 데이터 | 현재 상태 | 해결 방안 |
|-------------|----------|---------|
| Supersede 체인 (역방향 추적) | `superseded_by`는 순방향만 저장. "이 메모리를 대체한 메모리"는 있지만 "이 메모리가 대체한 메모리"는 쿼리 필요 | `WHERE superseded_by = :current_id` 역쿼리 추가 |
| 프로젝트별 depth 분포 | 없음 (매번 계산 필요) | `GROUP BY depth` 집계 쿼리 또는 API 레벨 캐시 |
| 태그 자동완성 목록 | 없음 | `SELECT DISTINCT tag FROM memory_tags` 쿼리 추가 |
| 최근 사용 메모리 | usage.jsonl에만 있음 | usage.jsonl 파싱 또는 별도 recent 테이블 |
| 전체 통계 (총 메모리 수, 프로젝트 수) | `list_projects()`에서 산출 가능 | Dashboard stat 카드용 집계 쿼리 추가 고려 |

### REST API 레이어 결정

현재 MCP Streamable HTTP는 도구 호출용 프로토콜이지 REST API가 아니다. 대시보드 옵션:

**Option A: MCP 도구 직접 호출 (현재 설계)**
- `POST /mcp` → `call_tool("muninn_status")` 형태
- 장점: 추가 코드 없음, 기존 인프라 재사용
- 단점: 문자열 반환 → JSON 파싱 필요, 비효율적

**Option B: store.py 직접 임포트하는 REST API (추천)**
- `server.py`에 FastAPI/Starlette 라우트 추가
- `GET /api/projects` → `store.list_projects()` → JSON 직접 반환
- `GET /api/projects/:id/memories` → `store.recall()` → 구조화된 JSON
- 장점: 타입 안전, 효율적, 프론트엔드 친화
- 단점: 새 API 레이어 코드 필요

**Option C: 하이브리드**
- 읽기 작업 → REST API (빈번, 성능 중요)
- 쓰기 작업 → MCP 도구 재사용 (이미 검증됨)

→ **Option B 추천.** dataclass를 `asdict()`로 JSON 직렬화하면 깔끔하다.

---

## 5. 구현 로드맵

### Step 1: 프로젝트 스캐폴딩 (Day 1)

```
web/                          ← 새 디렉터리
├── package.json
├── next.config.ts
├── tailwind.config.ts
├── tsconfig.json
├── components.json            (shadcn/ui 설정)
├── public/
├── src/
│   ├── app/
│   │   ├── layout.tsx         (Geist 폰트, 테마)
│   │   ├── page.tsx           (Dashboard)
│   │   ├── projects/
│   │   │   └── [name]/
│   │   │       ├── page.tsx   (Project Detail)
│   │   │       └── [id]/
│   │   │           └── page.tsx (Memory Detail)
│   │   ├── search/
│   │   │   └── page.tsx
│   │   └── settings/
│   │       └── page.tsx
│   ├── components/
│   │   ├── ui/                (shadcn/ui 컴포넌트)
│   │   ├── layout/
│   │   │   ├── sidebar.tsx
│   │   │   ├── header.tsx
│   │   │   └── command-palette.tsx
│   │   └── muninn/
│   │       ├── project-card.tsx
│   │       ├── memory-row.tsx
│   │       ├── depth-badge.tsx
│   │       ├── status-indicator.tsx
│   │       ├── tag-pill.tsx
│   │       ├── supersede-chain.tsx
│   │       ├── freshness-indicator.tsx
│   │       └── char-budget-bar.tsx
│   ├── lib/
│   │   ├── api.ts             (Muninn HTTP API 클라이언트)
│   │   ├── store.ts           (Zustand 상태)
│   │   └── utils.ts
│   └── styles/
│       └── globals.css        (디자인 토큰)
└── .env.local                 (MUNINN_API_URL, MUNINN_API_KEY)
```

### Step 2: 디자인 시스템 + 레이아웃 (Day 2)

- [ ] shadcn/ui 초기화 (`npx shadcn@latest init`)
- [ ] Geist 폰트 설치 (`geist` npm 패키지)
- [ ] 디자인 토큰 → globals.css
- [ ] 사이드바 레이아웃 (collapsible)
- [ ] 헤더 + Command Palette (shadcn Command)
- [ ] Dark/Light 모드 토글

### Step 3: API 클라이언트 (Day 3)

- [ ] Muninn HTTP API 타입 정의 (TypeScript)
- [ ] fetch wrapper (Bearer token auth)
- [ ] React Query hooks: `useProjects`, `useMemories`, `useSearch`
- [ ] 에러 핸들링 + 로딩 상태

### Step 4: 핵심 페이지 구현 (Day 4-6)

- [ ] Dashboard — 통계 카드 + 프로젝트 리스트
- [ ] Project Detail — 메모리 테이블 + 필터 + depth 토글
- [ ] Memory Detail — 콘텐츠 뷰 + 인라인 편집 + supersede 체인
- [ ] Search — 전역 FTS 검색 결과
- [ ] Bulk 관리 — 멀티 셀렉트 + 일괄 삭제/태그

### Step 5: 인터랙션 + 폴리시 (Day 7)

- [ ] Cmd+K 커맨드 팔레트 (검색, 네비게이션, 액션)
- [ ] 키보드 단축키 (j/k 네비게이션, e 편집, d 삭제)
- [ ] Toast 알림 (저장/삭제 확인)
- [ ] 반응형 (모바일에서도 사용 가능)
- [ ] 애니메이션 (페이지 전환, 리스트 갱신)

### Step 6: 통합 + 배포 (Day 8)

- [ ] Docker 통합 (Next.js + Muninn 서버 함께 실행)
- [ ] 프록시 설정 (Next.js → Muninn HTTP API)
- [ ] README 업데이트
- [ ] E2E 테스트 (Playwright)

---

## 6. API 연동 설계

Muninn의 기존 MCP 도구를 HTTP API로 활용:

| Dashboard 기능 | MCP Tool | HTTP Endpoint |
|---------------|----------|---------------|
| 프로젝트 목록 | `muninn_status` | `POST /mcp` (tool call) |
| 프로젝트 상세 | `muninn_recall` | `POST /mcp` (tool call) |
| 메모리 검색 | `muninn_search` | `POST /mcp` (tool call) |
| 메모리 저장 | `muninn_save` | `POST /mcp` (tool call) |
| 메모리 편집 | `muninn_manage` (update) | `POST /mcp` (tool call) |
| 메모리 삭제 | `muninn_manage` (delete) | `POST /mcp` (tool call) |
| 상태 변경 | `muninn_manage` (set_status) | `POST /mcp` (tool call) |
| 프로젝트 생성 | `muninn_manage` (create) | `POST /mcp` (tool call) |
| GitHub 동기화 | `muninn_sync` | `POST /mcp` (tool call) |

**대안 고려:** MCP Streamable HTTP를 직접 호출하는 것이 복잡할 경우, 별도의 REST API 레이어를 `server.py`에 추가하는 것도 검토. `store.py`를 직접 임포트하면 더 간단한 JSON API 구축 가능.

---

## 7. 리스크 & 미결 사항

| 리스크 | 대응 |
|-------|------|
| MCP Streamable HTTP가 대시보드 API로 적합한지 | 프로토타입 단계에서 검증. 필요시 REST wrapper 추가 |
| Next.js가 Python 프로젝트에 맞는지 | `web/` 서브디렉터리로 분리. Docker multi-service로 배포 |
| 실시간 업데이트 필요성 | Phase 3 v1은 폴링. v2에서 SSE/WebSocket 고려 |
| 인증 통합 | 기존 Bearer token (`MUNINN_API_KEY`) 재사용 |

---

## 8. Non-Negotiable UX 요구사항

2025-2026 개발자 도구 UX 트렌드에서 도출한 필수 기능:

1. **Command Palette (Cmd+K)** — save, recall, search, manage 모든 작업 진입점. cmdk 라이브러리 (Linear/Raycast 사용)
2. **Dark Mode First** — 다크를 디폴트로 디자인하고, 라이트 모드는 검증. 개발자 문화적 기대
3. **Keyboard-Navigable** — `j/k` 리스트 이동, `e` 편집, `d` 삭제, `Enter` 확인, `Esc` 닫기. WAI-ARIA 컴플라이언스
4. **Monospace Rendering** — 메모리 ID (prefix matching이 핵심 기능), 타임스탬프, 코드 블록에 Geist Mono
5. **Depth Indicators** — 색상 + 공간적 계층 동시 사용 (색상만으로는 부족)
6. **Project Switcher** — 사이드바에서 Vercel의 "project-as-filter" 패턴
7. **Status Badges** — active/paused/idea/archived 상태가 한눈에
8. **Functional Color Tokens** — `bgColor-default`, `fgColor-muted` 등 시맨틱 토큰. 테마 전환 시 자동 적응
9. **Content Density Control** — 개발자는 화면당 더 많은 정보를 원함. 밀도 높되 타이포그래피 계층으로 클러터 방지
10. **`font-variant-numeric: tabular-nums`** — 데이터 컬럼 정렬을 위해 고정폭 숫자

---

## References

- [Vercel Geist Design System](https://vercel.com/geist/introduction)
- [Vercel Dashboard Redesign](https://vercel.com/blog/dashboard-redesign)
- [Linear UI Redesign](https://linear.app/now/how-we-redesigned-the-linear-ui)
- [Linear uses Radix Primitives](https://www.radix-ui.com/primitives/case-studies/linear)
- [shadcn/ui](https://ui.shadcn.com/)
- [Supabase UI Library](https://supabase.com/ui)
- [Supabase Design System (DeepWiki)](https://deepwiki.com/supabase/supabase/2.5-design-system-and-ui-library)
- [Railway UI Screens (NicelyDone)](https://nicelydone.club/apps/railway)
- [Best shadcn Dashboard Templates 2026](https://adminlte.io/blog/shadcn-admin-dashboard-templates/)
- [shadcn-admin (GitHub)](https://github.com/satnaing/shadcn-admin)
- [Geist Font](https://vercel.com/font)
