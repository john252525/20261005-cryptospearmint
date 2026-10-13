# funding-carry (delta-neutral spot + perp)

Публичные данные Binance/Bybit -> сигнал funding/basis -> event-driven backtest ->
paper-runner на Binance Testnet (spot + USDT-M) -> SQLite-учёт -> дневной отчёт.

Дерево (4-пробельный отступ = markdown-кодблок):

    src/
        strategies/funding_carry/{config,signal,gates,backtest}.py
        execution/funding_carry_runner.py
        paper/portfolio.py
        report/funding_carry_report.py
    configs/funding_carry.yaml
    tests/
    Makefile

## Быстрый старт

    make install
    make test
    make backtest-funding-synthetic        # офлайн, детерминированный
    make backtest-funding                  # 90 дней, Binance public
    BINANCE_TESTNET_API_KEY=... BINANCE_TESTNET_API_SECRET=... make paper-funding
    make report-funding

Артефакты:
- backtest/results/funding_carry_YYYYMMDD.parquet — daily equity
- backtest/results/funding_carry_YYYYMMDD.metrics.json — метрики
- journal/funding_carry.jsonl — append-only журнал исполнения
- state/funding_carry.db — SQLite (positions / orders / funding_events / pnl_snapshots)

## Cost model

Binance VIP0 taker (source: Binance Spot Fee Schedule, Binance USDⓈ-M Futures Fee Schedule):
- spot taker — 0.10% (10.0 bps)
- perp taker — 0.05% ( 5.0 bps)
- slippage — 2 bps per leg per side (допущение, не измерение)

Одна смена состава ног = 19 bps. Round-trip (открытие + закрытие) = 38 bps.
Валидируется в FundingCarrySettings.cost_bps_per_leg_change.

## Что НЕ делает этот код

Явные границы. Всё ниже — принятые допущения модели, а не реализованные фичи.

1. **Не учитывает latency при входе.** Сигнал читается с публичного REST, ордера
   уходят следующим round-trip. Между lastFundingRate и фактическим fill цена
   другая. Backtest использует 8h close через merge_asof.

2. **Не учитывает частичные fills на testnet.** Обе ноги считаются исполненными
   целиком (FILLED). При частичном fill hedge теряет дельта-нейтральность,
   код это не ловит.

3. **Не учитывает funding reversal risk.** Знак funding считается стабильным до
   следующего settlement. Между поллами (до 30 с) и cooldown (60 с) знак может
   перевернуться — позиция удержит неоплаченный риск.

4. **Не работает с cross-margin constraints на testnet.** Spot- и futures-кошельки
   независимы, авто-transfer не реализован. Если на futures-нога не хватило
   маржи — runner сделает unwind спота и запишет no_op, но деньги сам не переведёт.

5. **Не валидирует ключи перед запуском.** Нет ключей — DRY-RUN (только сигналы
   и учёт). Ключи неверные/без прав — ошибка всплывёт только в момент первого
   ордера.

6. **Не моделирует borrow/funding short-spot ноги.** Для short_spot_long_perp
   нужен margin-borrow спота; стоимость borrow не учтена. На testnet spot-margin
   часто недоступен — направление фактически неисполнимо.

7. **Не моделирует ликвидность.** Slippage 2 bps/leg — константа из конфига,
   без связи с размером ордера, глубиной книги и волатильностью.

8. **Не строит order-book по глубине.** Basis считается по mid, а не по
   executable bid/ask обеих ног.

9. **Backtest использует одну цену на бар.** 8h close spot и 8h close perp,
   слитые merge_asof. Внутрибарный путь (high/low) не восстанавливается.

10. **Fee-модель — Binance VIP0 taker.** BNB-дискаунты, VIP-тиры, maker-ребейты
    не учтены. Slippage 2 bps/leg — допущение, не измерение.

11. **Нет мониторинга и алертинга.** Нет healthcheck, нет alerting на
    расхождения дельты. Kill-switch только по slippage per-leg
    (kill_if_slippage_bps_gt).

12. **SQLite — single-writer.** Параллельный запуск двух runner'ов на одной БД
    приведёт к блокировкам и/или рассинхронизации позиций.
