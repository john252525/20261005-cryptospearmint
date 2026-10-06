# Funding carry — backtest conclusion (2026-10-06)

## Прогоны

| Конфиг | Symbols | Fees | Ret | Sharpe | Trades |
|---|---|---|---|---|---|
| funding_carry_1y | BTC | retail 10/5 bps | +0.43% | 3.01 | 2 |
| basket | BTC ETH SOL BNB XRP | retail | +0.12% | 1.05 | 13 |
| basket_vip1 | то же | VIP1 4/3 bps | +0.30% | 4.61 | 13 |

## Модель

Delta-neutral: long spot + short perp, long-hold per signals
`strategies/funding_carry.py`. PnL — funding credits минус round-trip fees.
Equity=const между funding-инкрементами и trade-close (модель нейтральна,
подтверждено: BTC упал -38% в первом trade, PnL остался положительным).

## Вывод

**Стратегия не имеет смысла на этих символах при 1x notional.**

- Funding edge: ~51 bps/год на notional (Binance, large-caps, 2025-2026).
- Fees retail: ~40 bps/год на капитал при текущей ротации.
- Net: ~6 bps.

Для 3%/год нужен effective leverage ~10x. Институциональный потолок для
delta-neutral с двумя ногами — 2-5x (spot 100% + perp margin). Даже при 5x
ожидаемая доходность ~1.5% — ниже безрисковой.

Sharpe 4.61 на vip1 — правдивый, но незначимый: высокий Sharpe на 0.3%
доходности не создаёт бизнеса.

## Что было бы дальше, если продолжать

1. Cross-venue basis (Binance spot / Bybit perp). Премия 5-15%/год, в 5-10×
   от within-venue. Отдельный движок.
2. Multi-symbol с 20+ парами и dynamic weighting (пропорционально current rate).
   Ожидаемая дельта к текущему — +50-100 bps.
3. Maker rebates на spot (Binance VIP4+ или BNB discount). Режет fees в 3-5×.

Ни одно из трёх не превращает 0.3% в 3% без одной из оставшихся опций.
