# Monitoring endpoints

Deployed on 2026-10-17 on canonical host `pixinvent.dev` / `109.172.6.35`.
**Host-native** Prometheus 2.55 + Grafana 11.3 — Docker containers are
blocked in this VM by cgroup fs restrictions (details below).

| Service | Local port | Public URL |
|---|---|---|
| Prometheus | 57447 | http://109.172.6.35:57447/ |
| Grafana    | 36308 | http://109.172.6.35:36308/login  (admin/admin) |
| Dashboard  | — | http://109.172.6.35:36308/d/trading-desk/ |
| Exporter   | 9100 | http://109.172.6.35:9100/metrics |

## systemd units (all three under systemd)

```
systemctl status trading-metrics
systemctl restart trading-metrics
journalctl -u trading-metrics -f

systemctl status prometheus
systemctl restart prometheus
journalctl -u prometheus -f

systemctl status grafana
systemctl restart grafana
journalctl -u grafana -f
```

All three services are `systemctl enable`d — **they survive reboot**.

## Config locations

- Prometheus:    `/opt/prometheus/prometheus.yml`
- Grafana pro.:  `/opt/grafana/conf/provisioning/{datasources,dashboards}/`
- Repo (source-of-truth): `infra/grafana/provisioning/`, `infra/systemd/`,
  `infra/docker/` (docker unused on this VM)

## Sync from repo → live

```
cp -f infra/grafana/provisioning/datasources/prometheus.yml \
   /opt/grafana/conf/provisioning/datasources/prometheus.yml
cp -f infra/grafana/provisioning/dashboards/trading.json \
   /opt/grafana/conf/provisioning/dashboards/trading.json
systemctl restart grafana
```

## Exporter

The exporter polls the SQLite state DB every 5s and exposes 11 `risk_*`
metrics. It runs from the repo checkout (`/root/trading-desk`) via system
python3 (deps: `prometheus_client`, `loguru`, `pyyaml`).

## Known limitation: Docker containers

`docker.io` is installed and daemon starts, but container create fails
with:

```
failed to set user-requested vfs flags on bind-mount:
remount with locked flags MS_NOSUID|MS_NODEV|MS_NOEXEC|MS_RELATIME
re-applied: ... permission denied
```

This is a sandbox-level restriction on `cgroup` remount inside this VM —
not fixable from userspace. Prometheus and Grafana are instead deployed
as native tarballs under `/opt/` and served by systemd units. Docker
compose file is retained in the repo for migration to an unrestricted VM.

## Firewall

No local iptables rules (`policy ACCEPT`). Provider firewall allows TCP
ports 30000-60000 and 9100; verified with external `curl` from this server
to its own public IP.
