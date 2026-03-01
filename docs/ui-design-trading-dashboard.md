# UI 디자인 가이드 — 트레이딩 대시보드 스타일

참고 이미지(트레이딩 대시보드·분석 대시보드) 기준으로 NanoQuant AI v2 UI에 반영한 비주얼 가이드.

## 적용 요약

- **헤더**: 메인 타이틀 "NanoQuant AI"(라이트 블루 `#58a6ff`) + 부제 "실시간 퀀트 에이전트 모니터링 및 통합 관리" + 우측 [새로고침] 버튼 + Last Update 시각.
- **탭**: 대시보드 | AI 채팅 | 모니터 | 설정. 활성 탭 라이트 블루 배경.
- **상단 요약 카드**: 대시보드에서 4열 그리드(등록 스킬, 채팅 세션, 최근 결정, 투자 요약). 카드당 아이콘 영역 + 숫자 + 라벨, 다크 그레이 배경·라운드.
- **섹션**: 섹션 제목은 `--nq-title`(라이트 블루). 본문은 카드(테두리·라운드) 내 테이블/폼.
- **상태 pill**: 녹색(정상/실행), 빨강(중지/오류), 보라(메타/전략). `.pill.ok`, `.pill.meta` 등.
- **색상 변수**: `--nq-bg`, `--nq-surface`, `--nq-border`, `--nq-title`, `--nq-success`, `--nq-danger`, `--nq-purple`, `--nq-warning`.

## 산출물

- `apps/web/index.html`: CSS 변수(다크 블루그레이·라이트 블루·녹/빨/보라).
- `apps/web/src/nanoquant-app.ts`: 헤더(타이틀+부제+새로고침+Last Update), 탭.
- `apps/web/src/dashboard-tab.ts`: 요약 카드 4개, 최근 결정 테이블.
- `apps/web/src/chat-tab.ts`, `settings-tab.ts`: 섹션 제목 라이트 블루, 카드 스타일 유지.
