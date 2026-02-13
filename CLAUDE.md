# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

NanoQuant AI is a 15-minute interval AI hybrid quant trading system for US small-cap stocks, designed to operate with ~$75 (10만원) capital. The core philosophy: use quant scanning to narrow candidates, then a deep agent (LLM) analyzes real-time news/charts for final trade decisions.

## Architecture

Three-layer pipeline:

- **Layer 1 – Quant Scanner**: Runs at market open (or hourly). Filters US small-cap stocks (bottom 20% market cap) by low PBR/PER and volume spikes (200%+ vs 5-day average) to extract ~20 candidates.
- **Layer 2 – Event-Driven Analyst**: Polls every 15 minutes. Activates the LLM deep agent only when event triggers fire (price volatility, news keywords, technical indicator crossovers) to optimize API costs.
- **Layer 3 – Execution Engine**: Executes fractional trades ($1–$5 units) via Alpaca Markets API (paper/live).

## Tech Stack

- **Language**: Python 3.10+
- **Core Libraries**: pandas, vectorbt (backtesting), alpaca-trade-api (trading)
- **AI**: LangChain or direct API calls (Claude 3.5 Sonnet / GPT-4o-mini)
- **Database**: Supabase (trade records and agent logs)
- **UI**: React + Tailwind CSS + Lightweight Charts

## Key Data Flows

- Deep agent input: chart data (JSON), news text, current balance
- Deep agent output: action (BUY/SELL/HOLD), amount ($), reasoning
- News source: NewsAPI (or similar), polled every 15 minutes
- Market data: 15-minute OHLCV candles

## Event Triggers (To Be Designed)

These are the critical logic pieces that gate when the expensive LLM agent runs:
1. Price volatility threshold (e.g., 2%+ move in 15 min)
2. News keyword detection (e.g., 'FDA approval', 'earnings', 'CEO resignation')
3. Technical indicator crossover signals (e.g., golden cross, Bollinger Band lower touch)
