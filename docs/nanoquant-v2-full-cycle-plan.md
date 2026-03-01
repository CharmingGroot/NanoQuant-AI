# NanoQuant AI v2 — 전 과정 기획·디자인·개발 방향·검토

사용자 요청에 따른 full-cycle 기획 개선안.  
**목표**: 현재 UI/기능을 실용적으로 개선하고, 지식그래프 기반 “성장형” 퀀트 에이전트로 서비스화한다. **OpenClaw 스타일 3단계 아키텍처**(Interface → Control/ReAct → Execution/Skills)를 그대로 반영하고, ReAct 단일 루프·DAG 미사용·도구/스킬 확장·HITL 최소화를 따른다.

---

## 1단계: 기획 (Planner)

### 1.1 요구사항 요약

| 항목 | 내용 |
|------|------|
| **목표** | 실제 사용자 관점에서 더 실용적인 “성장형” 퀀트 트레이딩 에이전트 서비스 |
| **대상 사용자** | 퀀트/트레이딩 관심 사용자, 지시만 내리면 에이전트가 작업 수행 |
| **핵심 가치** | 지시 → 자동 실행 → 필요 시에만 HITL, 도구/스킬 자유 확장, 모든 작업 후 Reflection |

### 1.2 기능 목록 (우선순위)

**Must (필수)**

- 지식그래프 도입: 퀀트 지표·규칙·판단 이력을 그래프로 저장·활용하여 에이전트가 “성장”하도록 설계
- **ReAct(Reasoning + Acting) 단일 루프**만 사용. **DAG(LangGraph 등) 미도입** — 노드/엣지 그래프 없이 “생각 → 행동 → 관찰” 반복으로 완료 시까지 진행
- LangChain/LangGraph·DAG 미사용. **자체 ReAct 루프**로 구현 (필요 시 CrewAI/AutoGen 등 오픈소스는 “참고만”, 그래프 구조는 쓰지 않음)
- **도구(Tool)**·**스킬(Skill)** 추가가 자유로워, 새 퀀트 수식/지표가 들어와도 에이전트가 자연스럽게 처리
- 사용자 “지시”만으로 작업 수행, **필요 시에만 HITL** 발생
- **모든 작업 후 Reflection**: 현재 작업이 잘 되었는지 검토하고, 실패/불만족 시 재시도
- UI에 **AI 채팅 세션** 포함 → 대화형으로 지시·확인·HITL
- **채팅 세션 구분·관리**: 세션별로 대화가 명확히 구분되고, 여타 AI 서비스처럼 세션 목록 조회·새 대화 생성·세션 전환·세션 삭제가 가능해야 함.

**Should (권장)**

- **OpenClaw 아키텍처 반영**: Interface Layer(게이트웨이) → Control Layer(ReAct 루프) → Execution Layer(Skills·Sandboxing). Standard Message·Session·Self-Correction·Spawn(서브에이전트) 개념 적용
- 서비스화: 단일 실행 파일/배치가 아닌, 웹 또는 로컬 서비스로 상시 대기
- 기존 Layer1~3·quant_rules·DB·시뮬레이션 포트폴리오는 유지하되, “에이전트 한 번 감싸는” 형태로 통합

**Could (선택)**

- 멀티 에이전트(기획/실행/검토 분리), 대시보드 고도화, 텔레그램/슬랙 알림

### 1.3 사용자 스토리·시나리오

- **US-1**  
  사용자: “이 종목 RSI 기반으로 매매 시그널 봐줘”  
  시스템: 해당 퀀트 수식(RSI)을 도구/스킬로 해석 → 실행 → 결과 반환 → Reflection 후 사용자에게 응답(필요 시 HITL).

- **US-2**  
  사용자: “지금 보유 종목 정리하고, 손절선만 다시 잡아줘”  
  시스템: 포지션 조회 도구 + 정리/손절 규칙 스킬 호출 → 실행 → Reflection → 응답.

