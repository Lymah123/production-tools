#!/usr/bin/env python3
"""
Real-time metrics testing - simulates cloud costs
"""

import time
import random
import logging
from datetime import datetime
from dataclasses import dataclass
from prometheus_client import start_http_server, Gauge

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Simple dataclass (in case import fails)
@dataclass
class CostMetric:
    service: str
    provider: str
    cost: float
    region: str = 'us-east-1'

# Prometheus metrics
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

def simulate_costs():
    """Simulate random cloud costs for testing"""
    providers_services = {
        'aws': ['ec2', 's3', 'rds', 'lambda', 'cloudfront'],
        'azure': ['vm', 'storage', 'sql', 'functions', 'cdn'],
        'gcp': ['compute', 'storage', 'bigquery', 'cloud-run', 'gke']
    }
    
    metrics = []
    for provider, services in providers_services.items():
        for service in services:
            cost = round(random.uniform(10, 500), 2)
            metrics.append(CostMetric(
                service=service,
                provider=provider,
                cost=cost,
                region='us-east-1'
            ))
    
    logger.info(f"Generated {len(metrics)} cost metrics")
    return metrics

def update_metrics(metrics):
    """Update Prometheus metrics"""
    provider_totals = {'aws': 0, 'azure': 0, 'gcp': 0}
    
    # Update per-service costs
    for metric in metrics:
        cost_gauge.labels(
            provider=metric.provider,
            service=metric.service,
            region=metric.region
        ).set(metric.cost)
        
        provider_totals[metric.provider] += metric.cost
    
    # Update daily and monthly projections
    for provider, total in provider_totals.items():
        daily_cost_gauge.labels(provider=provider).set(total)
        monthly_projection_gauge.labels(provider=provider).set(total * 30)
    
    logger.info(f"Updated metrics: AWS=${provider_totals['aws']:.2f}, Azure=${provider_totals['azure']:.2f}, GCP=${provider_totals['gcp']:.2f}")
    return provider_totals

def print_summary(iteration, provider_totals):
    """Print cost summary"""
    print(f"\n{'='*70}")
    print(f"📊 Iteration {iteration} - {datetime.now().strftime('%H:%M:%S')}")
    print(f"{'='*70}")
    
    print("\n💰 Current Costs:")
    print(f"{'Provider':<10} {'Daily':<15} {'Monthly (est.)':<20}")
    print("-" * 70)
    
    for provider in ['aws', 'azure', 'gcp']:
        total = provider_totals[provider]
        monthly = total * 30
        print(f"{provider.upper():<10} ${total:>12.2f}  ${monthly:>17.2f}")
    
    total_daily = sum(provider_totals.values())
    total_monthly = total_daily * 30
    
    print("-" * 70)
    print(f"{'TOTAL':<10} ${total_daily:>12.2f}  ${total_monthly:>17.2f}")
    print()

if __name__ == '__main__':
    import click
    
    @click.command()
    @click.option('--port', default=8000, help='HTTP server port')
    @click.option('--interval', default=30, help='Update interval (seconds)')
    def main(port, interval):
        """Test metrics exporter with simulated cloud costs"""
        
        print("\n" + "="*70)
        print("🧪 CLOUD COST METRICS SIMULATOR")
        print("="*70)
        print(f"\n📡 Starting metrics server on port {port}")
        print(f"⏱️  Update interval: {interval} seconds")
        
        # Start HTTP server
        start_http_server(port)
        logger.info(f"Metrics server started on port {port}")
        
        print(f"\n✅ Metrics available at http://localhost:{port}/metrics")
        print(f"📈 View in Prometheus: http://localhost:9090/graph")
        print(f"📊 View in Grafana: http://localhost:3000")
        print("\n💡 Queries to try in Prometheus:")
        print("   - cloud_cost_daily")
        print("   - sum(cloud_cost_daily)")
        print("   - sum by (provider) (cloud_cost_daily)")
        print("   - topk(5, cloud_cost_total)")
        print("\n⌨️  Press Ctrl+C to stop\n")
        
        iteration = 0
        
        try:
            while True:
                iteration += 1
                
                # Generate and update metrics
                metrics = simulate_costs()
                provider_totals = update_metrics(metrics)
                
                # Print summary
                print_summary(iteration, provider_totals)
                
                # Alert check
                total = sum(provider_totals.values())
                if total > 1000:
                    print(f"⚠️  WARNING: Daily cost ${total:.2f} exceeds $1000 threshold!")
                
                print(f"⏳ Next update in {interval} seconds...")
                print(f"   Metrics endpoint: http://localhost:{port}/metrics")
                
                time.sleep(interval)
                
        except KeyboardInterrupt:
            print("\n\n👋 Shutting down gracefully...")
            logger.info("Metrics server stopped")
    
    main()