# Архитектура

    vendors -> src/data/ -> data/bars/*.parquet -> src/research/ -> backtest/
                                                       |
                                       src/risk/limits.py + kill_switch.py
                                                       |
                   src/execution/paper_runner.py -> live_runner.py -> broker
                                                       |
                                             journal/*.jsonl

## Инварианты

1. Один контракт данных: колонка ts (UTC), партиционирование по символу/таймфрейму.
2. Стратегия — чистая функция, не знает про риск и сайзинг.
3. Risk — единственный шлюз: любой ордер проходит check_order.
4. Kill switch переживает рестарт: файл risk/KILL_SWITCH.
5. Live только через APP_ENV=live + LIVE_CONFIRM=YES-I-AM-LIVE.
