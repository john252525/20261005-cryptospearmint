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

## Alt-universe extension (V3)
_generated: 2026-10-17T10:26:26.342599+00:00_
_grid: `backtest/results/funding_carry_grid_20261017.parquet` | distribution: `backtest/results/funding_distribution_20261017.parquet`_

Universe: BTCUSDT, ETHUSDT, SOLUSDT, DOGEUSDT, WIFUSDT, AVAXUSDT, LINKUSDT, ARBUSDT, OPUSDT. (PEPEUSDT skipped: Binance USDT-M uses 1000PEPEUSDT, spot uses PEPEUSDT.)

### Funding distribution per symbol (90d, per 8h event, bps)

| symbol | n_events | median_bps | mean_bps | p90_bps | p99_bps | max_bps | min_bps | pct_gt_5bps | pct_gt_10bps |
|---|---|---|---|---|---|---|---|---|---|
| BTCUSDT | 270 | 0.5408 | 0.5183 | 1.0000 | 1.0000 | 1.0000 | -0.4135 | 0.0000 | 0.0000 |
| ETHUSDT | 270 | 0.4156 | 0.4041 | 0.9833 | 1.0000 | 1.0000 | -1.1754 | 0.0000 | 0.0000 |
| SOLUSDT | 270 | 0.3493 | 0.3166 | 1.0000 | 1.0000 | 1.0000 | -1.3796 | 0.0000 | 0.0000 |
| DOGEUSDT | 270 | 0.7208 | 0.5764 | 1.0000 | 1.0000 | 1.0000 | -1.3699 | 0.0000 | 0.0000 |
| WIFUSDT | 540 | 0.5000 | 0.3719 | 0.5000 | 0.5000 | 0.5000 | -0.9464 | 0.0000 | 0.0000 |
| AVAXUSDT | 270 | 0.5496 | 0.4149 | 1.0000 | 1.0000 | 1.0000 | -2.4723 | 0.0000 | 0.0000 |
| LINKUSDT | 270 | 0.5653 | 0.5510 | 1.0000 | 1.0000 | 1.0000 | -1.4153 | 0.0000 | 0.0000 |
| ARBUSDT | 270 | 0.2505 | 0.0691 | 1.0000 | 1.0000 | 1.0000 | -3.8917 | 0.0000 | 0.0000 |
| OPUSDT | 270 | 0.8356 | 0.3994 | 1.0000 | 1.0000 | 1.0000 | -2.5701 | 0.0000 | 0.0000 |

### Sensitivity grid — basket portfolio (9 symbols), 6 min_funding × 3 tiers

| min_funding | tier | trades_count | funding_pnl_usd | fees_usd | net_pnl_usd | sharpe | max_dd | ratio_funding_to_fees |
|---|---|---|---|---|---|---|---|---|
| 0.5000 | vip0 | 541 | 87.9542 | 2055.8000 | -1965.1470 | -37.4873 | -0.2183 | 0.0428 |
| 1.0000 | vip0 | 291 | 46.3539 | 1105.8000 | -1064.5388 | -34.3088 | -0.1183 | 0.0419 |
| 2.0000 | vip0 | 13 | -0.2056 | 49.4000 | -52.6955 | -8.0531 | -0.0059 | -0.0042 |
| 3.0000 | vip0 | 3 | -0.0027 | 11.4000 | -13.7969 | -3.8677 | -0.0015 | -0.0002 |
| 5.0000 | vip0 | 0 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |  |
| 10.0000 | vip0 | 0 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |  |
| 0.5000 | vip1_bnb | 541 | 87.9542 | 1406.6000 | -1315.9470 | -35.0941 | -0.1462 | 0.0625 |
| 1.0000 | vip1_bnb | 291 | 46.3539 | 756.6000 | -715.3388 | -32.0731 | -0.0795 | 0.0613 |
| 2.0000 | vip1_bnb | 13 | -0.2056 | 33.8000 | -37.0955 | -7.6594 | -0.0041 | -0.0061 |
| 3.0000 | vip1_bnb | 3 | -0.0027 | 7.8000 | -10.1969 | -3.8513 | -0.0011 | -0.0003 |
| 5.0000 | vip1_bnb | 0 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |  |
| 10.0000 | vip1_bnb | 0 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |  |
| 0.5000 | vip4 | 541 | 87.9542 | 1082.0000 | -991.3470 | -32.8491 | -0.1101 | 0.0813 |
| 1.0000 | vip4 | 291 | 46.3539 | 582.0000 | -540.7388 | -29.8480 | -0.0601 | 0.0796 |
| 2.0000 | vip4 | 13 | -0.2056 | 26.0000 | -29.2955 | -7.2643 | -0.0033 | -0.0079 |
| 3.0000 | vip4 | 3 | -0.0027 | 6.0000 | -8.3969 | -3.8302 | -0.0009 | -0.0005 |
| 5.0000 | vip4 | 0 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |  |
| 10.0000 | vip4 | 0 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |  |

### Summary

- cells net>0: **0 / 18**
- cells ratio>1.0: **0 / 18**
- cells ratio>1.5: **0 / 18**
- cells with trades=0: **6 / 18**
- best net (active): min_funding=3.0, tier=vip4, trades=3, net=$-8.40, sharpe=-3.83
- best ratio (active): min_funding=0.5, tier=vip4, trades=541, ratio=0.0813, net=$-991.35

### Data-quality note (unresolved)

`p99_bps == max_bps` for 8 of 9 symbols; max funding = 1.0000 bps (WIF max = 0.5000 bps). `premiumIndex.interestRate = 0.00010000 = 1.0 bps` — positive funding appears pegged at the Binance USDT-M interest-rate floor. Negative funding ranges freely to -3.89 bps (ARBUSDT).

Two interpretations not resolved in this environment: (A) quiet regime with premiumIndex ≤ interestRate; (B) environment clips positive funding. Independent replication recommended.

Note: cells with min_funding=3.0 have trades=3 in all tiers because `funding_bps_8h ≤ -3.0` still triggers `short_spot_long_perp`; these are short-perp-flip events, not sustained carry. Net remains negative in all tiers.

### Verdict

**Final: close hypothesis for BTC/ETH/SOL/alt-universe at VIP0/VIP1/VIP4 on observed 90-day window.**

No cell reaches ratio>1.5. No cell reaches net>0. `%>5bps = 0` and `%>10bps = 0` across all 9 symbols. Max observed funding = 1.0 bps (interest-rate floor). Raising `min_funding_bps` above 2.0 eliminates all long-carry entries. Best active ratio = 0.0813 (threshold 1.5, gap ~18.5x).

### Reopen conditions

1. Independent source confirms alt funding >10 bps stable for 30+ days.
2. VIP4+ available (round-trip ≤ 10 bps).
3. Testnet confirms fill slippage ≤ 2 bps/leg/side for the basket.
