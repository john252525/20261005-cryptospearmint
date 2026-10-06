# Runbook

## Ежедневный минимум

    make fetch-crypto SYMBOL=BTCUSDT INTERVAL=1m DAYS=7
    make backtest
    make paper
    make lint
    make type
    make test

## Аварийный стоп

    touch risk/KILL_SWITCH
    cat risk/KILL_SWITCH
    rm risk/KILL_SWITCH

## Инцидент: расхождение с брокером

1. touch risk/KILL_SWITCH
2. Сверить journal/trades-*.jsonl с брокерским стейтментом.
3. Закрыть расхождение вручную.
4. Разобрать root cause, добавить проверку в src/risk/limits.py.
5. rm risk/KILL_SWITCH — только после разбора.
