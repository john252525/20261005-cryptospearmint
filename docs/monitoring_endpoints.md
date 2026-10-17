# Monitoring endpoints

Deployed on 2026-10-17 — host-native Prometheus 2.55 + Grafana 11.3.
Docker containers blocked in this VM by cgroup fs restrictions
(`failed to set user-requested vfs flags on bind-mount: remount with locked
flags ... permission denied` at container start, even with vfs driver).

| Service | Local port | Public URL |
|---|---|---|
| Prometheus | 57447 | http://109.172.6.35:57447/ |
| Grafana    | 36308 | http://109.172.6.35:36308/login  (admin/admin) |
| Exporter   | 9100 | http://109.172.6.35:9100/metrics |

## Running processes

- `/opt/prometheus/prometheus` — systemd unit `prometheus.service` (running via nohup now; unit enabled for reboot)
- `/opt/grafana/bin/grafana` — systemd unit `grafana.service` (running via nohup now; unit enabled for reboot)
- `src/monitoring/http_exporter.py` — python process, log `/tmp/exporter.log`

## Config locations

- Prometheus:    `/opt/prometheus/prometheus.yml`
- Grafana pro.:  `/opt/grafana/conf/provisioning/{datasources,dashboards}/`
- Repo (source-of-truth): `infra/grafana/provisioning/`, `infra/docker/` (docker unused on this VM)

## Sync from repo → live

```
sudo cp -f infra/grafana/provisioning/datasources/prometheus.yml \
   /opt/grafana/conf/provisioning/datasources/prometheus.yml
sudo cp -f infra/grafana/provisioning/dashboards/trading.json \
   /opt/grafana/conf/provisioning/dashboards/trading.json
sudo systemctl restart grafana.service
```

## Docker note

`docker.io` installed, daemon starts, but container create fails on
`cgroup` remount due to sandbox restrictions. Prometheus/Grafana deployed
as native tarballs instead, repointing the same dashboards/datasources.
