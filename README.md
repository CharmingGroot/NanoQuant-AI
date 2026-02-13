# 🤖 NanoQuant AI

15분 간격 AI 하이브리드 퀀트 트레이딩 시스템 - 미국 소형주 자동매매 봇 (시뮬레이션)

## 📋 프로젝트 개요

NanoQuant AI는 약 $75 (10만원) 소액 자본으로 운영되는 지능형 트레이딩 시스템입니다.

### 핵심 특징

- **3계층 아키텍처**: Quant Scanner → Event Trigger → Deep Agent
- **이벤트 기반**: 불필요한 API 호출을 줄여 비용 최적화
- **AI 분석**: Claude 3.5 Sonnet 또는 GPT-4o-mini로 최종 매매 결정
- **무료 데이터**: yfinance 사용 (API 키 불필요)
- **시뮬레이션 모드**: 안전한 가상 트레이딩

## 🏗️ 시스템 아키텍처

```
┌─────────────────────────────────────────────────────┐
│  Layer 1: Quant Scanner (매일/4시간마다)             │
│  - 미국 소형주 중 저평가 종목 20개 선정                │
│  - yfinance로 시장 데이터 수집                        │
└─────────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────┐
│  Layer 2: Event-Driven Trigger (15분마다)            │
│  - 가격 변동률 (40점)                                 │
│  - 뉴스 키워드 (40점) - Playwright 크롤링             │
│  - 거래량 급증 (20점)                                 │
│  - 60점 이상 시 Layer 3 활성화                        │
└─────────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────┐
│  Layer 3: Deep Agent (트리거 발동 시)                 │
│  - LLM이 차트 + 뉴스 분석                             │
│  - BUY/SELL/HOLD 결정                                │
│  - 시뮬레이션 모드로 포트폴리오 추적                   │
└─────────────────────────────────────────────────────┘
```

## 🚀 빠른 시작

### 1. 환경 설정

```bash
# 의존성 설치
pip install -r requirements.txt

# Playwright 브라우저 설치
python -m playwright install chromium
```

### 2. API 키 설정

`.env` 파일을 편집하고 AI API 키를 입력하세요:

```env
# AI API (둘 중 하나만 필요)
ANTHROPIC_API_KEY=your_anthropic_key  # Claude 사용 시
# 또는
OPENAI_API_KEY=your_openai_key        # GPT 사용 시

# 트레이딩 설정
TRADING_CAPITAL=75
MAX_POSITION_SIZE=5
```

### 3. API 키 발급 방법

#### Anthropic Claude (권장)
1. https://console.anthropic.com 회원가입
2. API 키 생성
3. 크레딧 충전 ($5 정도면 테스트 충분)

#### OpenAI GPT (대안)
1. https://platform.openai.com 회원가입
2. API 키 생성
3. 크레딧 충전

### 4. 실행

```bash
# 전체 시스템 실행
python main.py

# 개별 모듈 테스트
python data_fetcher.py  # yfinance 데이터 수집 테스트
python scraper.py       # 웹 크롤러 테스트
python trigger.py       # 트리거 엔진 테스트
python deep_agent.py    # AI 에이전트 테스트 (API 키 필요)
python db_viewer.py     # SQLite 실시간 뷰어 (http://127.0.0.1:5050)
```

### 5. DB 뷰어 (감시)

판단/성찰 기록을 실시간으로 보려면 **별도 터미널**에서:

```bash
python db_viewer.py
```

브라우저에서 **http://127.0.0.1:5050** 접속. 10초마다 자동 새로고침됩니다.

- **Recent decisions**: 최근 50건 (시간, 종목, 액션, 가격, 금액, 신뢰도, 리스크, 트리거 점수, 추론)
- **Recent reflections**: 최근 20건 (평가 시점, 종목, 결정가/평가가, 수익률, 성공 여부, 성찰 메모)

환경 변수: `NANOQUANT_DB=nanoquant_v1.db` (기본), `DB_VIEWER_PORT=5050` (기본)

## 📁 파일 구조

