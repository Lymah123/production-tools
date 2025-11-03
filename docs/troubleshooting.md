# Troubleshooting Guide

Common issues and solutions for production tools.

---

## 📋 Table of Contents

1. [Secrets Manager Issues](#secrets-manager-issues)
2. [Cost Tracker Issues](#cost-tracker-issues)
3. [Monitoring Stack Issues](#monitoring-stack-issues)
4. [Deployment Issues](#deployment-issues)
5. [Docker Issues](#docker-issues)

---

## 🔐 Secrets Manager Issues

### Issue: "Unable to locate credentials"

**Symptoms:**
```
botocore.exceptions.NoCredentialsError: Unable to locate credentials
```

**Solutions:**

1. **Check AWS credentials:**
```bash
# Verify credentials are configured
aws sts get-caller-identity

# Configure if missing
aws configure
```

2. **Set AWS profile:**
```bash
export AWS_PROFILE=production
```

3. **Check ~/.aws/credentials:**
```ini
[default]
aws_access_key_id = YOUR_KEY
aws_secret_access_key = YOUR_SECRET
```

---

### Issue: "Vault authentication failed"

**Symptoms:**
```
hvac.exceptions.InvalidRequest: permission denied
```

**Solutions:**

1. **Check Vault connection:**
```bash
vault status
```

2. **Login to Vault:**
```bash
vault login
```

3. **Verify token:**
```bash
export VAULT_TOKEN=$(vault print token)
echo $VAULT_TOKEN
```

4. **Check Vault address:**
```bash
export VAULT_ADDR=https://vault.company.com
```

---

### Issue: "Secret not found"

**Symptoms:**
```
ResourceNotFoundException: Secret not found
```

**Solutions:**

1. **List all secrets:**
```bash
python security/secrets_manager.py list-secrets
```

2. **Check secret name:**
```bash
# AWS format: prod/api-key
# Vault format: secret/prod/api-key
```

3. **Verify backend:**
```bash
python security/secrets_manager.py get prod/api-key --backend aws
```

---

## 📊 Cost Tracker Issues

### Issue: "No metrics collected"

**Symptoms:**
```
2025-11-02 03:41:42,973 - INFO - Total metrics: 0
2025-11-02 03:41:42,973 - INFO - Collected 0 metrics
```

**Solutions:**

1. **Check provider credentials:**

**AWS:**
```bash
# Test AWS access
aws ce get-cost-and-usage \
  --time-period Start=2025-11-01,End=2025-11-02 \
  --granularity DAILY \
  --metrics UnblendedCost
```

**Azure:**
```bash
# Login
az login

# Verify subscription
az account show
```

**GCP:**
```bash
# Check auth
gcloud auth list

# Set project
gcloud config set project my-project
```

2. **Enable providers in config:**
```yaml
# ~/.cost_tracker.yaml
providers:
  aws:
    enabled: true  # Make sure this is true
    region: us-east-1
```

3. **Check IAM permissions:**

**AWS required permissions:**
```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": [
      "ce:GetCostAndUsage",
      "ce:GetCostForecast"
    ],
    "Resource": "*"
  }]
}
```

---

### Issue: "'list' object has no attribute 'get'"

**Symptoms:**
```
ERROR - Failed to collect metrics: 'list' object has no attribute 'get'
```

**Solution:**

Update config format in `~/.cost_tracker.yaml`:

```yaml
# ❌ Wrong (list format)
providers:
  - name: aws
    enabled: true

# ✅ Correct (dict format)
providers:
  aws:
    enabled: true
    region: us-east-1
```

---

### Issue: "Slack notifications not working"

**Symptoms:**
```
[yellow]SLACK_WEBHOOK not set[/]
```

**Solutions:**

1. **Set Slack webhook:**
```bash
export SLACK_WEBHOOK_URL="https://hooks.slack.com/services/YOUR/WEBHOOK/URL"
```

2. **Update config:**
```yaml
slack:
  enabled: true
  webhook_url: ${SLACK_WEBHOOK_URL}
  channel: "#cost-alerts"
```

3. **Test webhook:**
```bash
curl -X POST -H 'Content-type: application/json' \
  --data '{"text":"Test alert"}' \
  $SLACK_WEBHOOK_URL
```

---

## 📈 Monitoring Stack Issues

### Issue: "Prometheus target down"

**Symptoms:**
- Prometheus shows target as "DOWN"
- http://localhost:9090/targets shows red status

**Solutions:**

1. **Check metrics exporter is running:**
```bash
curl http://localhost:8000/metrics
```

2. **Restart metrics exporter:**
```bash
python monitoring/metrics_tracker.py --port 8000
```

3. **Check Docker networking:**
```bash
# From inside Prometheus container
docker exec prometheus ping host.docker.internal
```

4. **Update Prometheus config:**
```yaml
# prometheus/prometheus.yml
scrape_configs:
  - job_name: 'cost-monitoring'
    static_configs:
      - targets: ['host.docker.internal:8000']  # Use this for Windows/Mac
      # - targets: ['172.17.0.1:8000']          # Use this for Linux
```

---

### Issue: "Grafana dashboard not loading"

**Symptoms:**
- Dashboard shows "No data" or empty panels

**Solutions:**

1. **Check Prometheus data source:**
- Go to Configuration → Data Sources
- Click Prometheus
- Click "Save & Test" (should show green checkmark)

2. **Verify data in Prometheus:**
```
http://localhost:9090/graph
Query: cloud_cost_daily
```

3. **Check time range:**
- Dashboard time picker (top right)
- Set to "Last 15 minutes" or "Last 1 hour"

4. **Rebuild dashboard:**
```bash
# Re-import dashboard
# Dashboards → Import → Upload monitoring/grafana/dashboard.json
```

---

### Issue: "Port already in use"

**Symptoms:**
```
Error starting userland proxy: listen tcp 0.0.0.0:8000: bind: address already in use
```

**Solutions:**

1. **Find process using port:**

**Windows:**
```powershell
netstat -ano | findstr :8000
taskkill /PID <PID> /F
```

**Linux/Mac:**
```bash
lsof -i :8000
kill -9 <PID>
```

2. **Use different port:**
```bash
python monitoring/metrics_tracker.py --port 8001
```

3. **Update docker-compose.yml:**
```yaml
services:
  prometheus:
    ports:
      - "9091:9090"  # Change external port
```

---

### Issue: "Docker containers won't start"

**Symptoms:**
```
ERROR: ... Container exited with code 1
```

**Solutions:**

1. **Check Docker is running:**
```bash
docker ps
```

2. **Check logs:**
```bash
docker-compose logs prometheus
docker-compose logs grafana
```

3. **Remove old containers:**
```bash
docker-compose down -v
docker-compose up -d
```

4. **Check disk space:**
```bash
df -h
docker system df
docker system prune  # Clean up
```

---

## 🚢 Deployment Issues

### Issue: "Health check failed"

**Symptoms:**
```
❌ Health check failed on attempt 1/3
```

**Solutions:**

1. **Check application is running:**
```bash
curl http://localhost:8080/health
```

2. **Check health endpoint:**
```bash
# Ensure your app has /health endpoint
curl -v http://localhost:8080/health
```

3. **Increase timeout:**
```yaml
# deployment/configs/production.yaml
health_check:
  timeout: 60  # Increase from 30
  retries: 5   # Increase from 3
```

4. **Skip health checks (testing only):**
```bash
./deployment/deploy.sh staging --skip-tests
```

---

### Issue: "Permission denied"

**Symptoms:**
```
bash: ./deployment/deploy.sh: Permission denied
```

**Solutions:**

1. **Make script executable:**
```bash
chmod +x deployment/deploy.sh
```

2. **Run with bash:**
```bash
bash deployment/deploy.sh staging
```

---

### Issue: "Rollback failed"

**Symptoms:**
```
❌ Rollback failed: previous version not found
```

**Solutions:**

1. **Check backup exists:**
```bash
ls -la /var/backups/app/
```

2. **Manual rollback:**
```bash
# Find previous version
docker images | grep myapp

# Tag and deploy
docker tag myapp:v1.2.3 myapp:latest
docker-compose up -d
```

---

## 🐳 Docker Issues

### Issue: "Cannot connect to Docker daemon"

**Symptoms:**
```
Cannot connect to the Docker daemon. Is the docker daemon running?
```

**Solutions:**

1. **Start Docker:**

**Windows:**
```powershell
Start-Service docker
```

**Mac:**
```bash
open -a Docker
```

**Linux:**
```bash
sudo systemctl start docker
```

2. **Check Docker status:**
```bash
docker info
```

3. **Add user to docker group (Linux):**
```bash
sudo usermod -aG docker $USER
newgrp docker
```

---

### Issue: "Image pull failed"

**Symptoms:**
```
Error response from daemon: Get https://registry-1.docker.io/v2/: unauthorized
```

**Solutions:**

1. **Login to Docker Hub:**
```bash
docker login
```

2. **Pull image manually:**
```bash
docker pull prom/prometheus:latest
```

3. **Use different registry:**
```yaml
# docker-compose.yml
services:
  prometheus:
    image: quay.io/prometheus/prometheus:latest
```

---

### Issue: "Out of disk space"

**Symptoms:**
```
no space left on device
```

**Solutions:**

1. **Check disk usage:**
```bash
docker system df
```

2. **Clean up:**
```bash
# Remove unused images
docker image prune -a

# Remove unused volumes
docker volume prune

# Remove everything unused
docker system prune -a --volumes
```

3. **Configure log rotation:**
```yaml
# docker-compose.yml
services:
  prometheus:
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

---

## 🔧 Configuration Issues

### Issue: "Config file not found"

**Symptoms:**
```
WARNING - Config file not found: C:\Users\830 G8\.cost_tracker.yaml
```

**Solutions:**

1. **Create config from template:**
```bash
cp monitoring/config.yaml.template ~/.cost_tracker.yaml
```

2. **Specify config path:**
```bash
python monitoring/cost_tracker.py --config ./my-config.yaml
```

3. **Use environment variables:**
```bash
export COST_TRACKER_CONFIG=./config.yaml
```

---

### Issue: "Invalid YAML syntax"

**Symptoms:**
```
yaml.scanner.ScannerError: mapping values are not allowed here
```

**Solutions:**

1. **Validate YAML:**
```bash
python -c "import yaml; yaml.safe_load(open('.cost_tracker.yaml'))"
```

2. **Check indentation:**
```yaml
# ❌ Wrong
providers:
aws:
  enabled: true

# ✅ Correct
providers:
  aws:
    enabled: true
```

3. **Use online validator:**
- https://www.yamllint.com/

---

## 🆘 Getting Help

### Still stuck?

1. **Check logs:**
```bash
# Application logs
tail -f ~/.cost_tracker.log

# Docker logs
docker-compose logs -f
```

2. **Enable debug mode:**
```bash
python monitoring/cost_tracker.py --verbose
```

3. **Open GitHub issue:**
```
https://github.com/yourusername/production-tools/issues/new
```

**Include:**
- Error message (full traceback)
- OS and Python version
- Config file (remove secrets!)
- Steps to reproduce

---

## 📚 Additional Resources

- [Setup Guide](setup.md) - Initial setup
- [Usage Guide](usage.md) - How to use
- [Security Guide](security.md) - Security best practices
- [Monitoring Guide](monitoring.md) - Monitoring setup
- [Goose Development Log](goose-development.md) - How this was built

---

**Built with 🦆 goose *