# Simple Strategies Playground
Отдельный трек от global empire. Изолирован на сервере 176.12.79.100 в /opt/20261005-cryptospearmint/. НЕ трогает canonical server 109.172.6.35 (где живёт trading-desk, risk_v0, short 13D paper, monitoring).
## Stack: pandas numpy ccxt yfinance + Binance testnet. No KYC, no real money until 2-4 weeks positive paper.
## Symbols: BTCUSDT, ETHUSDT, SOLUSDT
## Strategies (10)
1. SMA cross (20/50)
2. EMA cross (12/26)
3. RSI OBOS (14, 30/70)
4. Bollinger Bounce (20, 2 sigma)
5. MACD cross (12/26/9)
6. Momentum (10d ROC)
7. Mean reversion (price < mid - 2 sigma)
8. Donchian breakout (20d)
9. RSI + BB combo
10. OBV divergence
## Flow
1. Backtest grid 2022-2024, 10 strategies x 3 symbols x tuning
2. Top-3 by Sharpe>1.0, DD<20%, hit>50%, trades>20
3. Paper testnet 2-4 weeks
4. If positive -> $10-100 live small ($10/trade, no market impact)
## Isolated from
canonical server 109.172.6.35, /root/trading-desk, /root/risk_v0, /root/env-scraper-wt, /root/short-13d-paper, monitoring stack.