```
nanoquant-ai/
├── main.py              # 메인 오케스트레이터 (시뮬레이션)
├── db_viewer.py         # SQLite 실시간 뷰어 (Flask)
├── scraper.py           # Playwright 웹 크롤러
├── trigger.py           # 점수제 트리거 엔진
├── data_fetcher.py      # yfinance 데이터 수집
├── deep_agent.py        # AI 딥 에이전트
├── quant_rules/         # 퀀트 지표 계산 모듈
│   ├── __init__.py
│   └── indicators.py    # RSI, SMA, EMA, MACD, Bollinger 등
├── requirements.txt     # Python 패키지 목록
├── .env                 # 환경 변수 (API 키)
├── .env.example         # 환경 변수 템플릿
├── nanoquant.log        # 실행 로그
├── trade_history.json   # 거래 기록
├── CLAUDE.md           # Claude Code 가이드
├── prd.md              # 프로젝트 요구사항 문서
└── README.md           # 이 파일
```

## 📐 퀀트 지표 (quant_rules) — 다중 타임프레임

Layer 2에서 **15분·1시간·1일** 세 타임프레임에 대해 각각 기술적 지표를 계산합니다.
소형주 분석 시 1일 추세 + 1시간 구조 + 15분 진입 타이밍을 함께 고려합니다.

| 타임프레임 | 역할 | 봉 수 |
|------------|------|-------|
| **15분** | 진입 타이밍, 당일 변동성·모멘텀 | 40봉 |
| **1시간** | 단기 구조, 노이즈 감소 | 40봉 |
| **1일** | 추세·지지/저항, RSI/SMA 해석에 가장 적합 | 30봉 |

| 지표 | 함수 | 설명 | 해석 |
|------|------|------|------|
| **RSI** | `rsi()` | 상대 강도 지수 (0~100) | <30 과매도, >70 과매수 |
| **SMA** | `sma()` | 단순이동평균 (20봉) | 추세 방향, 지지/저항 |
| **EMA** | `ema()` | 지수이동평균 (12/26) | 단기·장기 추세선 |
| **MACD** | `macd()` | MACD, Signal, Histogram | histogram 부호=추세 방향 |
| **Bollinger** | `bollinger_bands()` | 상/중/하단 밴드, %B | %B<0 과매도, %B>1 과매수 |
| **Momentum** | `price_momentum()` | N봉 대비 변동률 % | 추세 강도·방향 |
| **Volume** | `volume_ratio()` | 현재/평균 거래량 배수 | 추세 확인 신뢰도 |

- **다중 타임프레임 일괄 계산**: `compute_all_multi(bars_15m, bars_1h, bars_1d)` → `{'15m': {...}, '1h': {...}, '1d': {...}}`
- **단일 타임프레임**: `compute_all(bars)` → 모든 지표를 dict로 반환
- **DB 뷰어**: RSI/SMA/MACD/BB%B 컬럼에 `15m / 1h / 1d` 형식으로 표시

## 🎯 트리거 점수 시스템

| 조건 | 점수 | 기준 |
|------|------|------|
| 가격 변동 | 40점 | 15분 내 ±3% 이상 변동 |
| 뉴스 감지 | 40점 | FDA, earnings, 인수합병 등 키워드 발견 |
| 거래량 급증 | 20점 | 평균 대비 2배 이상 |

**트리거 임계값**: 60점 이상 시 Deep Agent 활성화

## 🧠 Deep Agent 동작 방식

1. **입력 데이터**:
   - 최근 5개 15분봉 차트 데이터
   - 최근 뉴스 헤드라인 5개
   - 트리거 발동 이유
   - **퀀트 지표 (15m / 1h / 1d)** — RSI, SMA, EMA, MACD, Bollinger, Momentum, Volume ratio
   - 현재 잔고 및 포지션

2. **분석 과정**:
   - LLM이 패턴, 뉴스, 리스크 종합 분석
   - BUY/SELL/HOLD 결정
   - 신뢰도(Confidence) 70% 이상만 실행

3. **출력**:
   - Action: BUY/SELL/HOLD
   - Amount: 거래 금액/비율
   - Confidence: 0-100
   - Reasoning: 결정 이유 2-3문장
   - Risk Level: LOW/MEDIUM/HIGH

## ⚙️ 주요 설정

