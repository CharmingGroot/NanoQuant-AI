# 지식그래프 — 개요

지식그래프(KG) 도입 및 뷰어는 **선택이 아닌 필수**. 에이전트 "성장"의 핵심 데이터 시각화.

## KG가 서비스에서 하는 역할

| 역할 | 설명 |
|------|------|
| **판단 이력 저장** | 에이전트가 스킬을 실행할 때마다 "누가(세션), 무엇을(스킬+인자), 어떤 결과"를 **Decision** 노드로 기록. |
| **스킬·지표 메타** | 사용된 스킬을 **Skill** 노드로 등록하고, Decision → Skill **used_in** 엣지로 연결. (추후 Indicator, Rule 노드 확장) |
| **모니터링 소스** | 대시보드·모니터 탭의 "최근 결정"은 KG의 Decision 목록을 조회해 표시. |
| **성장 기반** | 나중에 "이 티커로 과거에 뭘 했는지", "이 스킬이 얼마나 쓰였는지"를 조회해 에이전트 추론·UI 분석에 활용. |

## 문서 구성

- [02-write-read-flow.md](02-write-read-flow.md) — 쓰기 시점·읽기 시점·서비스 흐름
- [03-api.md](03-api.md) — 기존·확장 API
- [04-viewer-ui.md](04-viewer-ui.md) — 지식그래프 뷰어 UI
- [05-agent-reference-and-persistence.md](05-agent-reference-and-persistence.md) — 에이전트 참고·영속성
- **[06-kg-enhancement-plan.md](06-kg-enhancement-plan.md)** — **구체화·고도화 기획** (데이터 모델, 쓰기/읽기, API, 뷰어, 에이전트 주입, 영속성, 로드맵)

원본 상세: [kg-service-integration.md](../../kg-service-integration.md)
