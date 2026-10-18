import sqlite3
import time
from prometheus_client import start_http_server, Gauge
from .config import Short13DSettings


positions_open = Gauge('short_13d_positions_open', 'Number of open positions')
notional_total = Gauge('short_13d_notional_total_usd', 'Total notional USD of open positions')
realized_pnl = Gauge('short_13d_realized_pnl_usd', 'Total realized PnL of closed positions')
fills_total = Gauge('short_13d_fills_total', 'Total number of entries')


def update_metrics():
    s = Short13DSettings()
    try:
        c = sqlite3.connect(s.state_db)
        n_open = c.execute("SELECT COUNT(*) FROM paper_positions WHERE status='OPEN'").fetchone()[0]
        notional = c.execute("SELECT COALESCE(SUM(notional_usd),0) FROM paper_positions WHERE status='OPEN'").fetchone()[0]
        pnl = c.execute("SELECT COALESCE(SUM(realized_pnl_usd),0) FROM paper_positions WHERE status='CLOSED'").fetchone()[0]
        total = c.execute("SELECT COUNT(*) FROM paper_positions").fetchone()[0]
        positions_open.set(n_open)
        notional_total.set(notional)
        realized_pnl.set(pnl)
        fills_total.set(total)
        c.close()
    except Exception as e:
        print('metric update error', e)


def run_exporter(port=9103):
    start_http_server(port)
    print(f'http exporter on :{port}', flush=True)
    while True:
        update_metrics()
        time.sleep(5)


if __name__ == '__main__':
    run_exporter(9103)
