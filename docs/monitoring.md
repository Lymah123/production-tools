# Monitoring Guide

Complete guide to setting up and using the monitoring stack.

---

## 📋 Table of Contents

1. [Quick Start](#quick-start)
2. [Architecture](#architecture)
3. [Prometheus Setup](#prometheus-setup)
4. [Grafana Setup](#grafana-setup)
5. [Custom Metrics](#custom-metrics)
6. [Alerting](#alerting)
7. [Troubleshooting](#troubleshooting)

---

## 🚀 Quick Start

### Start Monitoring Stack

```bash
cd monitoring
./setup_monitoring.sh
```

**Access points:**
- Prometheus: http://localhost:9090
- Grafana: http://localhost:3000 (admin/admin)
- Metrics: http://localhost:8000/metrics

### Start Metrics Exporter

```bash
# Production mode
python monitoring/metrics_tracker.py --port 8000 --interval 300

# Test mode with simulated data
python monitoring/test_metrics.py --port 8000 --interval 30
```

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────┐
│          Cloud Providers                     │
│     (AWS, Azure, GCP, OpenAI)               │
└──────────────────┬──────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────┐
│       Cost Tracker (cost_tracker.py)        │
│   - Fetches costs from APIs                 │
│   - Processes and aggregates data           │
└──────────────────┬──────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────┐
│    Metrics Exporter (metrics_tracker.py)    │
│   - Exposes Prometheus metrics              │
│   - HTTP endpoint: :8000/metrics            │
└──────────────────┬──────────────────────────┘
                   │
                   ▼ (scrapes every 15s)
┌─────────────────────────────────────────────┐
│         Prometheus (:9090)                  │
│   - Stores time-series data                 │
│   - Evaluates alert rules                   │
│   - Provides PromQL query interface         │
└──────────────────┬──────────────────────────┘
                   │
                   ▼ (queries)
┌─────────────────────────────────────────────┐
│          Grafana (:3000)                    │
│   - Visualizes metrics                      │
│   - Dashboards and panels                   │
│   - Alerting and notifications              │
└─────────────────────────────────────────────┘
```

---

## 📊 Prometheus Setup

### Configuration

```yaml
# monitoring/prometheus/prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'cost-monitoring'
    static_configs:
      - targets: ['host.docker.internal:8000']
    scrape_interval: 15s

alerting:
  alertmanagers:
    - static_configs:
        - targets: ['alertmanager:9093']

rule_files:
  - 'alerts.yml'
```

### Alert Rules

```yaml
# monitoring/prometheus/alerts.yml
groups:
  - name: cost_alerts
    interval: 1m
    rules:
      - alert: HighDailyCost
        expr: sum(cloud_cost_daily) > 1000
        for: 5m
        labels:
          severity: warning
          team: finops
        annotations:
          summary: "Daily cloud cost exceeds $1000"
          description: "Current: ${{ $value | humanize }}"
      
      - alert: CostSpike
        expr: |
          sum(cloud_cost_daily) / 
          sum(cloud_cost_daily offset 1d) > 1.5
        for: 10m
        labels:
          severity: critical
        annotations:
          summary: "Cost spike detected (50% increase)"
      
      - alert: MetricsExporterDown
        expr: up{job="cost-monitoring"} == 0
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "Metrics exporter is down"
```

### Querying with PromQL

**Basic queries:**
```promql
# Total daily cost
sum(cloud_cost_daily)

# Cost by provider
sum by (provider) (cloud_cost_daily)

# Top 5 expensive services
topk(5, cloud_cost_total)

# Monthly projection
sum(cloud_cost_monthly_projection)
```

**Advanced queries:**
```promql
# Rate of cost increase
rate(cloud_cost_daily[1h])

# Week-over-week comparison
sum(cloud_cost_daily) / sum(cloud_cost_daily offset 7d)

# Predict cost in 7 days
predict_linear(cloud_cost_daily[1d], 7*24*3600)

# Anomaly detection
abs(cloud_cost_daily - avg_over_time(cloud_cost_daily[7d])) > 
  2 * stddev_over_time(cloud_cost_daily[7d])
```

---

## 📈 Grafana Setup

### Initial Setup

1. **Access Grafana**: http://localhost:3000
2. **Login**: admin / admin
3. **Change password** (required on first login)

### Add Prometheus Data Source

1. Go to **Configuration → Data Sources**
2. Click **Add data source**
3. Select **Prometheus**
4. Set URL: `http://prometheus:9090`
5. Click **Save & Test**

### Import Dashboard

1. Go to **Dashboards → Import**
2. Upload `monitoring/grafana/dashboard.json`
3. Select Prometheus data source
4. Click **Import**

### Create Custom Dashboard

```json
{
  "title": "Cloud Cost Overview",
  "panels": [
    {
      "title": "Daily Cost by Provider",
      "targets": [
        {
          "expr": "sum by (provider) (cloud_cost_daily)",
          "legendFormat": "{{provider}}"
        }
      ],
      "type": "graph"
    },
    {
      "title": "Total Monthly Projection",
      "targets": [
        {
          "expr": "sum(cloud_cost_monthly_projection)"
        }
      ],
      "type": "stat",
      "format": "currencyUSD"
    }
  ]
}
```

### Grafana Alerts

**Create alert rule:**

1. Go to **Alerting → Alert rules**
2. Click **New alert rule**
3. Set query: `sum(cloud_cost_daily) > 1000`
4. Configure notification channel (Slack/Email)
5. Save

---

## 📊 Custom Metrics

### Available Metrics

#### Gauges (Current Values)

| Metric | Description | Labels |
|--------|-------------|--------|
| `cloud_cost_total` | Per-service cost | provider, service, region |
| `cloud_cost_daily` | Daily cost by provider | provider |
| `cloud_cost_monthly_projection` | Projected monthly cost | provider |

#### Counters (Cumulative)

| Metric | Description | Labels |
|--------|-------------|--------|
| `cost_fetch_total` | Number of fetch operations | provider, status |
| `cost_alerts_total` | Number of alerts triggered | alert_type, provider |

#### Histograms (Distributions)

| Metric | Description | Labels |
|--------|-------------|--------|
| `cost_fetch_duration_seconds` | Fetch operation duration | provider |

### Query Examples

```promql
# Average daily cost over 7 days
avg_over_time(sum(cloud_cost_daily)[7d])

# Fetch success rate
rate(cost_fetch_total{status="success"}[5m]) / 
rate(cost_fetch_total[5m])

# 95th percentile fetch time
histogram_quantile(0.95, 
  rate(cost_fetch_duration_seconds_bucket[5m])
)

# Alert frequency
sum by (alert_type) (
  increase(cost_alerts_total[24h])
)
```

---

## 🚨 Alerting

### Slack Integration

**Configure webhook:**

```yaml
# ~/.cost_tracker.yaml
slack:
  enabled: true
  webhook_url: ${SLACK_WEBHOOK_URL}
  channel: "#cost-alerts"
  mentions: ["@finops-team"]
```

**Test alert:**
```bash
python monitoring/cost_tracker.py --test-alert
```

### Email Notifications

```yaml
# ~/.cost_tracker.yaml
notifications:
  email:
    enabled: true
    smtp_host: smtp.gmail.com
    smtp_port: 587
    from: alerts@company.com
    to: [finance@company.com, devops@company.com]
    username: ${SMTP_USER}
    password: ${SMTP_PASSWORD}
```

### PagerDuty Integration

```yaml
# prometheus/alertmanager.yml
receivers:
  - name: 'pagerduty'
    pagerduty_configs:
      - service_key: ${PAGERDUTY_SERVICE_KEY}
        description: "{{ .GroupLabels.alertname }}"

route:
  receiver: 'pagerduty'
  group_wait: 10s
  group_interval: 5m
  repeat_interval: 3h
  routes:
    - match:
        severity: critical
      receiver: pagerduty
```

---

## 🧪 Testing

### Test with Simulated Data

```bash
# Start simulator
python monitoring/test_metrics.py --port 8000 --interval 30

# Simulate cost spike every 5 iterations
python monitoring/test_metrics.py --spike-every 5
```

### Verify Prometheus Scraping

```bash
# Check if Prometheus is scraping
curl http://localhost:9090/api/v1/targets

# Query metrics directly
curl http://localhost:9090/api/v1/query?query=cloud_cost_daily
```

### Load Testing

```bash
# Stress test metrics endpoint
for i in {1..100}; do
  curl http://localhost:8000/metrics &
done
wait
```

---

## 🔧 Troubleshooting

### Metrics Not Showing

**Check exporter is running:**
```bash
curl http://localhost:8000/metrics
```

**Check Prometheus targets:**
http://localhost:9090/targets

**Check logs:**
```bash
docker-compose logs -f prometheus
docker-compose logs -f grafana
```

### High Memory Usage

**Prometheus retention:**
```yaml
# prometheus.yml
storage:
  tsdb:
    retention.time: 15d  # Reduce from default 30d
    retention.size: 50GB
```

**Reduce scrape frequency:**
```yaml
scrape_configs:
  - job_name: 'cost-monitoring'
    scrape_interval: 60s  # Increase from 15s
```

### Grafana Dashboard Not Loading

**Rebuild dashboard cache:**
```bash
docker-compose restart grafana
```

**Check data source:**
1. Go to Configuration → Data Sources
2. Click Prometheus
3. Click "Save & Test"

---

## 📚 Additional Resources

- [Prometheus Documentation](https://prometheus.io/docs/)
- [Grafana Documentation](https://grafana.com/docs/)
- [PromQL Guide](https://prometheus.io/docs/prometheus/latest/querying/basics/)
- [Grafana Dashboard Examples](https://grafana.com/grafana/dashboards/)

---

**Need help?** Check [Troubleshooting Guide](troubleshooting.md) or open an issue.