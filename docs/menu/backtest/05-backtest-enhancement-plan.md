# 백테스트 — 구체화·고도화 기획

현재 스텁 수준의 백테스트를 **데이터·엔진·전략·UI·에이전트 연동**까지 단계적으로 구체화·고도화하기 위한 기획.

---

## 1. 현황 정리

| 구분 | 현재 상태 | 부족한 점 |
|------|-----------|-----------|
| **UI** | 기간·종목 1개·전략 프리셋 선택 + 실행 버튼, 결과 카드·거래 테이블(스텁) | 다중 종목, 전략 파라미터 직접 입력, 수익 곡선 차트, 실행 이력 |
| **API** | `POST /agent/backtest` 스텁 응답(0 수치, 빈 trades) | 실제 시뮬레이션 없음 |
| **데이터** | 없음. 스킬은 현재가/RSI 등 **현재 시점**만 반환 | **과거 구간** 일봉(OHLC)·지표(RSI 등) 조회 API 필요 |
| **엔진** | 없음 | 기간별 봉 순회 → 시그널 → 매수/매도 → 수익률·MDD·샤프 등 계산 |
| **에이전트** | `run_backtest` 스킬 미등록 | 채팅에서 "백테스트 해줘" 요청 처리 불가 |

---

## 2. 데이터 계층 구체화

백테스트가 돌아가려면 **과거 일봉(또는 분봉) + 지표**가 필요하다.

### 2.1 요구 데이터

| 데이터 | 용도 | 비고 |
|--------|------|------|
| **일봉 OHLCV** | 봉 단위 시뮬레이션, 수익률 계산 | date, open, high, low, close, volume |
| **지표(RSI 등)** | 전략 시그널 생성 | 기간(period), 임계값(buy_below, sell_above)에 따라 계산 또는 사전 계산 |

### 2.2 데이터 소스 옵션

| 옵션 | 설명 | 장단점 |
|------|------|--------|
| **A. 기존 Python 코어** | nanoquant-ai의 `core/data_fetcher.py`, DB 등이 있다면 **기간 조회 API** 노출 | 재사용 가능 시 유리. 없으면 신규 구현. |
| **B. Node에서 외부 API** | API 서버에서 yfinance·Alpha Vantage·Polygon 등 호출해 일봉 조회 | 구현 빠름. 의존성· rate limit·키 관리 필요. |
| **C. 별도 히스토리 API** | `GET /data/history?symbol=&start=&end=` 형태로 일봉 반환하는 엔드포인트 신설 | 백테스트·차트·다른 기능에서 공용. |

### 2.3 제안: 히스토리 API 스펙

```
GET /agent/data/history
  ?symbol=AAPL
  &start=2024-01-01
  &end=2024-12-31
  &interval=d   (d=일봉, 선택 시 w, m 등)

Response:
{
  "symbol": "AAPL",
  "interval": "d",
  "rows": [
    { "date": "2024-01-02", "open": 185.5, "high": 186.2, "low": 184.1, "close": 185.8, "volume": 12345678 }
  ]
}
```

- **지표(RSI)**: 서버에서 일봉 수신 후 `close`로 RSI 계산해 각 row에 `rsi` 필드 추가하거나, 별도 파라미터 `?indicators=rsi&rsi_period=14`로 포함 반환.

이 계층이 있으면 백테스트 엔진은 "날짜 구간 + 심볼"만 지정해 데이터를 가져와 시뮬레이션할 수 있다.

---

## 3. 백테스트 엔진 구체화

### 3.1 엔진 입력/출력

| 입력 | 타입 | 설명 |
|------|------|------|
| `start_date`, `end_date` | string (YYYY-MM-DD) | 백테스트 기간 |
| `symbols` | string[] | 종목 리스트 (1개 이상) |
| `strategy` | object | 전략 타입 + 파라미터 (아래 3.2) |
| `initial_capital` | number (선택) | 초기 자본. 기본 1,000,000 등 |
| `commission_pct` | number (선택) | 거래당 수수료 % (기본 0 또는 0.1) |

