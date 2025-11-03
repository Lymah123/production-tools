# Security Guide

Best practices and security guidelines for production tools.

---

## 🔒 Table of Contents

1. [Secrets Management](#secrets-management)
2. [Access Control](#access-control)
3. [Encryption](#encryption)
4. [Audit Logging](#audit-logging)
5. [Network Security](#network-security)
6. [Best Practices](#best-practices)

---

## 🔐 Secrets Management

### Never Commit Secrets

**❌ NEVER do this:**
```yaml
# config.yaml
api_key: sk-proj-abc123  # NEVER hardcode secrets!
password: mypassword123   # NEVER!
```

**✅ DO this instead:**
```yaml
# config.yaml
api_key: ${API_KEY}      # Use environment variables
password: ${DB_PASSWORD}
```

### Use Environment Variables

```bash
# .env (add to .gitignore!)
export API_KEY="sk-proj-abc123"
export DB_PASSWORD="secure-password"
export SLACK_WEBHOOK="https://hooks.slack.com/..."
```

**Load in Python:**
```python
import os
from pathlib import Path

# Load from .env file
from dotenv import load_dotenv
load_dotenv()

api_key = os.getenv('API_KEY')
db_password = os.getenv('DB_PASSWORD')
```

### Use Secrets Manager

**AWS Secrets Manager:**
```bash
# Store secret
python security/secrets_manager.py put prod/api-key \
  --key token --value "sk-proj-abc123"

# Retrieve in code
from security.secrets_manager import SecretsManager

sm = SecretsManager(backend='aws')
secret = sm.get_secret('prod/api-key')
api_key = secret['token']
```

**HashiCorp Vault:**
```bash
# Store secret
vault kv put secret/prod/api-key token=sk-proj-abc123

# Retrieve in code
sm = SecretsManager(backend='vault')
secret = sm.get_secret('prod/api-key')
```

---

## 🛡️ Access Control

### IAM Roles (AWS)

**Principle of Least Privilege:**

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue",
        "secretsmanager:DescribeSecret"
      ],
      "Resource": "arn:aws:secretsmanager:us-east-1:*:secret:prod/*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "ce:GetCostAndUsage"
      ],
      "Resource": "*"
    }
  ]
}
```

### Service Accounts

**Create dedicated service accounts:**

```bash
# AWS
aws iam create-user --user-name production-tools-bot

# Azure
az ad sp create-for-rbac --name production-tools \
  --role Reader --scopes /subscriptions/{subscription-id}

# GCP
gcloud iam service-accounts create production-tools \
  --display-name "Production Tools Bot"
```

### API Key Rotation

**Automatic rotation policy:**

```yaml
# ~/.secrets_manager.yaml
rotation:
  enabled: true
  schedule: "0 0 1 * *"  # Monthly on 1st
  secrets:
    - prod/api-key
    - prod/db-password
  
  notification:
    slack:
      channel: "#security"
    email:
      to: ["security@company.com"]
```

**Manual rotation:**
```bash
python security/secrets_manager.py rotate prod/api-key \
  --new-value "sk-proj-new123"
```

---

## 🔐 Encryption

### Encryption at Rest

**AWS Secrets Manager:**
- Automatically encrypted with AWS KMS
- Use customer-managed KMS keys for additional control

```yaml
# ~/.secrets_manager.yaml
backends:
  aws:
    region: us-east-1
    kms_key_id: arn:aws:kms:us-east-1:123456789:key/abc-123
```

**Vault:**
- Uses Shamir's Secret Sharing for unsealing
- Transit secrets engine for encryption-as-a-service

```bash
# Enable transit engine
vault secrets enable transit

# Encrypt data
vault write transit/encrypt/my-key plaintext=$(base64 <<< "secret data")
```

### Encryption in Transit

**Always use HTTPS/TLS:**

```python
# ✅ Good
response = requests.get('https://api.example.com', verify=True)

# ❌ Bad
response = requests.get('http://api.example.com')  # Unencrypted!
response = requests.get('https://api.example.com', verify=False)  # Insecure!
```

**Monitoring Stack TLS:**

```yaml
# docker-compose.yml
services:
  prometheus:
    environment:
      - '--web.config.file=/etc/prometheus/web-config.yml'
    volumes:
      - ./certs:/etc/prometheus/certs:ro
```

---

## 📝 Audit Logging

### Enable Audit Logs

**Secrets Manager:**
```python
import logging

logger = logging.getLogger('secrets_audit')
logger.setLevel(logging.INFO)

# Log all secret access
handler = logging.FileHandler('/var/log/secrets-audit.log')
handler.setFormatter(logging.Formatter(
    '%(asctime)s - %(user)s - %(action)s - %(secret)s - %(status)s'
))
logger.addHandler(handler)
```

**Cost Tracker:**
```python
# monitoring/cost_tracker.py
logger.info(f"User {os.getenv('USER')} fetched costs for {provider}")
```

### Monitor Access

**CloudWatch Logs (AWS):**
```bash
aws logs create-log-group --log-group-name /production-tools/secrets

aws logs put-subscription-filter \
  --log-group-name /production-tools/secrets \
  --filter-name alerts \
  --filter-pattern "ERROR" \
  --destination-arn arn:aws:sns:us-east-1:123456789:alerts
```

**Prometheus Alerting:**
```yaml
# prometheus/alerts.yml
groups:
  - name: security
    rules:
      - alert: UnauthorizedSecretAccess
        expr: rate(secret_access_denied_total[5m]) > 0
        labels:
          severity: critical
        annotations:
          summary: "Unauthorized secret access detected"
```

---

## 🌐 Network Security

### Firewall Rules

**Only expose necessary ports:**

```bash
# Allow only local access to metrics
sudo ufw allow from 127.0.0.1 to any port 8000

# Allow Prometheus from specific IP
sudo ufw allow from 10.0.1.0/24 to any port 9090

# Deny all other incoming
sudo ufw default deny incoming
```

### Docker Security

```yaml
# docker-compose.yml
services:
  prometheus:
    # Don't expose to public
    ports:
      - "127.0.0.1:9090:9090"  # Localhost only
    
    # Run as non-root
    user: "65534:65534"
    
    # Read-only root filesystem
    read_only: true
    
    # Drop all capabilities
    cap_drop:
      - ALL
```

### VPN/Bastion Access

**Require VPN for sensitive operations:**

```bash
# Check VPN connection before deployment
if ! ping -c 1 internal.vpn.company.com &> /dev/null; then
    echo "❌ VPN required for production deployment"
    exit 1
fi
```

---

## ✅ Best Practices Checklist

### Development

- [ ] Never commit secrets to Git
- [ ] Use `.gitignore` for sensitive files
- [ ] Use environment variables or secrets manager
- [ ] Enable pre-commit hooks to scan for secrets
- [ ] Use `git-secrets` or `truffleHog`

```bash
# Install git-secrets
git secrets --install
git secrets --register-aws
```

### Production

- [ ] Use separate credentials for dev/staging/prod
- [ ] Enable MFA on all admin accounts
- [ ] Rotate secrets regularly (monthly minimum)
- [ ] Monitor access logs
- [ ] Set up alerts for unauthorized access
- [ ] Use IAM roles instead of access keys when possible
- [ ] Enable CloudTrail/audit logs
- [ ] Encrypt all data at rest and in transit

### Monitoring

- [ ] Alert on failed authentication attempts
- [ ] Monitor secret access patterns
- [ ] Track API key usage
- [ ] Set up anomaly detection
- [ ] Review logs regularly

```promql
# Prometheus alert for suspicious activity
rate(secret_access_total[5m]) > 100
```

---

## 🚨 Incident Response

### If Secrets Are Compromised

**Immediate actions:**

1. **Rotate compromised secrets immediately**
   ```bash
   python security/secrets_manager.py rotate prod/api-key
   ```

2. **Revoke old credentials**
   ```bash
   # AWS
   aws iam delete-access-key --access-key-id AKIA...
   
   # Vault
   vault token revoke <token-id>
   ```

3. **Audit access logs**
   ```bash
   # Check who accessed the secret
   aws secretsmanager list-secret-version-ids \
     --secret-id prod/api-key
   ```

4. **Notify security team**
   ```bash
   python monitoring/cost_tracker.py \
     --alert "Security incident: credentials rotated"
   ```

5. **Review and patch vulnerability**

---

## 📚 Additional Resources

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [AWS Security Best Practices](https://aws.amazon.com/security/best-practices/)
- [HashiCorp Vault Docs](https://www.vaultproject.io/docs)
- [CIS Benchmarks](https://www.cisecurity.org/cis-benchmarks/)

---

## 🆘 Security Contacts

- **Security Team**: security@company.com
- **Incident Response**: incidents@company.com
- **On-Call**: +1-555-SECURITY

---

**Remember: Security is everyone's responsibility!** 