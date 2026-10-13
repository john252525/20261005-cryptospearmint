# Funding-carry V2 — sensitivity verdict
_generated: 2026-10-13T13:14:36.607988+00:00 | grid: `backtest/results/funding_carry_grid_20261013.parquet`_
## Grid (min_funding_bps × fee_tier), 90d BTC/ETH/SOL реальные Binance public
| min_funding | tier | trades_count | funding_pnl_usd | fees_usd | net_pnl_usd | sharpe | max_dd | hit_rate | funding_per_trade_bps | fees_per_trade_bps | ratio_funding_to_fees |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 0.500 | vip0 | 154 | 23.286 | 585.200 | -561.628 | -33.115 | -0.185 | 0.000 | 1.512 | 38.000 | 0.040 |
| 1.000 | vip0 | 58 | 10.149 | 220.400 | -207.943 | -17.086 | -0.069 | 0.000 | 1.750 | 38.000 | 0.046 |
| 2.000 | vip0 | 0 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |  |
| 3.000 | vip0 | 0 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |  |
| 5.000 | vip0 | 0 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |  |
| 0.500 | vip1_bnb | 154 | 23.286 | 400.400 | -376.828 | -31.718 | -0.124 | 0.000 | 1.512 | 26.000 | 0.058 |
| 1.000 | vip1_bnb | 58 | 10.149 | 150.800 | -138.343 | -16.611 | -0.046 | 0.000 | 1.750 | 26.000 | 0.067 |
| 2.000 | vip1_bnb | 0 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |  |
| 3.000 | vip1_bnb | 0 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |  |
| 5.000 | vip1_bnb | 0 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |  |
## Best combinations
- max net_pnl среди активных (trades>0): min_funding=1.0, tier=vip1_bnb, net=$-138.34, sharpe=-16.61, ratio=0.0673
(ячейки с 0 trades имеют net=$0.00 по определению и исключены)
- max ratio:   min_funding=1.0, tier=vip1_bnb, net=$-138.34, sharpe=-16.61, ratio=0.0673
- max min_funding с trades>0: **1.0 bps** (выше — ноль входов)
## Критерий positive expectancy: ratio_funding_to_fees > 1.5
Комбинаций с net>0: **0** / 10
Комбинаций с ratio>1.5: **0** / 10
## Verdict
**Закрыть гипотезу** для VIP0/VIP1 аккаунтов на 2024 H2, BTC/ETH/SOL.

Основания:
1. При min_funding_bps ≥ 2.0 за 90 дней было **0 сделок** — реальный funding за 8h
   на BTC/ETH/SOL в 2024 H2 не превышал 2 bps. Потолок funding в окне ~= 1.75 bps.
2. Лучший net = −$138.34 (vip1_bnb, min=1.0): ratio=0.067 vs порог 1.5, gap ×22.
3. Gross funding при min=0.5 = +$23.29 за 90d = +0.78%/квартал = +3.1%/год — это
   **до** комиссий; net = −$561.63 = −18.7% за квартал.
4. Капитал (от $5k до $20M) не помогает: fees pro-rata к notional, breakeven не
   достигается никаким размером счета при VIP0/VIP1.
## Когда гипотезу можно переоткрыть
- VIP ≥ 4 (round-trip ≤ 12 bps) **и** funding_mean ≥ 3 bps за 8h стабильно.
- Альткоин-бasket: SOL/memecoins дают всплески 10–50 bps funding; ratio там
  на порядок выше, но требует ручного universe и ограничения ноционала.
- Долгий горизонт (≥1 года) с реинвестированием funding: тогда +3.1%/год gross
  приближается к 3.5–3.8% после compounding — но всё равно ниже T-bills.
## Критичные assumptions (требуют теста на реальных testnet fill'ах)
1. **fees**: Binance VIP0 spot 10 bps / perp 5 bps — из fee schedule; vip1_bnb
   spot 6 / perp 3 — **estimate**, требует проверки актуальных ставок.
2. **slippage 2 bps/leg/side** — flat-константа, не из order book. Для $1000 ноги
   на BTC USDT-M это ближе к 0.5 bps, для SOL — к 3–5 bps, для альтов — 10+ bps.
3. **basis P&L** считается по mid-price 8h close, не по исполняемым bid/ask.
   Реальный round-trip spread сжигает ещё ~4–8 bps.
4. **funding timing**: `lastFundingRate` берётся из public REST, значение между
   poll'ами может измениться до settlement.
5. **not modeled**: cross-margin Binance, auto-transfer spot↔futures, borrow cost
   для short-spot ноги, partial fills на testnet.
## Breakeven капитал
**Не существует в текущей конфигурации.** Fees всех уровней линейно растут с
notional, а funding income — тоже линейно. Отношение ratio неизменно от размера
счёта. Единственный рычаг — снижение fees per bps через VIP-tier или повышение
funding_mean через альткоин-universe.