| 출력 | 타입 | 설명 |
|------|------|------|
| `total_return_pct` | number | 기간 총 수익률 (%) |
| `annualized_return_pct` | number | 연환산 수익률 |
| `max_drawdown_pct` | number | 최대 낙폭 (%) |
| `sharpe_ratio` | number (선택) | 샤프 비율 (무위험 이율 가정 가능 시) |
| `trade_count` | number | 체결 거래 수 |
| `win_rate` | number | 승률 (0~1) |
| `equity_curve` | number[] | 일별(또는 봉별) 누적 자산 비율 또는 절대값 |
| `trades` | array | [{ date, symbol, side, price, quantity?, pnl?, ... }] |
| `benchmark_return_pct` | number (선택) | 벤치마크(예: buy & hold) 수익률 |

### 3.2 전략 타입·파라미터

| 전략 type | params | 설명 |
|-----------|--------|------|
| `rsi_threshold` | `period`(기본 14), `buy_below`, `sell_above` | RSI &lt; buy_below 매수, RSI &gt; sell_above 매도 |
| `ma_cross` | `fast`, `slow` (이동평균 기간) | 골든크로스 매수, 데드크로스 매도 |
| `bollinger` | `period`, `std_dev`, `band_touch` | 밴드 터치 시 매수/매도 (추후) |

1단계에서는 **rsi_threshold** 하나만 구현해도 된다. 이후 `ma_cross` 등 확장.

### 3.3 시뮬레이션 로직 (의사)

1. `symbols` × `[start_date, end_date]`에 대해 **히스토리 API**로 일봉(＋지표) 조회.
2. 날짜 순으로 봉을 순회:
   - 전략 규칙에 따라 **매수/매도 시그널** 계산.
   - 시그널 발생 시 **포지션 변경** (현금 ↔ 주식) 및 **거래 기록** 추가.
3. 수수료·슬리피지는 옵션으로 적용 (단가 × (1 ± commission_pct)).
4. 구간 종료 후:
   - `total_return_pct`, `annualized_return_pct`, `max_drawdown_pct`, `sharpe_ratio`, `win_rate` 계산.
   - `equity_curve`, `trades` 반환.

---

## 4. API 계층 구체화

### 4.1 POST /agent/backtest (확장)

**Request body (확장):**

```json
{
  "start_date": "2024-01-01",
  "end_date": "2024-12-31",
  "symbols": ["AAPL", "SOFI"],
  "strategy": {
    "type": "rsi_threshold",
    "params": { "period": 14, "buy_below": 30, "sell_above": 70 }
  },
  "options": {
    "initial_capital": 1000000,
    "commission_pct": 0.1
  }
}
```

**Response:** 3.1의 출력 필드 그대로 반환. (기존 스텁 필드와 호환 유지)

### 4.2 실행 이력 저장 (고도화)

- **저장**: 실행 시 `run_id`(UUID) 부여 후 DB 또는 메모리 저장. (기간, 종목, 전략, 결과 요약, 실행 시각)
- **조회**: `GET /agent/backtest/runs` → 최근 N건 목록. `GET /agent/backtest/runs/:id` → 상세 결과(equity_curve, trades 포함).
- UI에서 "최근 실행" 클릭 시 `runs/:id`로 상세 불러와 동일 화면에 표시.

---

## 5. UI 구체화·고도화

### 5.1 입력 폼

| 항목 | 현재 | 구체화 |
|------|------|--------|
| 기간 | start_date, end_date | 달력 또는 프리셋(최근 1개월/3개월/6개월/1년) |
| 종목 | 단일 텍스트 | 다중 선택(태그 입력 또는 워치리스트 연동), 최소 1개 |
| 전략 | 드롭다운(프리셋만) | 프리셋 + **파라미터 직접 입력**(RSI period, buy_below, sell_above) |
| 옵션 | 없음 | (고도화) 초기 자본, 수수료 % 접이식 영역 |

### 5.2 결과 영역

