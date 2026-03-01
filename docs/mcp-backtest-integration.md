# 백테스트·도구 MCP 연동 기획

백테스트 Python 서비스를 **MCP(Model Context Protocol) 서버**로 전환하고, Skill 호출 시 **MCP 클라이언트**를 통해 도구를 호출하도록 하는 기획.

---

## 1. 목표

| 기존 | 변경 후 |
|------|---------|
| Python 서버: FastAPI HTTP API (`/backtest`, `/history`) | Python 서버: **MCP 서버** — 도구 `get_history`, `run_backtest` 노출 |
| Node: HTTP 프록시로 Python API 호출 | Node: **MCP 클라이언트**로 Python MCP 서버에 연결, 도구 호출 |
| Skill `run_backtest`: Node 내부 `runBacktest()` 또는 HTTP POST | Skill `run_backtest`: **MCP 도구 호출** (Python 서버의 `run_backtest` 툴 실행) |

- **Skill이 도구를 호출할 때** → 해당 도구가 MCP로 제공되면 **MCP로 호출**한다.
- 백테스트·히스토리 연산은 Python(pandas, yfinance)이 담당하고, Node는 ReAct·세션·KG에 집중한다.

---

## 2. 아키텍처

```
[ UI / 채팅 ]  →  [ Node API (ReAct, Skill 레지스트리) ]
                          │
                          │  Skill 실행 시 "도구" 필요
                          ▼
                  [ MCP Client (Node) ]
                          │
                          │  MCP 프로토콜 (stdio / SSE / Streamable HTTP)
                          ▼
                  [ Python MCP Server ]
                    - Tool: get_history
                    - Tool: run_backtest
                    (pandas, yfinance 기반)
```

- **Python MCP 서버**: `apps/backtest-python`을 MCP 서버로 동작하도록 변경. FastMCP 등으로 `get_history`, `run_backtest` 툴 등록.
- **Node MCP 클라이언트**: Skill 레지스트리에서 `run_backtest`(및 필요 시 `get_history`) 실행 시, Node가 설정된 MCP 서버(백테스트용)에 연결해 해당 **도구 이름**으로 호출하고 결과를 Skill 반환값으로 사용.

---

## 3. Python 쪽 (MCP 서버)

### 3.1 역할

- 기존 FastAPI HTTP 엔드포인트를 **MCP Tools**로 노출.
- 전송(transport): **Streamable HTTP** 또는 **SSE**로 Node가 연결 가능하도록.

### 3.2 노출 도구

| MCP Tool 이름 | 설명 | 입력 (예시) | 출력 |
|---------------|------|-------------|------|
| `get_history` | 종목·기간별 일봉(OHLCV) 조회 | `symbol`, `start`, `end`, `interval?` | `rows[]` (date, open, high, low, close, volume) |
| `run_backtest` | 기간·종목·전략으로 백테스트 실행 | `start_date`, `end_date`, `symbols[]`, `strategy: { type, params }` | `total_return_pct`, `max_drawdown_pct`, `trades`, `equity_curve` 등 (기존 API와 동일 스키마) |

- 구현: 기존 `engine.py`(yfinance, pandas) 로직을 그대로 사용하고, FastMCP `@mcp.tool()` 로 래핑.

### 3.3 기술 스택

- **MCP Python SDK**: `mcp` (또는 `mcp[cli]`) — FastMCP 사용 권장.
- 실행: `uv run server.py` 또는 `mcp run server.py` — transport는 Streamable HTTP(예: 포트 5052)로 노출.

---

## 4. Node 쪽 (MCP 클라이언트)

### 4.1 역할

- **백테스트·히스토리용 MCP 서버** 1개 연결 (환경 변수로 URL 또는 stdio 설정).
- Skill `run_backtest` 실행 시:
  - MCP 클라이언트로 해당 서버의 **도구 `run_backtest`** 호출.
  - 인자를 스킬 인자에서 MCP 도구 인자로 매핑.
  - 반환값을 그대로 Skill 결과로 사용 (요약 문자열 생성 등은 기존처럼 Node에서 처리 가능).
- (선택) `get_history`를 필요로 하는 다른 스킬이 생기면, 동일하게 MCP 도구 `get_history` 호출.

### 4.2 설정

- 예: `BACKTEST_MCP_URL=http://127.0.0.1:5052/mcp` (Streamable HTTP) 또는 stdio로 Python 프로세스 spawn.
- MCP URL이 없으면: 기존처럼 Node 내부 `runBacktest()` / HTTP 프록시로 폴백(하위 호환).

### 4.3 Skill ↔ MCP 도구 매핑

| Skill 이름 | MCP 서버 | MCP Tool 이름 | 비고 |
|------------|----------|----------------|------|
| `run_backtest` | 백테스트 Python MCP | `run_backtest` | 인자: start_date, end_date, symbols, strategy |
| (추가 시) | 백테스트 Python MCP | `get_history` | 예: RSI 계산 등 다른 스킬에서 사용 |

- Skill 레지스트리에서 “이 스킬은 MCP 도구 위임”인 경우, **MCP 클라이언트.call_tool(server, tool_name, args)** 만 호출하고, 그 결과를 파싱해 스킬 반환 형식으로 맞춘다.

---

## 5. 호출 흐름 (Skill → 도구 → MCP)

1. 사용자: "AAPL 1년치 백테스트 해줘"
2. ReAct: `run_backtest` 스킬 사용 결정, 인자 추출.
3. Node Skill 실행기: `run_backtest`가 **MCP 도구 위임**으로 설정되어 있음 → **MCP 클라이언트**로 백테스트 MCP 서버의 `run_backtest` 도구 호출.
4. Python MCP 서버: `run_backtest` 툴 실행 → pandas·yfinance로 시뮬레이션 → 결과 반환.
5. Node: MCP 응답을 Skill 반환값으로 사용 → ReAct가 사용자에게 요약 응답.

즉, **Skill을 호출할 때 그 구현이 “도구”라면 MCP로 호출**하는 구조로 통일한다.

---

## 6. 단계별 적용 (로드맵)

| 단계 | 내용 |
|------|------|
| **1. 기획·설계** | 본 문서 반영, `backtest-python-service.md`를 MCP 기준으로 수정 |
| **2. Python MCP 서버** | `apps/backtest-python`에 MCP SDK 도입, `get_history`·`run_backtest` 툴 노출 (Streamable HTTP) |
| **3. Node MCP 클라이언트** | Node에 MCP 클라이언트 라이브러리 도입, `BACKTEST_MCP_URL` 연결 및 `call_tool` 래퍼 구현 |
| **4. Skill 연동** | `run_backtest` 스킬 핸들러를 “MCP 도구 호출”로 전환 (설정 시 MCP, 미설정 시 기존 로직) |
| **5. (선택) get_history** | 다른 스킬에서 과거 데이터가 필요할 때 MCP `get_history` 도구 호출로 통일 |

---

## 7. 정리

- **백테스트 Python 서버**: 도구를 **MCP로 제공** (MCP 서버).
- **Skill에서 도구를 쓸 때**: Node는 **MCP 클라이언트**로 해당 도구를 호출.
- 기존 HTTP API는 하위 호환용으로 유지할지, 아니면 MCP만 노출할지는 구현 단계에서 결정. (권장: 먼저 MCP 서버 + Node MCP 클라이언트 연동, HTTP는 선택적 유지.)

이 설계대로 진행하면 “Skill 호출 시 도구는 MCP로 호출”하는 구조로 기획이 변경된다.
