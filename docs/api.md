# API Reference

Complete API documentation for all production tools.

---

## 📋 Table of Contents

1. [Secrets Manager API](#secrets-manager-api)
2. [Cost Tracker API](#cost-tracker-api)
3. [Metrics Exporter API](#metrics-exporter-api)
4. [Deployment API](#deployment-api)

---

## 🔐 Secrets Manager API

### CLI Commands

#### `put` - Store a Secret

```bash
python security/secrets_manager.py put <secret-name> [OPTIONS]
```

**Options:**
- `--key <key>` - Secret key
- `--value <value>` - Secret value
- `--file <path>` - JSON file containing secrets
- `--backend <aws|vault>` - Backend to use (default: from config)

**Examples:**
```bash
# Store single value
python security/secrets_manager.py put api-key \
  --key token --value "sk-123"

# Store from JSON
python security/secrets_manager.py put db-config \
  --file db-credentials.json
```

#### `get` - Retrieve a Secret

```bash
python security/secrets_manager.py get <secret-name> [OPTIONS]
```

**Options:**
- `--key <key>` - Get specific key (optional)
- `--backend <aws|vault>` - Backend to use

**Examples:**
```bash
# Get entire secret
python security/secrets_manager.py get api-key

# Get specific key
python security/secrets_manager.py get api-key --key token
```

#### `list-secrets` - List All Secrets

```bash
python security/secrets_manager.py list-secrets [OPTIONS]
```

**Options:**
- `--backend <aws|vault>` - Backend to use

#### `delete` - Delete a Secret

```bash
python security/secrets_manager.py delete <secret-name> [OPTIONS]
```

**Options:**
- `--force` - Skip confirmation
- `--backend <aws|vault>` - Backend to use

#### `rotate` - Rotate a Secret

```bash
python security/secrets_manager.py rotate <secret-name> [OPTIONS]
```

**Options:**
- `--new-value <value>` - New secret value
- `--backend <aws|vault>` - Backend to use

---

## 📊 Cost Tracker API

### CLI Commands

#### Run Cost Tracker

```bash
python monitoring/cost_tracker.py [OPTIONS]
```

**Options:**
- `--output <path>` - Save report to JSON file
- `--verbose` - Enable verbose logging

**Output Format:**
```json
{
  "analysis": {
    "total_cost": 1234.56,
    "by_provider": {
      "aws": 789.12,
      "azure": 445.44
    },
    "by_service": {
      "ec2": 500.00,
      "s3": 289.12
    },
    "timestamp": "2025-11-02T03:00:00Z"
  },
  "metrics": [
    {
      "service": "ec2",
      "provider": "aws",
      "cost": 500.00,
      "currency": "USD",
      "timestamp": "2025-11-02T03:00:00Z"
    }
  ]
}
```

### Python API

```python
from monitoring.cost_tracker import CostTracker, CostMetric

# Initialize tracker
tracker = CostTracker(config_dict_or_path)

# Collect costs from all providers
metrics = tracker.collect()

# Analyze costs
analysis = tracker.analyze()

# Check for alerts
alerts = tracker.check_alerts(analysis)

# Send notifications
for alert in alerts:
    if 'slack' in alert['channels']:
        tracker.send_slack(alert)
    if 'email' in alert['channels']:
        tracker.send_email(alert)
```

---

## 📈 Metrics Exporter API

### CLI Commands

```bash
python monitoring/metrics_tracker.py [OPTIONS]
```

**Options:**
- `--port <int>` - HTTP server port (default: 8000)
- `--interval <int>` - Collection interval in seconds (default: 300)
- `--config <path>` - Path to cost tracker config

**Example:**
```bash
python monitoring/metrics_tracker.py \
  --port 8000 \
  --interval 60 \
  --config ~/.cost_tracker.yaml
```

### Prometheus Metrics

#### Gauges

**`cloud_cost_total`** - Per-service cost
```promql
cloud_cost_total{provider="aws", service="ec2", region="us-east-1"}
```

**`cloud_cost_daily`** - Daily cost by provider
```promql
cloud_cost_daily{provider="aws"}
```

**`cloud_cost_monthly_projection`** - Projected monthly cost
```promql
cloud_cost_monthly_projection{provider="aws"}
```

#### Counters

**`cost_fetch_total`** - Number of fetch operations
```promql
cost_fetch_total{provider="all", status="success"}
```

**`cost_alerts_total`** - Number of alerts triggered
```promql
cost_alerts_total{alert_type="threshold", provider="aws"}
```

#### Histograms

**`cost_fetch_duration_seconds`** - Fetch operation duration
```promql
cost_fetch_duration_seconds{provider="all"}
```

### HTTP Endpoints

**`GET /metrics`** - Prometheus metrics endpoint
```bash
curl http://localhost:8000/metrics
```

---

## 🚢 Deployment API

### CLI Commands

```bash
./deployment/deploy.sh <environment> [OPTIONS]
```

**Environments:**
- `staging` - Staging environment
- `production` - Production environment

**Options:**
- `--strategy <rolling|blue-green>` - Deployment strategy
- `--rollback` - Rollback to previous version
- `--version <version>` - Deploy specific version
- `--skip-tests` - Skip health checks
- `--dry-run` - Show what would be deployed

**Examples:**
```bash
# Standard deployment
./deployment/deploy.sh production

# Blue-green deployment
./deployment/deploy.sh production --strategy blue-green

# Rollback
./deployment/deploy.sh production --rollback

# Dry run
./deployment/deploy.sh staging --dry-run
```

---

## 🔧 Configuration Validator API

### Python API

```python
from validation.config_validator import ConfigValidator

# Initialize validator
validator = ConfigValidator('config.yaml')

# Validate
result = validator.validate()

if result['valid']:
    print("✅ Configuration is valid")
else:
    print("❌ Validation errors:")
    for error in result['errors']:
        print(f"  - {error}")
```

---

## 📚 Additional Resources

- [Usage Guide](usage.md) - Detailed usage examples
- [Security Guide](security.md) - Security best practices
- [Monitoring Guide](monitoring.md) - Monitoring setup
- [Troubleshooting](troubleshooting.md) - Common issues

---

**Need help?** Open an issue on GitHub.