| 설정 | 기본값 | 설명 |
|------|--------|------|
| `TRADING_CAPITAL` | $75 | 총 투자 자본 (시뮬레이션) |
| `MAX_POSITION_SIZE` | $5 | 종목당 최대 투자액 |

## 📊 시뮬레이션 모드

- **가상 포트폴리오**: 실제 거래 없이 매매 시뮬레이션
- **거래 기록**: `trade_history.json`에 모든 거래 저장
- **실시간 P/L**: 매 거래 후 수익률 계산 및 로그 출력
- **안전성**: 실제 돈이 움직이지 않음

## 📈 데이터 소스

- **시장 데이터**: yfinance (무료, API 키 불필요)
- **뉴스**: Yahoo Finance (Playwright 크롤링)
- **AI 분석**: Claude API 또는 OpenAI API (유료)

## 💡 사용 예시

```bash
# 1. API 키 설정
# .env 파일에 ANTHROPIC_API_KEY 또는 OPENAI_API_KEY 입력

# 2. 시스템 시작
python main.py

# 출력:
# 🚀 NANOQUANT AI STARTING
# Capital: $75.0
# Max Position: $5.0
# Mode: SIMULATION
#
# LAYER 1: Scanning for small-cap candidates...
# ✓ Selected 20 candidates: SOFI, HOOD, COIN, ...
#
# LAYER 2: Evaluating triggers...
#   Analyzing SOFI...
#   Analyzing HOOD...
#   ...
# ✓ Triggered stocks: 2/20
#
# LAYER 3: Deep analysis for SOFI
#   Decision: BUY
#   Amount: $5.00
#   Confidence: 85%
#   Reasoning: Strong momentum with positive news catalyst...
#   ✓ [SIMULATION] BUY: SOFI $5.00 @ $8.50
#   Portfolio: Cash=$70.00 | Total=$75.00 | P/L=+$0.00 (+0.0%)
```

## ⚠️ 주의사항

1. **시뮬레이션 모드**: 현재는 실제 거래가 발생하지 않습니다
2. **API 비용**: AI API 호출 비용 발생 (하루 ~$1-2 예상)
3. **시장 시간**: 미국 주식시장 개장 시간(한국 시간 23:30-06:00)에만 의미 있는 데이터
4. **yfinance 제한**: 15분 데이터는 최근 7일치만 제공됨
5. **크롤링 주의**: Yahoo Finance 크롤링 시 너무 빈번하면 IP 차단될 수 있음

## 🛠️ 트러블슈팅

### "ANTHROPIC_API_KEY not found"
- `.env` 파일에 `ANTHROPIC_API_KEY` 또는 `OPENAI_API_KEY`를 입력하세요

### "No data available for ticker"
- 해당 종목의 15분 데이터가 없거나 시장 마감 시간일 수 있습니다
- 미국 시장 개장 시간(한국 시간 23:30-06:00)에 테스트하세요

### "playwright 설치 오류"
```bash
python -m playwright install chromium
```

### yfinance 데이터 오류
- yfinance는 비공식 API이므로 가끔 오류가 발생할 수 있습니다
- 잠시 후 다시 시도하세요

## 📈 향후 개선 사항

- [ ] 실제 브로커 API 연동 (한국투자증권 KIS API 등)
- [ ] Supabase 데이터베이스 연동
- [ ] React 대시보드 구현
- [ ] 백테스팅 기능 (VectorBT)
- [ ] 손절/익절 자동 관리
- [ ] Telegram 알림 기능
- [ ] 다중 계정 관리

## 🔧 실제 거래 연동하려면?

현재는 시뮬레이션 모드만 지원합니다. 실제 거래를 원한다면:

1. **한국 투자자**: 한국투자증권 KIS API 연동
2. **미국 거래**: Alpaca Markets API 또는 Interactive Brokers
3. **main.py 수정**: `execute_trade()` 함수에 실제 브로커 API 호출 추가

## 📝 라이선스

MIT License

## 🤝 기여

이슈 및 PR 환영합니다!

## ⚖️ 면책 조항

이 소프트웨어는 교육 및 연구 목적으로 제공됩니다. 실제 투자에 사용 시 발생하는 손실에 대해 개발자는 책임을 지지 않습니다. 투자는 본인의 판단과 책임 하에 진행하세요.
