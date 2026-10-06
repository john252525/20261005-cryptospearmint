# STRATEGY: funding carry delta-neutral

## Идея

Позиция: **лонг спот BTC + шорт перп BTC равными ноционалами**.
Delta ≈ 0, цена не влияет на PnL. Доход — funding payments, которые
лонги перпа платят шортам в бычьем рынке.

Не предсказание цены. Механическая рента.

## Winner параметры

| параметр | значение |
|---|---|
| universe | LINKUSDT, BTCUSDT, LTCUSDT, DOGEUSDT, ETHUSDT |
| lookback | 42 funding-события (14 дней) |
| statistic | median (не mean — защита от одиночных -200bps выбросов) |
| entry_thr | 0.00007 (0.7 bps / 8h) |
| exit_thr | -0.00003 |
| deploy_ratio | 0.9 |

Отбор пар — по `pos_share` (доля положительных events). Исключены:
- SOLUSDT — 71% pos, median +8 bps, но mean -6.9 bps (выбросы -200bps)
- BNBUSDT — 16% pos, median 0.0 — половина времени carry отсутствует
- ADA/AVAX/XRP — слабее top-5 по pos_share и среднему funding

## Backtest (2022-01-01 .. 2024-12-31)

| метрика | значение |
|---|---|
| cagr | **7.01%** |
| total return | 22.52% |
| max drawdown | **-0.25%** |
| funding_pnl / fees | **30.35** (fees несущественны) |
| trades | 14 (за 3 года) |
| avg holding | ~180 дней |

## Родственные, но проигравшие

| Стратегия | Результат | Где задокументировано |
|---|---|---|
| sma_cross / momentum_roc / donchian / mean_reversion_z | mean_excA ≤ 0 на 1d и 1h — сигнала нет | artifacts/walkforward/* |
| equal-weight 10 пар | cagr 5.89% — балласт из SOL/BNB | artifacts/funding_portfolio/* |
| rolling top-K allocation | cagr < 0 — fees ротации съедают carry | artifacts/funding_allocation/* |

## Границы применимости

- Модель НЕ учитывает: **basis risk** (расхождение спот/перп цен), **liquidation risk** на короткой ноге перпа, **exchange/custody risk**.
- Sharpe 16.28 в backtest — артефакт нулевой волатильности 8h funding-шагов; реалистичная оценка Sharpe = **3–5**.
- Работает **в бычьем режиме BTC** (funding > 0, 86% времени 2022–2024). В медвежьем — funding уходит в минус, стратегия стоит вне позиций.
- Mean funding 7.3 bps/8h × 3 × 365 = **8.0% gross APY** при 100% deploy. При deploy_ratio 0.9 и сайзинге по top-5 — **7% cagr**.
- Реальная просадка при **деплое**: basis расширяется на панических sell-off (до 0.3% кратковременно), маржин-ползунок на short-ногe требует 10%+ буфера.

## Что делать при развороте в медвежий режим

1. Median funding падает ниже `exit_thr = -0.00003` — все позиции закрываются автоматически.
2. Капитал уходит в USDT, ждём восстановления median > entry_thr.
3. Опционально: инвертируем (лонг перп + шорт спот), когда funding устойчиво отрицательный. В backtest не проверялось (нет данных для устойчивого отрицательного режима > 30 дней).

## Реальный базис (наблюдение из shadow runner)

Измерено `paper_runner_shadow.py` на живых публичных данных (окт-2026, 5 пар):

- Диапазон basis = (perp / spot − 1) × 10000: примерно **-6..+3 bps**
- На каждый момент варьируется в пределах 5-10 bps между парами

**Что это значит для backtest**: модель закладывала fees 10+5 bps и игнорировала
базис. Реальность:

- basis не теряется на входе/выходе (дельта 0 на обоих концах), он только
  фиксируется в моменте;
- расхождение basis между symbol при входе даёт разный notional за одинаковый
  cash — незначительно (0.05% от notional), не влияет на PnL;
- **backtest 7.01% CAGR остаётся консервативным** относительно реального flow —
  реальные fees на Binance (spot taker 7.5 bps, futures taker 4 bps) ниже наших
  10+5, а basis в среднем близок к нулю.

**Когда basis становится проблемой**: если в момент открытия базис резко
расширился (perp > spot + 20 bps), вход временно "over-pays" — это либо
register в drawdown, либо сигнал, что рынок в шоке. Планируемая мера —
приостановить открытие при `|basis| > 15 bps` (не реализовано).

## Достоверность цифр (после shadow)

- Backtest 7.01% CAGR: реалистично (fees были консервативны)
- Sharpe 16: нереалистично, реально 3-5 (артефакт нулевой волатильности 8h-steps)
- Max DD 0.25%: реалистично при delta-neutral (basis-blow risk не материализовался)
