# NanoQuant AI v2

성장형 퀀트 트레이딩 에이전트 (OpenClaw 스타일 3단계: Interface → Control/ReAct → Execution/Skills).

## 요구사항

- Node.js ≥ 22
- pnpm (또는 `npx pnpm`)

## 설치

```bash
pnpm install
pnpm run build
```

## 실행

**한 번에 API + 웹 실행:**

```bash
pnpm run dev
```

- **API**: http://127.0.0.1:5051  
- **웹**: http://localhost:5173 (또는 5174 등 다음 빈 포트)

브라우저에서 웹 주소로 접속하면 대시보드·AI 채팅·설정 탭이 보입니다. 채팅 사용 전 **설정** 탭에서 LLM API 키를 입력하세요.

**API만 실행 (빌드된 dist):**

```bash
pnpm run dev:api   # tsx로 API만
# 또는
cd apps/api && node dist/index.js
```

## 실행 검증

API가 떠 있는 상태에서 다른 터미널에서:

```bash
pnpm run verify
```

`/health`와 `/agent/skills` 호출로 정상 동작 여부를 확인합니다.

## 테스트

```bash
pnpm run test
```

(API 단위 테스트: Gateway, Skill Registry 등)

## 환경 변수 (API)

- `PORT`: API 포트 (기본 **5051**)
- `ANTHROPIC_API_KEY` 또는 `OPENAI_API_KEY`: LLM 호출용 (또는 채팅 요청 body에 `api_key` 전달)

## 기획·명세

- [docs/nanoquant-v2-full-cycle-plan.md](docs/nanoquant-v2-full-cycle-plan.md)
- [docs/agent-api-spec.md](docs/agent-api-spec.md)
