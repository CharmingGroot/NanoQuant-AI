# 메뉴별 상세 기획서

실시간 퀀트 에이전트 모니터링·통합 관리를 위한 **메뉴별·기능별** 상세 기획 문서 모음이다.  
원본 통합 정리는 [ui-features-monitoring-management.md](../ui-features-monitoring-management.md) 참고.

---

## 메뉴 구조

| 메뉴 | 폴더 | 설명 |
|------|------|------|
| **대시보드** | [dashboard/](dashboard/) | 포트폴리오·요약 카드·연결 상태·최근 결정 |
| **AI 채팅** | [chat/](chat/) | 세션 관리·대화·에이전트 제어·우측 스킬/도구 패널(강제 사용·툴팁)·HITL |
| **백테스트** | [backtest/](backtest/) | 기간·종목·전략·결과·에이전트 연동 |
| **모니터** | [monitor/](monitor/) | 실시간 활동 스트림 |
| **지식그래프** | [kg/](kg/) | KG 역할·쓰기/읽기·뷰어·API·영속성 |
| **설정** | [settings/](settings/) | API 키·스킬 목록·HITL·워치리스트 |
| **공통** | [common/](common/) | 네비게이션·반응형·빈/에러 상태·디자인 톤 |

---

## 폴더별 문서 목록

### [dashboard/](dashboard/)
- [01-overview.md](dashboard/01-overview.md) — 대시보드 역할·위치
- [02-portfolio.md](dashboard/02-portfolio.md) — 현재 포트폴리오 표시(P-1~P-5)·UI 상세
- [03-summary-and-monitoring.md](dashboard/03-summary-and-monitoring.md) — 연결 상태·스킬·세션·최근 결정
- [04-api.md](dashboard/04-api.md) — 포트폴리오·KG 연동 API

### [chat/](chat/)
- [01-overview.md](chat/01-overview.md) — 채팅 탭 역할·에이전트 제어 요약
- [02-session-role-and-features.md](chat/02-session-role-and-features.md) — 세션 정의·필수 기능(S-1~S-6)
- [03-session-list-ui.md](chat/03-session-list-ui.md) — 세션 목록 UI·레이아웃·반응형
- [04-session-delete-flow.md](chat/04-session-delete-flow.md) — 세션 삭제 플로우
- [05-session-title-flow.md](chat/05-session-title-flow.md) — 세션 제목 자동·수정 플로우
- [06-session-create-switch.md](chat/06-session-create-switch.md) — 새 세션 생성·전환
- [07-agent-control.md](chat/07-agent-control.md) — 지시 입력·히스토리·스킬 투명성·우측 스킬/도구 패널(C-8)·HITL·로딩·에러
- [08-api.md](chat/08-api.md) — 세션·채팅·HITL API

### [backtest/](backtest/)
- [01-overview.md](backtest/01-overview.md) — 백테스트 목적·에이전트와의 관계
- [02-features.md](backtest/02-features.md) — 기간·종목·전략·실행·결과(B-1~B-7)
- [03-ui-and-results.md](backtest/03-ui-and-results.md) — 탭 구성·입력 폼·결과 영역·이력
- [04-api-and-priority.md](backtest/04-api-and-priority.md) — API·스킬·우선순위
- [05-backtest-enhancement-plan.md](backtest/05-backtest-enhancement-plan.md) — **구체화·고도화 기획** (데이터·엔진·전략·UI·에이전트·로드맵)
- **도구 제공 방식**: Python 백테스트 서비스는 **MCP 서버**로 도구(`get_history`, `run_backtest`)를 노출. Skill 호출 시 Node가 MCP 클라이언트로 해당 도구 호출. → [mcp-backtest-integration.md](../mcp-backtest-integration.md)

### [monitor/](monitor/)
- [01-overview.md](monitor/01-overview.md) — 모니터 탭 역할
- [02-activity-and-api.md](monitor/02-activity-and-api.md) — 실시간 활동·API

### [kg/](kg/)
- [01-overview.md](kg/01-overview.md) — KG 역할·필수 요건
- [02-write-read-flow.md](kg/02-write-read-flow.md) — 쓰기 시점·읽기 시점·서비스 흐름
- [03-api.md](kg/03-api.md) — 기존·확장 API
- [04-viewer-ui.md](kg/04-viewer-ui.md) — 지식그래프 뷰어 UI
- [05-agent-reference-and-persistence.md](kg/05-agent-reference-and-persistence.md) — 에이전트 참고·영속성
- [06-kg-enhancement-plan.md](kg/06-kg-enhancement-plan.md) — **구체화·고도화 기획** (데이터 모델·API·뷰어·에이전트 주입·영속성·로드맵)

### [settings/](settings/)
- [01-overview.md](settings/01-overview.md) — 설정 탭 역할
- [02-api-keys.md](settings/02-api-keys.md) — LLM API 키·모델
- [03-skills-list.md](settings/03-skills-list.md) — 스킬·도구 목록 조회
- [04-hitl-watchlist.md](settings/04-hitl-watchlist.md) — HITL 기본 동작·워치리스트(추가 시)

### [common/](common/)
- [01-navigation.md](common/01-navigation.md) — 탭 네비게이션
- [02-refresh-and-responsive.md](common/02-refresh-and-responsive.md) — 새로고침·반응형
- [03-empty-and-error-states.md](common/03-empty-and-error-states.md) — 빈 상태·에러 상태
- [04-design-tone.md](common/04-design-tone.md) — 다크 테마·일관된 톤
