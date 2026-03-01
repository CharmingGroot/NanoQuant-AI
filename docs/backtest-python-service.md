# 백테스트 Python 서비스 분리

백테스트·히스토리 조회는 CPU/데이터 연산이 많고 pandas·yfinance 등 Python 생태계가 유리하므로, **Node API와 별도로 Python 서버를 하나 두는 구성**을 권장한다.

---

## 1. 역할 분담

| 구분 | Node (Express) | Python (FastAPI 등) |
|------|----------------|---------------------|
| **담당** | 채팅·ReAct·세션·KG·HITL·스킬 오케스트레이션, UI API 라우팅 | 과거 일봉 조회, 백테스트 엔진 (pandas, RSI, 시뮬레이션) |
| **호출 관계** | Node가 백테스트/히스토리 요청 시 **Python 서버로 HTTP 호출** | Python은 Node를 호출하지 않음 (무상태) |

- `POST /agent/backtest` → Node가 내부 엔진 대신 **Python `POST /backtest`** 호출 후 결과 그대로 반환.
- `GET /agent/data/history` → Node가 **Python `GET /history`** 호출 후 그대로 반환 (또는 1단계는 Node 스텁 유지, 2단계에서 Python 전환).

---

## 2. Python 서버 스펙 (제안)

- **프레임워크**: FastAPI (비동기, 스키마 자동 문서화).
- **엔드포인트**:
  - `GET /history?symbol=&start=&end=&interval=d`  
    → yfinance 등으로 일봉 조회, RSI 등 지표 옵션 시 계산해 반환.
  - `POST /backtest`  
    body: `{ start_date, end_date, symbols[], strategy: { type, params } }`  
    → 히스토리 조회 후 pandas로 시뮬레이션, 기존과 동일한 응답 형식 (total_return_pct, max_drawdown_pct, trades, equity_curve 등).
- **실행**: `uvicorn` 등으로 별도 포트 (예: 5052) 기동. Node는 `BACKTEST_SERVICE_URL=http://127.0.0.1:5052` 로 호출.

---

## 3. Node 측 변경

- **설정**: `BACKTEST_SERVICE_URL` (또는 `PYTHON_BACKTEST_URL`) 환경 변수. 없으면 기존처럼 Node 내부 스텁/엔진 사용 (하위 호환).
- **프록시 로직**:
  - `POST /agent/backtest`: `BACKTEST_SERVICE_URL` 이 있으면 해당 URL의 `/backtest`에 body 전달, 응답을 그대로 클라이언트에 반환. 없으면 기존 `runBacktest()`.
  - `GET /agent/data/history`: 선택적으로 동일하게 Python `/history`로 프록시.

---

## 4. 정리

- **장점**: pandas·yfinance·numpy로 백테스트·지표 연산 구현이 쉽고, Node는 채팅/에이전트에만 집중. 무거운 연산이 Python 프로세스로 분리되어 Node 이벤트 루프 블로킹 감소.
- **단점**: 서버 2개 기동·배포 필요, 네트워크/지연 고려. 개발 시에는 `pnpm run dev` + `uvicorn main:app --reload --port 5052` 같이 두 터미널로 실행하면 됨.

---

## 5. 구현 상태 및 실행 방법

- **Python 서비스**: `apps/backtest-python/` — FastAPI, `GET /history` (yfinance), `POST /backtest` (pandas·RSI). 자세한 내용은 해당 폴더의 README 참고.
- **Node**: `BACKTEST_SERVICE_URL` 환경 변수가 있으면 `POST /agent/backtest`·`GET /agent/data/history` 를 해당 URL로 프록시. 없으면 기존 Node 엔진/스텁 사용.

로컬: `apps/backtest-python`에서 `pip install -r requirements.txt` 후 `python main.py` (포트 5052). Node는 `BACKTEST_SERVICE_URL=http://127.0.0.1:5052` 로 기동.

이 설계대로 진행하면 기획서의 “yfinance·기존 코어 활용”과도 맞고, 이후 전략 확장(MA 크로스, 벤치마크 등)도 Python 쪽에서만 확장 가능하다.
