#!/usr/bin/env bash
set -euo pipefail

echo "════════════════════════════════════════════════════════════"
echo "Setting up Monitoring Stack (Prometheus + Grafana)"
echo "════════════════════════════════════════════════════════════"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker not found. Please install Docker first.${NC}"
    exit 1
fi

echo -e "${GREEN}✓${NC} Docker found"

# Check if docker-compose exists
if ! docker compose version &> /dev/null && ! docker-compose --version &> /dev/null; then
    echo -e "${RED}❌ Docker Compose not found.${NC}"
    exit 1
fi

echo -e "${GREEN}✓${NC} Docker Compose found"

# Create directories if they don't exist
mkdir -p prometheus grafana

# Check if prometheus.yml exists
if [[ ! -f "prometheus/prometheus.yml" ]]; then
    echo -e "${YELLOW}⚠${NC} Creating prometheus.yml..."
    cat > prometheus/prometheus.yml << 'EOF'
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'cost-monitoring'
    static_configs:
      - targets: ['host.docker.internal:8000']
        labels:
          service: 'cloud-costs'
          environment: 'production'
EOF
    echo -e "${GREEN}✓${NC} prometheus.yml created"
fi

# Start containers
echo ""
echo "Starting Prometheus and Grafana..."
if command -v docker-compose &> /dev/null; then
    docker-compose up -d
else
    docker compose up -d
fi

# Wait for services to be ready
echo ""
echo "Waiting for services to start..."
sleep 5

# Check if services are running
if docker ps | grep -q prometheus && docker ps | grep -q grafana; then
    echo ""
    echo -e "${GREEN}✅ Monitoring stack started successfully!${NC}"
    echo ""
    echo "════════════════════════════════════════════════════════════"
    echo "📊 Access Points:"
    echo "════════════════════════════════════════════════════════════"
    echo "   Prometheus:  http://localhost:9090"
    echo "   Grafana:     http://localhost:3000"
    echo "                (default login: admin/admin)"
    echo ""
    echo "════════════════════════════════════════════════════════════"
    echo "🚀 Next Steps:"
    echo "════════════════════════════════════════════════════════════"
    echo "1. Start the metrics exporter:"
    echo "   cd .."
    echo "   python monitoring/metrics_tracker.py --port 8000 --interval 60"
    echo ""
    echo "2. Import Grafana dashboard:"
    echo "   - Open http://localhost:3000"
    echo "   - Login with admin/admin"
    echo "   - Go to Dashboards > Import"
    echo "   - Upload: monitoring/grafana/dashboard.json"
    echo ""
    echo "3. View metrics in Prometheus:"
    echo "   - Open http://localhost:9090"
    echo "   - Go to Graph and search: cloud_cost_daily"
    echo ""
    echo "════════════════════════════════════════════════════════════"
else
    echo -e "${RED} Failed to start services${NC}"
    echo "Check logs with: docker-compose logs"
    exit 1
fi