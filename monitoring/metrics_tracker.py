#!/usr/bin/env python3
"""
Prometheus Metrics Exporter
Exports cost monitoring metrics to Prometheus
"""

import time
import logging
from typing import Dict, List
from prometheus_client import start_http_server, Gauge, Counter, Histogram
from prometheus_client.core import GaugeMetricFamily, REGISTRY
import yaml
from pathlib import Path

from cost_tracker import CostTracker, CostMetric

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────
# PROMETHEUS METRICS
# ──────────────────────────────────────────────────────────────
# Gauges (current values)
cost_gauge = Gauge(
    'cloud_cost_total',
    'Total cloud cost by provider and service',
    ['provider', 'service', 'region']
)

daily_cost_gauge = Gauge(
    'cloud_cost_daily',
    'Daily cloud cost by provider',
    ['provider']
)

monthly_projection_gauge = Gauge(
    'cloud_cost_monthly_projection',
    'Projected monthly cost by provider',
    ['provider']
)

# Counters (cumulative)
fetch_counter = Counter(
    'cost_fetch_total',
    'Total number of cost fetches',
    ['provider', 'status']
)

alert_counter = Counter(
    'cost_alerts_total',
    'Total number of cost alerts triggered',
    ['alert_type', 'provider']
)

# Histogram (latency tracking)
fetch_duration = Histogram(
    'cost_fetch_duration_seconds',
    'Time spent fetching costs',
    ['provider']
)


# ──────────────────────────────────────────────────────────────
# METRICS COLLECTOR
# ──────────────────────────────────────────────────────────────
class CostMetricsCollector:
    """Collects and exports cost metrics to Prometheus"""
    
    def __init__(self, config_path: str = None):
        self.config_path = config_path or str(Path.home() / ".cost_tracker.yaml")

        # Load config if file exists, otherwise use empty config
        if Path(self.config_path).exists():
            logger.info(f"Loading config from: {self.config_path}")
            with open(self.config_path) as f:
                config = yaml.safe_load(f)
            self.tracker = CostTracker(config)
        else:
            logger.warning(f"Config file not found: {self.config_path}")
            logger.info("Using default configuration")
            # Create minimal config
            default_config = {
                "providers": {
                    "openai": {"enabled": False},
                    "aws": {"enabled": False, "region": "us-east-1"},
                    "azure": {"enabled": False, "subscription_id": ""},
                    "gcp": {"enabled": False, "project_id": ""}
                },
                "alerts": [
                    {
                        "name": "daily_cost_high",
                        "type": "threshold",
                        "threshold": 100,
                        "period": "daily",
                        "enabled": False
                    }
                ],
                "slack": {
                    "enabled": False,
                    "webhook_url": None,
                    "channel": "#cost-alerts"
                }
            }
            self.tracker = CostTracker(default_config)
    
    def collect_metrics(self):
        """Collect current cost metrics"""
        logger.info("Collecting cost metrics...")
        
        try:
            # Fetch metrics from all providers
            with fetch_duration.labels(provider='all').time():
                metrics = self.tracker.collect()
            
            fetch_counter.labels(provider='all', status='success').inc()
            
            # Update Prometheus metrics
            self._update_cost_metrics(metrics)
            
            # Check for alerts
            analysis = self.tracker.analyze()
            triggered_alerts = self.tracker.check_alerts(analysis)
            self._update_alert_metrics(triggered_alerts)
            
            logger.info(f"Collected {len(metrics)} metrics")
            
        except Exception as e:
            logger.error(f"Failed to collect metrics: {e}", exc_info=True)
            fetch_counter.labels(provider='all', status='error').inc()
    
    def _update_cost_metrics(self, metrics: List[CostMetric]):
        """Update Prometheus cost gauges"""
        # Clear old metrics
        cost_gauge.clear()
        
        provider_totals = {}
        
        for metric in metrics:
            # Per-service cost
            cost_gauge.labels(
                provider=metric.provider,
                service=metric.service,
                region=metric.region or 'unknown'
            ).set(metric.cost)
            
            # Aggregate by provider
            if metric.provider not in provider_totals:
                provider_totals[metric.provider] = 0
            provider_totals[metric.provider] += metric.cost
        
        # Update daily costs
        for provider, total in provider_totals.items():
            daily_cost_gauge.labels(provider=provider).set(total)
            
            # Project monthly cost (daily * 30)
            monthly_projection = total * 30
            monthly_projection_gauge.labels(provider=provider).set(monthly_projection)
    
    def _update_alert_metrics(self, alerts: List):
        """Update alert counters"""
        for alert in alerts:
            alert_counter.labels(
                alert_type=alert.get('type', 'threshold'),
                provider=alert.get('provider', 'unknown')
            ).inc()
    
    def run(self, port: int = 8000, interval: int = 300):
        """Run metrics exporter server"""
        logger.info(f"Starting Prometheus exporter on port {port}")
        logger.info(f"Metrics will be collected every {interval} seconds")
        
        # Start HTTP server
        start_http_server(port)
        
        logger.info(f"Metrics available at http://localhost:{port}/metrics")
        
        # Collect metrics periodically
        while True:
            self.collect_metrics()
            time.sleep(interval)


# ──────────────────────────────────────────────────────────────
# CLI
# ──────────────────────────────────────────────────────────────
if __name__ == '__main__':
    import click
    
    @click.command()
    @click.option('--port', default=8000, help='HTTP server port')
    @click.option('--interval', default=300, help='Collection interval (seconds)')
    @click.option('--config', help='Path to cost tracker config')
    def main(port, interval, config):
        """Start Prometheus metrics exporter for cloud costs"""
        collector = CostMetricsCollector(config_path=config)
        collector.run(port=port, interval=interval)
    
    main()