| 영역 | 내용 |
|------|------|
| **요약 카드** | 총 수익률, 연환산, MDD, 샤프, 거래 수, 승률. 벤치마크 대비 표시(선택). |
| **수익 곡선** | X축: 날짜, Y축: 누적 수익률(%). 선 그래프. (라이브러리: Chart.js, Lightweight Charts, 또는 SVG 직접) |
| **거래 테이블** | 날짜, 종목, 매수/매도, 가격, 수량, 손익, 누적 수익률 등. 정렬·필터(선택). |
| **실행 이력** | 하단 또는 사이드 "최근 실행" 목록. 클릭 시 해당 run 결과 로드. |

### 5.3 빈/에러 상태

- 데이터 없음: "해당 기간 데이터가 없습니다. 종목·기간을 확인하세요."
- API 실패: "백테스트 실행에 실패했습니다. 재시도" + (개발 시 상세 메시지).

---

## 6. 에이전트·KG 연동

### 6.1 run_backtest 스킬 (구현됨)

| 항목 | 내용 |
|------|------|
| **이름** | `run_backtest` |
| **설명** | Run a backtest for the given period, symbols, and RSI strategy. Returns summary (total return %, max drawdown, trade count, win rate) and a short text summary. |
| **params_schema** | `start_date`, `end_date`, `symbols`(string, 쉼표 구분 또는 단일), `strategy_type`, `period`, `buy_below`, `sell_above` |
| **동작** | 내부에서 **백테스트 엔진(runBacktest)** 직접 호출 → 결과에서 `summary` 문자열 + 수치 반환. (예: "백테스트 결과 (2024-01-01 ~ 2024-12-31, AAPL): 총 수익률 12.3%, 연환산 12.3%, 최대 낙폭 -8.2%, 거래 24회, 승률 58.0%.") |

**툴화**: 백테스트 로직은 `backtest/engine.ts`의 `runBacktest`로 공통화되어 있으며, `skills/index.ts`에서 `run_backtest` 스킬로 등록. 채팅에서 "지난 1년 AAPL RSI 30/70 백테스트해줘" 요청 시 ReAct가 이 스킬을 호출해 결과를 답변에 포함한다.

### 6.2 백테스트 탭과의 연동

- 채팅에서 백테스트 실행 시 **run_id**를 응답에 포함시키거나, "상세 결과는 백테스트 탭에서 확인하세요" + 링크(또는 run_id 전달)로 탭에서 `runs/:id` 조회 가능하게 함.

### 6.3 KG 연동 (선택·고도화)

- 백테스트 실행 결과(전략 요약, 수익률, MDD)를 KG에 **결정/이벤트** 노드로 기록.
- 에이전트가 "비슷한 전략은 과거에 OO% 수익이었어"처럼 참고할 수 있음.

---

## 7. 단계별 로드맵 (구체화·고도화)

| 단계 | 목표 | 산출물 |
|------|------|--------|
| **1단계** | **데이터 + 엔진 1종** | 히스토리 API(일봉) 1개 구현(yfinance 또는 기존 코어). 백테스트 엔진: RSI 임계값 전략만, 단일 종목. POST /backtest 실연동. UI는 기존 폼 유지, 결과 숫자·거래 테이블 실제 데이터. |
| **2단계** | **전략 파라미터·다중 종목** | UI에서 RSI period/buy_below/sell_above 입력. API에서 symbols[] 다중 종목 처리. 수익 곡선 차트(equity_curve) 표시. |
| **3단계** | **run_backtest 스킬·실행 이력** | run_backtest 스킬 등록. 채팅 연동. 실행 이력 저장·조회 API + "최근 실행" UI. |
| **4단계** | **고도화** | 전략 추가(MA 크로스 등). 벤치마크 대비. 샤프·수수료 옵션. KG 기록(선택). |

---

## 8. 문서 간 연결

- **개요·기능**: [01-overview.md](01-overview.md), [02-features.md](02-features.md)
- **UI·결과**: [03-ui-and-results.md](03-ui-and-results.md)
- **API·우선순위**: [04-api-and-priority.md](04-api-and-priority.md)
- **본 문서**: 구체화·고도화 로드맵 및 데이터/엔진/API/UI 상세.

구현 시 1단계부터 순차 진행하면, 스텁에서 실제 동작하는 백테스트까지 단계적으로 전환할 수 있다.