- **US-3**  
  사용자: (채팅) “새 지표 공식 추가해줘: Stochastic %K 14”  
  시스템: 스킬/도구 등록 플로우 → 검증 → 지식그래프/레지스트리 업데이트 → Reflection → “추가했고, 이제 ~에서 사용됩니다” 응답.

- **US-4**  
  사용자: (채팅) “오늘 스캔 결과 요약해줘”  
  시스템: 스캔 결과 조회 도구 + 요약 스킬 → 실행 → Reflection → 채팅으로 요약 응답.

### 1.4 비기능 요구사항

- **확장성**: 새 퀀트 수식/도구/스킬 추가 시 기존 코드 대규모 수정 없이 등록만으로 동작
- **투명성**: 어떤 도구/스킬이 호출되었는지, Reflection 결과(성공/재시도)를 사용자에게 노출 가능
- **안정성**: 에이전트 루프 장애 시 기존 시뮬레이션/DB/스캔은 독립적으로 동작 가능하도록 분리

### 1.5 제약·가정·미정 사항

| 항목 | 내용 |
|------|------|
| **제약** | LangChain/LangGraph·DAG 미사용; 에이전트는 ReAct 단일 루프만 사용; **서비스·API·UI는 OpenClaw와 동일 스택**(Node.js ≥22, TypeScript, ESM, pnpm, Express, ws, Vite+Lit 등, 1.6 참고); 퀀트 데이터·연산은 기존 yfinance·SQLite·시뮬레이션 활용(또는 Node에서 호출) |
| **가정** | 지식그래프는 1단계에서 “판단 이력 + 지표 메타데이터” 수준으로 시작해 점진 확장 |
| **미정** | 지식그래프 저장소(Neo4j vs 네이티브 그래프 vs SQLite 관계 테이블). UI·백엔드 스택은 아래 1.6 확정. |

### 1.6 기술 스택 (UI · 백엔드) — OpenClaw 프로젝트 기준

