# 백테스트 Python 서비스 — MCP 기반 도구 제공

백테스트·히스토리 조회는 CPU/데이터 연산이 많고 pandas·yfinance 등 Python 생태계가 유리하므로, **Node API와 별도로 Python 서비스를 두는 구성**을 유지한다.  
**변경**: Python 서비스가 HTTP API가 아니라 **MCP(Model Context Protocol) 서버**로 도구를 노출하고, Skill 호출 시 Node가 **MCP 클라이언트**로 해당 도구를 호출한다.

- 상세 기획: **[docs/mcp-backtest-integration.md](./mcp-backtest-integration.md)** 참고.

---

## 1. 역할 분담 (MCP 기준)

| 구분 | Node (Express) | Python (MCP 서버) |
|------|-----------------|-------------------|
| **담당** | 채팅·ReAct·세션·KG·HITL·스킬 오케스트레이션, UI API, **MCP 클라이언트** | **MCP 도구** 제공: `get_history`, `run_backtest` (pandas, yfinance) |
| **호출 관계** | Skill 실행 시 도구가 필요하면 **MCP 클라이언트**로 Python MCP 서버의 **도구** 호출 | Python은 Node를 호출하지 않음 (무상태) |

- **Skill이 도구를 호출할 때** → 그 도구가 MCP로 제공되면 **MCP로 호출**한다.
- 예: `run_backtest` 스킬 → Node가 백테스트 MCP 서버의 `run_backtest` 툴을 MCP로 호출.

---

## 2. Python 서버 (MCP 서버)

- **프레임워크**: MCP Python SDK (FastMCP 권장).
- **노출 방식**: HTTP API 대신 **MCP Tools**로 노출.
  - **Tool: `get_history`** — 종목·기간별 일봉 조회 (yfinance 등).
  - **Tool: `run_backtest`** — 기간·종목·전략으로 백테스트 (pandas, RSI 시뮬레이션).
- **전송(transport)**: Streamable HTTP 또는 SSE (Node MCP 클라이언트가 연결).
- **실행**: `uv run server.py` 등으로 MCP 서버 기동 (예: 포트 5052).

기존 FastAPI HTTP 엔드포인트(`/backtest`, `/history`)는 하위 호환용으로 유지할지, MCP만 노출할지는 구현 단계에서 결정. (권장: MCP 우선, 필요 시 HTTP는 별도 루트로 유지.)

---

## 3. Node 측 (MCP 클라이언트)

- **설정**: `BACKTEST_MCP_URL` (또는 기존 `BACKTEST_SERVICE_URL`를 MCP 엔드포인트로 해석) 환경 변수.
  - 예: `http://127.0.0.1:5052/mcp` (Streamable HTTP).
- **동작**:
  - Skill `run_backtest` 실행 시 → MCP 클라이언트로 백테스트 MCP 서버에 연결 → **도구 `run_backtest`** 호출 → 결과를 Skill 반환값으로 사용.
  - (선택) 다른 스킬에서 과거 데이터가 필요하면 **도구 `get_history`** 를 MCP로 호출.
- **폴백**: MCP URL이 없으면 기존처럼 Node 내부 `runBacktest()` 또는 HTTP 프록시 사용 (하위 호환).

---

## 4. 정리

- **Python**: 백테스트·히스토리 **도구를 MCP로 제공** (MCP 서버).
- **Node**: Skill 호출 시 해당 도구가 MCP 도구면 **MCP 클라이언트**로 호출.
- 장점: 도구 노출 방식이 MCP로 통일되어, 다른 MCP 호환 클라이언트(예: Cursor, 다른 에이전트)에서도 동일 도구 활용 가능. Node는 ReAct·스킬 오케스트레이션에만 집중.

구현 상태 및 실행 방법은 **docs/mcp-backtest-integration.md** 및 `apps/backtest-python/` README를 참고한다.
