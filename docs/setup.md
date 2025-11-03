# Production Tools Suite - Setup Guide

Complete setup instructions for the production tools suite.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Installation](#installation)
3. [Configuration](#configuration)
4. [Verification](#verification)
5. [Platform-Specific Setup](#platform-specific-setup)
6. [Troubleshooting](#troubleshooting)

## Prerequisites

### System Requirements

- **Operating System**: Linux, macOS, or Windows with WSL2
- **Python**: 3.8 or higher
- **Bash**: 4.0 or higher
- **Git**: 2.20 or higher
- **Disk Space**: Minimum 500MB free

### Required Tools

```bash
# Check if you have required tools
python3 --version
bash --version
git --version
curl --version
```

### Optional Tools

- **Docker**: For containerized deployments
- **jq**: For JSON processing
- **AWS CLI**: For AWS integrations
- **gcloud CLI**: For GCP integrations
- **Azure CLI**: For Azure integrations

## Installation

### 1. Clone Repository

```bash
git clone <repository-url> production-tools
cd production-tools
```

### 2. Verify Structure

```bash
tree -L 2
# Should show complete directory structure
```

### 3. Install Python Dependencies

```bash
# Create virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r monitoring/requirements.txt
```

### 4. Make Scripts Executable

```bash
chmod +x deployment/deploy.sh
chmod +x monitoring/cost_tracker.py
chmod +x validation/config_validator.py
chmod +x validation/version_checker.py
chmod +x env-manager/env_template.py
```

### 5. Run System Check

```bash
python validation/version_checker.py --check-all
```

## Configuration

### 1. Environment Setup

Initialize environment configuration:

```bash
python env-manager/env_template.py --init
```

This creates:
- `.env.template` - Template file (commit to version control)
- `.env` - Your local configuration (DO NOT commit)
- `.gitignore` - Updated to exclude .env files

### 2. Edit Environment File

```bash
# Copy template and edit
cp .env.template .env
nano .env  # or vim, code, etc.
```

Fill in required values:

```bash
# Required
APP_ENV=production
APP_NAME=your-app
DATABASE_URL=postgresql://user:pass@localhost/db
SECRET_KEY=your-secret-key-here

# Optional but recommended
AWS_REGION=us-east-1
LOG_LEVEL=INFO
```

### 3. Validate Configuration

```bash
python env-manager/env_template.py --validate .env
```

### 4. Configure Deployment

Edit deployment configurations for your platform:

```bash
# Linux
nano deployment/config/linux.conf

# macOS
nano deployment/config/macos.conf

# Windows
nano deployment/config/windows.conf
```

### 5. Configure Cost Monitoring

```bash
# Copy template
cp monitoring/config.yaml.template monitoring/config.yaml

# Edit configuration
nano monitoring/config.yaml
```

Update with your cloud provider credentials and alert thresholds.

## Verification

### 1. Validate All Configurations

```bash
python validation/config_validator.py --config deployment/config/
python validation/config_validator.py --config monitoring/
```

### 2. Test Deployment Script (Dry Run)

```bash
./deployment/deploy.sh \
  --env staging \
  --platform linux \
  --service test-app \
  --dry-run
```

### 3. Test Cost Tracker

```bash
python monitoring/cost_tracker.py \
  --config monitoring/config.yaml \
  --output /tmp/test-report.json
```

### 4. Run Complete Test Suite

```bash
pytest --cov=.
```

## Platform-Specific Setup

### Linux (Ubuntu/Debian)

```bash
# Install system dependencies
sudo apt-get update
sudo apt-get install -y \
  python3 \
  python3-pip \
  python3-venv \
  git \
  curl \
  jq \
  shellcheck

# Install optional tools
sudo apt-get install -y docker.io

# Add user to docker group
sudo usermod -aG docker $USER
```

### Linux (CentOS/RHEL)

```bash
# Install system dependencies
sudo yum install -y \
  python3 \
  python3-pip \
  git \
  curl \
  jq

# Install Docker
sudo yum install -y docker
sudo systemctl start docker
sudo systemctl enable docker
```

### macOS

```bash
# Install Homebrew if not already installed
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install dependencies
brew install python@3.9 git curl jq shellcheck

# Install Docker Desktop
brew install --cask docker
```

### Windows (WSL2)

```powershell
# Enable WSL2
wsl --install

# In WSL2 terminal, follow Linux setup instructions
```

## Cloud Provider Setup

### AWS Configuration

```bash
# Install AWS CLI
pip install awscli

# Configure credentials
aws configure

# Test access
aws sts get-caller-identity
```

### Google Cloud Configuration

```bash
# Install gcloud CLI
# Follow: https://cloud.google.com/sdk/docs/install

# Authenticate
gcloud auth login

# Set project
gcloud config set project YOUR_PROJECT_ID
```

### Azure Configuration

```bash
# Install Azure CLI
# Follow: https://docs.microsoft.com/cli/azure/install-azure-cli

# Login
az login

# Set subscription
az account set --subscription YOUR_SUBSCRIPTION_ID
```

## Security Setup

### 1. Secret Management

**Using AWS Secrets Manager:**

```bash
# Store secrets
aws secretsmanager create-secret \
  --name production/app/database-url \
  --secret-string "postgresql://..."

# Retrieve in deployment
DATABASE_URL=$(aws secretsmanager get-secret-value \
  --secret-id production/app/database-url \
  --query SecretString \
  --output text)
```

**Using HashiCorp Vault:**

```bash
# Store secret
vault kv put secret/production/app \
  database_url="postgresql://..."

# Retrieve in deployment
vault kv get -field=database_url secret/production/app
```

### 2. SSH Key Setup

```bash
# Generate deployment key
ssh-keygen -t ed25519 -C "deployment@example.com" -f ~/.ssh/deploy_key

# Add to ssh-agent
eval "$(ssh-agent -s)"
ssh-add ~/.ssh/deploy_key

# Copy public key to servers
ssh-copy-id -i ~/.ssh/deploy_key.pub user@server
```

### 3. GPG Setup (for encrypted configs)

```bash
# Generate GPG key
gpg --gen-key

# Encrypt sensitive file
gpg --encrypt --recipient your@email.com config.yaml

# Decrypt
gpg --decrypt config.yaml.gpg > config.yaml
```

## CI/CD Integration

### GitHub Actions

The included `.github/workflows/ci.yml` is pre-configured. To enable:

1. Push repository to GitHub
2. Enable Actions in repository settings
3. Add required secrets:

```bash
# In GitHub: Settings > Secrets > Actions
AWS_ACCESS_KEY_ID
AWS_SECRET_ACCESS_KEY
SLACK_WEBHOOK_URL
SMTP_PASSWORD
```

### GitLab CI

Create `.gitlab-ci.yml`:

```yaml
include:
  - template: Python.gitlab-ci.yml

stages:
  - validate
  - test
  - deploy

validate:
  stage: validate
  script:
    - python validation/config_validator.py --config deployment/config/
```

### Jenkins

```groovy
pipeline {
    agent any
    stages {
        stage('Validate') {
            steps {
                sh 'python validation/config_validator.py --config deployment/config/'
            }
        }
        stage('Deploy') {
            steps {
                sh './deployment/deploy.sh --env production --platform linux'
            }
        }
    }
}
```

## Monitoring Setup

### 1. Prometheus Integration

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'cost-tracker'
    static_configs:
      - targets: ['localhost:9090']
```

### 2. Grafana Dashboard

Import the included Grafana dashboard:

```bash
# Dashboard is in monitoring/grafana/dashboard.json
```

### 3. Alert Manager

Configure alert routing in `monitoring/alertmanager.yml`

## Backup and Recovery

### 1. Configure Automated Backups

```bash
# Add to crontab
crontab -e

# Daily backups at 2 AM
0 2 * * * /path/to/production-tools/deployment/deploy.sh --backup
```

### 2. Test Recovery

```bash
# Test rollback
./deployment/deploy.sh \
  --env staging \
  --platform linux \
  --rollback v1.0.0
```

## Troubleshooting

### Common Issues

**Issue: Permission denied on deployment**

```bash
# Fix: Ensure correct file permissions
chmod +x deployment/deploy.sh
chmod 600 ~/.ssh/deploy_key
```

**Issue: Python module not found**

```bash
# Fix: Activate virtual environment
source venv/bin/activate
pip install -r monitoring/requirements.txt
```

**Issue: Configuration validation fails**

```bash
# Fix: Check syntax
python validation/config_validator.py --config path/to/config --verbose
```

**Issue: Cost tracker can't connect to AWS**

```bash
# Fix: Verify AWS credentials
aws sts get-caller-identity

# Check IAM permissions
aws iam get-user
```

### Getting Help

1. Check logs: `tail -f deployment/deploy.log`
2. Run with verbose: `--verbose` or `--debug`
3. Validate system: `python validation/version_checker.py --check-all`
4. Review documentation in `docs/`
5. Open GitHub issue with logs

## Next Steps

After setup is complete:

1. ✅ Read the [Usage Guide](usage.md)
2. ✅ Customize configurations for your environment
3. ✅ Set up monitoring dashboards
4. ✅ Configure alert notifications
5. ✅ Schedule automated backups
6. ✅ Document team-specific procedures

## Additional Resources

- [Usage Guide](usage.md)
- [Development Log](development-log.md)
- [API Documentation](api.md)
- [Security Best Practices](security.md)