**[OpenClaw](https://github.com/openclaw/openclaw)에서 실제 사용 중인 스택을 그대로 반영한다.** 에이전트 서비스·API·대시보드는 동일한 런타임·언어로 맞추어 확장·타입 공유·유지보수를 단순화한다.

#### OpenClaw에서 사용하는 스택 (참고)

| 구분 | OpenClaw 실제 스택 | 비고 |
|------|-------------------|------|
| **런타임** | **Node.js ≥ 22** | `engines.node: ">=22.12.0"` |
| **언어** | **TypeScript** | 코드베이스 대부분 TS. ESM(`"type": "module"`) |
| **패키지 매니저** | **pnpm** | `pnpm-workspace.yaml` — 루트, `ui`, `packages/*`, `extensions/*` |
| **백엔드** | **Express 5.x** | Gateway HTTP 서버. `express: ^5.2.1` |
| | **WebSocket (ws)** | Gateway 제어 평면. `ws: ^8.19.0` |
| | **dotenv, zod** | 설정·환경변수·스키마 검증 |
| **UI (Control UI)** | **Vite + Lit** | 단일 페이지 앱. Gateway가 정적 제공. WebSocket으로 Gateway와 통신 |
| | **Lit** | `lit`, `@lit-labs/signals`, `@lit/context` (devDependencies). 웹 컴포넌트 기반 |
| **빌드** | **tsdown** | TS 번들. `tsx`로 개발 시 TS 직접 실행 |
| **테스트** | **Vitest** | 단위·e2e·gateway 등 `vitest.*.config.ts` |
| **포맷·린트** | **oxfmt, oxlint** | 포맷터·린터 (TypeScript 네이티브) |
| **스키마·검증** | **@sinclair/typebox, ajv, zod** | JSON 스키마·런타임 검증 |

#### NanoQuant AI v2 적용안 (OpenClaw 스택 그대로 반영)

| 구분 | 스택 | 비고 |
|------|------|------|
| **UI Stack** | **TypeScript** | 전 구간 타입 통일 |
| | **Vite + Lit** | OpenClaw Control UI와 동일. SPA, Gateway(또는 API 서버)가 제공 또는 별도 정적 호스팅 |
| | **WebSocket (ws)** | 채팅·에이전트 이벤트 스트리밍 시 Gateway와 동일하게 WS 사용 권장 |
| | 스타일 | 다크 테마·모노스페이스 톤 유지. (OpenClaw는 Tailwind 미사용, 커스텀 스타일) |
| **백엔드 Stack** | **Node.js ≥ 22** | OpenClaw와 동일 런타임 |
| | **TypeScript (ESM)** | `"type": "module"` |
| | **Express 5.x** | REST API + (선택) WebSocket 서버. 채팅·에이전트·스킬·HITL·KG API |
| | **ws** | 세션·스트리밍용 WebSocket |
| | **dotenv, zod** | 설정·요청 검증 |
| **패키지 구조** | **pnpm workspace** | 예: `apps/web`(UI), `apps/api` 또는 `packages/gateway`(에이전트·ReAct), `packages/skills` |
| **빌드·개발** | **tsdown, tsx** | 프로덕션 빌드·개발 시 TS 실행 |
| **테스트** | **Vitest** | 단위·통합·e2e |
| **스키마·검증** | **TypeBox 또는 zod** | API 스키마·Standard Message 등 검증 |

- **퀀트 연산·데이터**: 기존 Python(yfinance, quant_rules, SQLite)은 Node에서 자식 프로세스/HTTP로 호출하거나, 점진적으로 Node/TS로 이식. 1단계에서는 “실행 가능한 스킬”로만 노출해도 무방.
- **정리**: OpenClaw와 동일하게 **Node.js ≥22, TypeScript, ESM, pnpm workspace, Express, ws, Vite + Lit, Vitest** 를 기준으로 한다. UI는 React 대신 **Lit**(OpenClaw Control UI와 동일) 사용을 권장하며, React 선호 시 커뮤니티 클라이언트(예: ClawUI는 React + Vite + Electron)처럼 별도 클라이언트로 두는 선택 가능.

---

## 2단계: 디자인 (Designer)

### 2.1 정보 구조(IA)

```
[서비스 루트]
├── 대시보드 (포트폴리오·스캔 요약·최근 결정)
├── AI 채팅 (세션별 대화 구분, 세션 관리: 목록·새 대화·전환·삭제, 지시·HITL·결과)
├── 모니터 (실시간 스캔/트리거 결과, 기존 DB 뷰어 연계)
├── 설정 (워치리스트, 도구/스킬 목록 조회, HITL 기본 동작, LLM API 키 입력)
└── 지식그래프 뷰어 (필수)
```

### 2.2 화면/플로우

- **메인**: 대시보드 + 사이드/하단 **AI 채팅 패널** (항상 접근 가능).
- **채팅 플로우**:  
  사용자 메시지 입력 → **ReAct 루프**: Reason(생각 + 도구/스킬 선택 또는 최종 답변) → Act(도구 실행) → Observe(결과를 LLM에 반영) → 반복. LLM이 최종 답변을 낼 때까지 루프. Reflection은 도구로 호출하거나 Reason 단계에서 “결과 만족 여부·재시도” 판단에 포함.  
  HITL 필요 시 채팅 내에서 “확인/거부/수정” 버튼 또는 단일 승인 플로우.
- **모니터**: 기존 DB 뷰어(결정/리플렉션/모니터 스냅샷)와 동일한 데이터 소스, 탭/페이지로 통합 또는 링크로 연결.

### 2.3 UI 요구사항 (와이어프레임 수준)

- **AI 채팅 세션**
  - **세션 구분**: 세션별로 대화 내용이 분리되어 표시되며, 현재 선택된 세션만 활성 채팅으로 표시.
  - **세션 관리**: 여타 AI 서비스와 동일하게 (1) 세션 목록 표시(사이드바 또는 드롭다운), (2) “새 대화”로 새 세션 생성, (3) 목록에서 클릭 시 해당 세션으로 전환, (4) 세션 삭제(선택). 세션 제목은 첫 사용자 메시지 요약 또는 “대화 1”, “대화 2” 등으로 표시.
  - 세션별 히스토리 유지(브라우저 새로고침 시 복구 가능하면 유리).
  - 메시지별 “사용된 도구/스킬” 배지 또는 접기/펼치기.
  - “Reflection: OK / Retry” 등 상태 표시.
  - HITL 시: 버튼(예: “실행 허용”, “취소”) 또는 짧은 폼.
- **설정**
  - **스킬·도구 목록**: `GET /agent/skills`로 목록 조회 후 테이블 또는 리스트로 표시(이름, 설명, 파라미터, HITL 여부).
  - **API 키 입력**: 에이전트 채팅 사용을 위한 LLM API 키 입력란. 제공자(Claude/OpenAI)·키·모델 선택 후 저장(클라이언트 localStorage). 채팅 요청 시 본문에 키를 실어 보내고, 서버는 해당 요청에만 사용(서버 비저장).
- **대시보드**
  - 포트폴리오 요약(현금, 포지션, P/L), 최근 스캔/트리거 요약, 최근 결정 1줄 요약.
- **일관성**
  - 기존 DB 뷰어와 동일한 톤(다크 테마, 모노스페이스) 유지 권장.
  - 네비게이션: “대시보드 | 채팅 | 모니터 | 설정”.

### 2.4 상태·예외

- **로딩**: 채팅 응답 대기 시 스피너 또는 “Thinking… / Acting…” 등 ReAct 단계 표시.
- **에러**: 도구/스킬 실패 시 채팅에 에러 메시지 + “재시도” 옵션.
- **HITL 대기**: 사용자 응답 전까지 다음 Execution 블록 대기, 타임아웃 시 “취소됨” 처리.

---

## 3단계: 개발 방향 (Developer)

### 3.0 OpenClaw 스타일 시스템 아키텍처 (3단계 레이어)

NanoQuant AI v2는 **OpenClaw**와 동일한 3단계 구조를 채택한다. 중앙 집중형 DAG가 아니라 “분산형 기술 집합(Skill Set)”을 LLM이 그때그때 조립해서 쓰는 에이전트형 구조다.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ ① Interface Layer (The Gateway)                                             │
│    역할: 사용자와의 접점 관리 및 입력 표준화                                   │
│    - 웹 채팅, (선택) Telegram/Discord 등 → Standard Message 포맷으로 변환     │
│    - 사용자별/채널별 Session ID 부여 → 대화 맥락(Memory) 유지                 │
└─────────────────────────────────────────────────────────────────────────────┘
                                        ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│ ② Control Layer (The Brain / ReAct Loop)                                     │
│    역할: 작업 계획(Planning) 및 도구/스킬 선택                                 │
│    - 고정된 순서도(DAG) 없음. 자율 ReAct 루프만 사용.                         │
│    - Reasoning: LLM이 현재 메시지 + 가용 Skills 목록 → “어떤 기술이 필요한가?” │
│    - Decision: 실행할 스킬명 + 인자(Arguments)를 JSON으로 도출                │
│    - Self-Correction: 도구 실행 결과가 에러면 → Observation으로 다시 입력 →   │
│      루프 내에서 스스로 교정(재시도 또는 대안 선택)                            │
└─────────────────────────────────────────────────────────────────────────────┘
                                        ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│ ③ Execution Layer (The Skills & Sandboxing)                                 │
│    역할: 실제 작업 수행 (팔과 다리)                                            │
│    - Skills: Python으로 작성된 독립 함수 모듈 (예: get_rsi, scan_candidates,  │
│      get_portfolio, summarize_scan). 새 스킬 = 새 모듈 등록만 하면 됨.        │
│    - Sub-Agent (Spawn): 복잡한 작업 시 spawn_agent 스킬로 자식 에이전트를     │
│      동적으로 생성. 미리 연결된 DAG 노드가 아니라 런타임 계층형 트리.           │
└─────────────────────────────────────────────────────────────────────────────┘
```

#### ① Interface Layer (Gateway)

| 항목 | 내용 |
|------|------|
| **역할** | 사용자 접점 관리, 입력 표준화 |
| **입력** | 웹 채팅 메시지, (선택) Telegram/Discord 등 |
| **출력** | **Standard Message** 포맷 (예: `{ session_id, user_id, channel?, content, timestamp }`) |
| **상태** | 사용자별/채널별 **Session ID** → 대화 이력(Memory) 유지, ReAct에 맥락 전달 |

#### ② Control Layer (Brain / ReAct Loop)

| 항목 | 내용 |
|------|------|
| **역할** | 작업 계획 및 도구/스킬 선택 |
| **메커니즘** | LangGraph 같은 고정 DAG 없음. **ReAct 자율 루프**만 사용. |
| **Reasoning** | LLM이 현재 메시지 + 가용 Skills 목록을 보고 “어떤 기술이 필요한가?” 판단 |
| **Decision** | 실행할 스킬명 + 인자(Arguments)를 **JSON** 형태로 도출 |
| **Self-Correction** | 도구 실행 결과가 에러일 경우 → 이를 **Observation**으로 다시 입력 → 루프 내에서 스스로 교정 |

#### ③ Execution Layer (Skills & Sandboxing)

| 항목 | 내용 |
|------|------|
| **역할** | 실제 물리적/논리적 작업 수행 |
| **Skills** | Python 독립 함수 모듈 (예: `get_rsi`, `scan_candidates`, `get_portfolio`, `summarize_scan`). 새 스킬 = 새 모듈 추가 후 레지스트리 등록. |
| **Sub-Agent (Spawn)** | 복잡한 작업 시 `spawn_agent` 스킬로 **자식 에이전트**를 동적 생성. DAG처럼 미리 연결된 노드가 아니라, 필요에 따라 런타임에 생성되는 계층형 트리. |

#### 데이터 흐름 예시

- **입력**: 사용자가 채팅으로 “오늘 스캔 결과 요약해줘” 전송.
- **Gateway**: Standard Message로 변환, Session ID로 이력 조회.
- **Control**: Main Agent가 `scan_candidates` + `summarize_scan` 스킬이 필요하다고 판단, JSON으로 도출.
- **Execution**: Executor가 스킬 실행 → 스캔 결과·요약 반환.
- **확장**: 스캔 대상이 많으면 `spawn_agent`로 “종목별 분석” 서브 에이전트 여러 개 띄워 병렬 처리 가능.
- **취합**: 서브 에이전트 결과를 메인이 취합 → 사용자에게 최종 응답.

#### LangGraph vs OpenClaw(본 프로젝트) 비교

| 항목 | LangGraph (DAG) | NanoQuant v2 (OpenClaw 스타일) |
|------|------------------|----------------------------------|
| **흐름 제어** | Static: 미리 정의된 엣지(Edge) | Dynamic: 실시간 추론에 의한 스킬 선택 |
| **확장 방식** | 노드 추가 및 그래프 재빌드 | 새 Skill 모듈 추가 후 레지스트리 등록 |
| **상태 전이** | State 객체의 엄격한 업데이트 | 대화 이력(History) 기반의 유연한 맥락 |
| **구조** | 중앙 집중형 그래프 | 분산형 기술 집합(Skill Set)을 LLM이 조립 |

---

### 3.1 스택 제안 (ReAct 단일 루프, DAG 미사용)

- **에이전트 코어**: **ReAct(Reasoning + Acting) 단일 루프**만 사용. DAG(LangGraph 등)는 도입하지 않음.  
  - 루프: `while not done: Reason(LLM) → [도구 호출이면] Act → Observe → Reason → …`  
  - LLM이 “최종 답변”을 내면 루프 종료.  
  - **Reflection**: (A) 도구 `reflect(이전_액션, 결과)` 로 에이전트가 스스로 호출, 또는 (B) Reason 프롬프트에 “지난 결과가 만족스러운가? 재시도할 것인가?” 포함. 권장: A+C(필요 시 reflect 도구 호출 + Reason에서도 결과 검토).
- **도구/스킬 레지스트리**:  
  - **도구**: 이름, 설명, 파라미터 스키마, 실행 함수를 등록하는 레지스트리(예: `ToolRegistry.register("get_rsi", ...)`).  
  - **스킬**: “언제 쓰는지” 설명 + 내부적으로 여러 도구/다른 스킬 조합 가능한 단위. 새 퀀트 수식은 “새 도구” 또는 “기존 도구 조합 스킬”로 추가.
- **LLM 호출**: 기존처럼 Claude/GPT API 직접 호출 유지. (LangChain 의존 제거)
- **지식그래프**:  
  - 1단계: SQLite 또는 in-memory 그래프(노드: 지표, 규칙, 판단; 엣지: 사용됨, 선행/후행).  
  - 이후 필요 시 Neo4j 또는 NetworkX 기반 영구 저장으로 확장.

### 3.2 Control Layer 내부: ReAct 루프 (DAG 없음)

아래는 **② Control Layer** 안에서만 도는 ReAct 루프이다. Gateway에서 넘어온 Standard Message + Session Memory가 입력이 된다.

```
[Standard Message + Session History]
        ↓
   ┌───────────────────────────────────────────────────────────┐
   │  Control Layer 내부 — ReAct 루프 (최종 답변 나올 때까지)    │
   │                                                            │
   │   ┌─────────────┐    ┌─────────────┐    ┌─────────────┐   │
   │   │   Reason    │ →  │    Act      │ →  │   Observe   │   │
   │   │ (생각+결정)  │    │ (Skill 실행) │    │ (결과 반영)  │   │
   │   │ Skill명+인자 │    │ Execution   │    │ Self-Correct │   │
   │   └──────┬──────┘    │ Layer 호출  │    └──────┬──────┘   │
   │          │           └─────────────┘           │          │
   │          │  Skill 호출 아님 & 최종 답변         │          │
   │          └────────────────────────────────────┘          │
   │                          ↓                                 │
   │                    (에러 시 Observation으로 재입력)         │
   └───────────────────────────────────────────────────────────┘
        ↓ (루프 탈출 시)
   [Response] Gateway로 반환 → 사용자에게 채팅 응답. (HITL은 Act 직전에만)
```

- **DAG 미사용**: 하나의 ReAct 스텝만 반복. 노드/엣지 그래프 없음.
- **Self-Correction**: 도구 실행 결과가 에러면 그대로 Observation으로 넣고 Reason 재진행.
- **Reflection**: Reason 단계에서 “결과 만족 여부·재시도” 판단 또는 `reflect` 스킬 호출.
- **HITL**: 위험 실행 시 Act 직전에만 사용자 확인.

### 3.3 구현 포인트 (OpenClaw 3단계 기준)

1. **Interface Layer (Gateway)**  
   - 채팅/메시지 수신 → **Standard Message** 포맷으로 정규화 (`session_id`, `user_id`, `content`, `timestamp` 등).  
   - **Session ID** 부여 및 대화 이력(Memory) 저장·조회. Control Layer에 넘길 때 이력 포함.
2. **Control Layer (ReAct)**  
   - Standard Message + Session History → Reason(LLM: 가용 Skills 목록 보고 스킬명+인자 JSON 도출) → Act(Execution Layer 호출) → Observe(결과 또는 에러를 Observation으로 반영) → 반복. 최종 답변 시 루프 종료.  
   - **Self-Correction**: 실행 에러를 그대로 Observation으로 넣어 루프 내에서 재판단.  
   - **Reflection**: Reason에서 결과 검토 또는 `reflect` 스킬 호출.
3. **Execution Layer (Skills)**  
   - **도구/스킬 레지스트리**: `quant_rules`(RSI, SMA, MACD 등) + 스캔/포지션/요약 등 Python 함수를 스킬로 등록. 새 스킬 = 새 모듈 + `register` 한 번.  
   - **Spawn(선택)**: `spawn_agent` 스킬로 복잡한 작업 시 자식 에이전트 동적 생성. DAG가 아닌 런타임 계층형 트리.
4. **지식그래프**  
   - “어떤 지표/규칙이 어떤 판단에 쓰였는지” 기록.  
   - 나중에 “비슷한 상황에서 과거 어떤 조합이 성과가 좋았는지” 조회용으로 확장.
5. **서비스화**  
   - Flask/FastAPI로 Gateway·채팅 API 제공.  
   - 기존 `main.py` Layer1~3는 그대로 두고, Interface/Control/Execution를 “에이전트 서비스”로 붙임.

### 3.4 테스트·문서

- 도구/스킬 등록·호출 단위 테스트.
- ReAct 한 사이클(Reason → Act → Observe 반복 → 최종 응답) 통합 테스트.
- API 명세(채팅 메시지 요청/응답, HITL 승인 요청) 문서화.

---

## 4단계: 검토 (Reviewer)

### 4.1 검토 요약

요구사항(지식그래프, 성장형 에이전트, UI 채팅, 서비스화, **OpenClaw 스타일 3단계 아키텍처**(Interface → Control/ReAct → Execution), ReAct 단일 루프·DAG 미사용, 도구/스킬 자유 확장, Self-Correction·Reflection, HITL 최소)이 기획·디자인·개발 방향에 잘 반영되었다.  
다만 일부는 범위·우선순위를 더 좁혀야 하고, 지식그래프와 HITL 정책은 구체화가 필요하다.

### 4.2 잘된 점

- OpenClaw 3단계(Interface / Control-ReAct / Execution-Skills)를 그대로 반영해 역할 분리가 명확함. ReAct 단일 루프·DAG 미사용으로 구현 부담 적음.
- Standard Message·Session·Self-Correction·Spawn 개념을 도입해 확장·유지보수와 “분산형 Skill Set” 조립 방식이 정리됨.
- 도구/스킬 레지스트리로 “어떤 퀀트 수식이 들어와도 에이전트가 처리” 가능한 확장 경로가 명확함.
- 기존 Layer1~3·quant_rules·DB·시뮬레이션을 유지하면서 “에이전트 레이어”만 추가하는 전략이 리스크를 줄임.
- UI에 AI 채팅 세션을 넣고 서비스화하는 방향이 “지시만 내리면 수행” 요구와 맞음.

### 4.3 Critical (반드시 반영 권장)

- **Reflection 재시도 정책**: “재시도” 시 최대 횟수, 재시도 시 계획 수정 여부, 포기 조건을 명시할 것.
- **HITL 트리거 조건**: 어떤 액션(실제 매매, 워치리스트 변경, 도구/스킬 등록 등)에서 HITL을 거는지 목록화할 것.
- **지식그래프 스키마 초안**: 노드/엣지 타입을 1페이지로 정의해 두면 구현 시 일관성이 생김.

### 4.4 Suggestion (개선 권장)

- **Openclaw 참조**: Openclaw의 “요청 → 도구/스킬 호출” 플로우를 문서/코드로 참고해, 네이밍·플로우를 비슷하게 맞추면 사용자 기대와 맞기 쉬움.
- **채팅 세션 저장**: 세션을 DB 또는 파일로 저장해 재접속 후 복구 가능하게 하면 실용성 증가.
- **에이전트 구조**: OpenClaw 3단계(Interface·Control·Execution) + Control 내부는 ReAct 단일 루프. DAG 미사용. 스킬 시그니처는 “스킬명 + 인자 JSON → 결과 반환” 형태로 고정.

### 4.5 Nice to have

- **(지식그래프 뷰어는 필수)** 지식그래프 시각화 뷰어(노드/엣지 탐색) — 성장형 에이전트의 핵심이므로 선택이 아닌 필수 기능.
- “이번 대화에서 사용된 도구/스킬” 요약 리포트.

### 4.6 체크리스트

- [x] 목표·범위가 명확함 (성장형 퀀트 에이전트, 서비스화, OpenClaw 3단계·ReAct, 도구/스킬 확장)
- [x] Reflection 재시도·포기 정책 구체화 (부록 A)
- [x] HITL 트리거 조건 목록화 (부록 B)
- [x] 지식그래프 스키마 초안 작성 (부록 C)
- [x] 에이전트 구조 확정: ReAct 단일 루프, DAG 미사용
- [x] 채팅 API(요청/응답/HITL) 명세 (docs/agent-api-spec.md)

---

## 부록 A: Reflection 재시도 정책

| 항목 | 내용 |
|------|------|
| **재시도 최대 횟수** | 작업 단위당 최대 2회 재시도 (총 3회 시도) |
| **재시도 시 계획** | 1회 재시도: 동일 계획으로 Execution만 재실행. 2회 재시도: Planning 단계에서 계획 수정 허용(LLM에 이전 실패 이유 전달) |
| **포기 조건** | 3회 실패 시 사용자에게 “실패했으며, 수동 확인이 필요합니다” 응답 + 로그에 실패 이력 저장 |
| **성공 기준** | Reflection 단계에서 “작업 목표 달성”, “도구/스킬 반환값 유효” 판정 시 성공으로 간주 |

---

## 부록 B: HITL 트리거 조건

다음 액션 실행 전에 **반드시 사용자 확인**을 받는다.

| 트리거 | 설명 |
|--------|------|
| **실제 매매** | 시뮬레이션 모드가 아닐 때 BUY/SELL 실행 직전 |
| **워치리스트 대량 변경** | 한 번에 N종목 이상 추가/삭제 (N은 설정 가능, 기본 10) |
| **도구/스킬 등록·삭제** | 새 퀀트 수식·스킬을 레지스트리에 등록하거나 기존 항목 삭제 시 |
| **설정 변경** | 트리거 임계값, 손절/익절 비율, 최대 포지션 수 등 위험 관련 설정 변경 시 |
| **선택 HITL** | 사용자가 “항상 실행 전에 물어봐” 모드 설정 시, 모든 Execution 전 확인 |

HITL 미발생: 데이터 조회, 스캔 요약, 시뮬레이션 내 매매, 로그/리포트 생성 등.

---

## 부록 C: 지식그래프 스키마 초안

**1단계(최소)** — SQLite 또는 in-memory로 구현 가능.

| 노드 타입 | 속성 | 설명 |
|-----------|------|------|
| **Indicator** | id, name, formula_type, params_schema | 퀀트 지표(예: RSI, MACD) |
| **Rule** | id, name, condition_expr, action_hint | 규칙(예: RSI<30 → 과매도 시그널) |
| **Decision** | id, timestamp, ticker, action, outcome_summary | 판단 이력(기존 DB 결정 로그와 연계) |
| **Skill** | id, name, description, tool_ids | 스킬(어떤 도구 조합인지) |

| 엣지 타입 | from → to | 설명 |
|-----------|-----------|------|
| **used_in** | Decision → Indicator, Decision → Rule | 해당 판단에 어떤 지표/규칙이 사용되었는지 |
| **composes** | Skill → Tool/Indicator | 스킬이 어떤 도구/지표를 쓰는지 |
| **follows** | Decision → Decision | 이전 판단 대비 후속 판단(선택) |

**확장(2단계)**  
- 노드: UserQuery, Session.  
- 엣지: Query → used_tools, Session → Decision.  
- 성과 메타(수익률, 승률)를 Decision 또는 별도 노드에 연결해 “성장” 분석에 사용.

---

## 다음 액션 제안

지식그래프를 서비스(API·UI·에이전트)와 어떻게 엮을지: [지식그래프 서비스 연동](kg-service-integration.md) 참고.

1. **즉시**: Reflection 재시도 정책, HITL 트리거 목록, 지식그래프 스키마 초안은 부록 A·B·C에 반영됨. **Standard Message** 스키마와 **Session** 저장 방식(메모리/DB) 결정.
2. **단기**: Interface Layer(Gateway) 골격 + Standard Message 변환. Control Layer(ReAct) + Execution Layer(스킬 레지스트리) 설계 및 `quant_rules` 1차 스킬 등록.
3. **중기**: Flask/FastAPI로 Gateway·채팅 API + 단순 채팅 UI(기존 db_viewer 확장 또는 별도 탭) 구현.
4. **이후**: 지식그래프 1단계(판단 이력 + 지표 메타) 저장·조회. (선택) `spawn_agent` 스킬로 서브 에이전트 동적 생성.
