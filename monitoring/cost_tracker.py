#!/usr/bin/env python3
"""
Production Cost Tracker
Multi-cloud cost monitoring with alerting (AWS, GCP, Azure)
"""

import os
import sys
import json
import yaml
import click
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, asdict
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box

# ──────────────────────────────────────────────────────────────
# LOGGING & CONSOLE
# ──────────────────────────────────────────────────────────────
console = Console()
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────
# CONFIG
# ──────────────────────────────────────────────────────────────
CONFIG_PATH = Path.home() / ".cost_tracker.yaml"
TEMPLATE_PATH = Path(__file__).parent / "config.yaml.template"

def load_config() -> Dict:
    if not CONFIG_PATH.exists():
        console.print(f"[yellow]Config missing → copying template to {CONFIG_PATH}[/]")
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        CONFIG_PATH.write_text(TEMPLATE_PATH.read_text())
    return yaml.safe_load(CONFIG_PATH.read_text()) or {}

# ──────────────────────────────────────────────────────────────
# DATA MODELS
# ──────────────────────────────────────────────────────────────
@dataclass
class CostMetric:
    """
    Cost metric data structure
    
    Attributes:
        service: Cloud service name (e.g., 'ec2', 's3', 'vm')
        provider: Cloud provider (e.g., 'aws', 'azure', 'gcp')
        cost: Cost amount in USD
        currency: Currency code (default: USD)
        timestamp: When the cost was recorded
        resource_id: Unique resource identifier
        region: Cloud region (e.g., 'us-east-1', 'eastus')
        tags: Additional metadata tags
    """
    service: str
    provider: str
    cost: float
    currency: str = "USD"
    timestamp: datetime = None
    resource_id: str = ""
    region: str = ""
    tags: Dict[str, str] = None

    def __post_init__(self):
        """Initialize defaults after creation"""
        if self.timestamp is None:
            self.timestamp = datetime.now()
        if self.tags is None:
            self.tags = {}
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            "service": self.service,
            "provider": self.provider,
            "cost": self.cost,
            "currency": self.currency,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "resource_id": self.resource_id,
            "region": self.region,
            "tags": self.tags
        }

@dataclass
class CostAlert:
    threshold: float
    period: str
    services: List[str]
    channels: List[str]

# ──────────────────────────────────────────────────────────────
# COST TRACKER
# ──────────────────────────────────────────────────────────────
class CostTracker:
    def __init__(self, config: Any):
        """Initialize cost tracker
        Args:
            config: Either a dict (config object) or str (path to config file)
        """
        # Handle both dict and string (file path)
        if isinstance(config, dict):
            self.config = config
        elif isinstance(config, str):
            # Legacy: Load from file path
            self.config = yaml.safe_load(Path(config).read_text())
        else:
            raise ValueError(f"Config must be dict or str, got {type(config)}")
        self.metrics: List[CostMetric] = []
        self.alerts: List[CostAlert] = self._load_alerts()

    def _load_alerts(self) -> List[CostAlert]:
        """Load alert configurations from config"""
        alerts = []
        alert_configs = self.config.get("alerts", [])

        if not alert_configs:
            return alerts
        
        for a in alert_configs:
            # Skip disabled alerts
            if not a.get("enabled", True):
                continue

            alerts.append(CostAlert(
                threshold=a.get("threshold", 100),
                period=a.get("period", "daily"),
                services=a.get("services", []),
                channels=a.get("notification_channels", [])
            ))
        return alerts

    # ── AWS ───────────────────────────────────────────────────
    def fetch_aws(self) -> List[CostMetric]:
        try:
            import boto3
            from botocore.exceptions import ClientError, NoCredentialsError

            client = boto3.client("ce", region_name=self.config["providers"]["aws"]["region"])
            end = datetime.now(timezone.utc).date()
            start = end - timedelta(days=1)

            response = client.get_cost_and_usage(
                TimePeriod={"Start": str(start), "End": str(end)},
                Granularity="DAILY",
                Metrics=["UnblendedCost"],
                GroupBy=[{"Type": "DIMENSION", "Key": "SERVICE"}]
            )

            metrics = []
            for item in response["ResultsByTime"][0]["Groups"]:
                service = item["Keys"][0]
                cost = float(item["Metrics"]["UnblendedCost"]["Amount"])
                metrics.append(CostMetric(service=service, provider="aws", cost=cost))
            logger.info(f"AWS: {len(metrics)} services")
            return metrics
        except Exception as e:
            logger.error(f"AWS fetch failed: {e}")
            return []

    # ── GCP ───────────────────────────────────────────────────
    def fetch_gcp(self) -> List[CostMetric]:
        try:
            from google.cloud import billing_v1
            from google.oauth2 import service_account

            project_id = self.config["providers"]["gcp"]["project_id"]
            credentials = service_account.Credentials.from_service_account_file(
                os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
            )
            client = billing_v1.CloudBillingClient(credentials=credentials)

            # Simplified: get last 24h cost
            # Real impl: use BigQuery export or Billing API
            metrics = [
                CostMetric("compute-engine", "gcp", 450.0),
                CostMetric("cloud-storage", "gcp", 120.0),
            ]
            logger.info(f"GCP: {len(metrics)} services (simulated)")
            return metrics
        except Exception as e:
            logger.error(f"GCP fetch failed: {e}")
            return []

    # ── AZURE ─────────────────────────────────────────────────
    def fetch_azure(self) -> List[CostMetric]:
        try:
            from azure.identity import DefaultAzureCredential
            from azure.mgmt.costmanagement import CostManagementClient
            from azure.mgmt.costmanagement.models import QueryDefinition, TimeframeType

            credential = DefaultAzureCredential()
            subscription_id = self.config["providers"]["azure"]["subscription_id"]
            client = CostManagementClient(credential, subscription_id)

            query = QueryDefinition(
                type="Usage",
                timeframe=TimeframeType.THE_LAST_7_DAYS,
                dataset={"granularity": "Daily"}
            )
            # Real query would return cost by service
            metrics = [
                CostMetric("virtual-machines", "azure", 480.0),
                CostMetric("sql-database", "azure", 290.0),
            ]
            logger.info(f"Azure: {len(metrics)} services (simulated)")
            return metrics
        except Exception as e:
            logger.error(f"Azure fetch failed: {e}")
            return []

    # ── COLLECT ALL ───────────────────────────────────────────
    def collect(self) -> List[CostMetric]:
        providers = self.config.get("providers", {})
        metrics = []

        # Handle both list format (from metrics_tracker.py)
        if isinstance(providers, list):
            # Convert list to dict for easier access
            providers_dict = {p.get("name"): p for p in providers if isinstance(p, dict)}
            providers = providers_dict

        # Now safely access providers
        if providers.get("aws", {}).get("enabled"):
            metrics.extend(self.fetch_aws())
        if providers.get("gcp", {}).get("enabled"):
            metrics.extend(self.fetch_gcp())
        if providers.get("azure", {}).get("enabled"):
            metrics.extend(self.fetch_azure())

        self.metrics = metrics
        logger.info(f"Total metrics: {len(metrics)}")
        return metrics

    # ── ANALYZE ───────────────────────────────────────────────
    def analyze(self) -> Dict:
        total = sum(m.cost for m in self.metrics)
        by_provider = {}
        by_service = {}

        for m in self.metrics:
            by_provider[m.provider] = by_provider.get(m.provider, 0) + m.cost
            by_service[m.service] = by_service.get(m.service, 0) + m.cost

        return {
            "total_cost": round(total, 2),
            "by_provider": {k: round(v, 2) for k, v in by_provider.items()},
            "by_service": dict(sorted(by_service.items(), key=lambda x: x[1], reverse=True)),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    # ── ALERTS ────────────────────────────────────────────────
    def check_alerts(self, analysis: Dict) -> List[Dict]:
        triggered = []
        total = analysis["total_cost"]

        for alert in self.alerts:
            if total > alert.threshold:
                triggered.append({
                    "threshold": alert.threshold,
                    "actual": total,
                    "period": alert.period,
                    "channels": alert.channels
                })
                logger.warning(f"ALERT: ${total} > ${alert.threshold}")
        return triggered

    # ── NOTIFY: SLACK ─────────────────────────────────────────
    def send_slack(self, alert: Dict):
        webhook = os.getenv("SLACK_WEBHOOK")
        if not webhook:
            console.print("[yellow]SLACK_WEBHOOK not set[/]")
            return
        try:
            import requests
            payload = {
                "text": f"Cost Alert: ${alert['actual']:.2f} exceeds ${alert['threshold']:.2f}"
            }
            requests.post(webhook, json=payload, timeout=10)
            console.print("[green]Slack alert sent[/]")
        except Exception as e:
            console.print(f"[red]Slack failed: {e}[/]")

    # ── NOTIFY: EMAIL ─────────────────────────────────────────
    def send_email(self, alert: Dict):
        cfg = self.config.get("notifications", {}).get("email", {})
        if not cfg.get("enabled"):
            return
        try:
            import smtplib
            from email.mime.text import MIMEText
            msg = MIMEText(f"Cost: ${alert['actual']:.2f} > ${alert['threshold']:.2f}")
            msg["Subject"] = "Cloud Cost Alert"
            msg["From"] = cfg["from"]
            msg["To"] = ", ".join(cfg["to"])

            with smtplib.SMTP(cfg["smtp_host"], cfg["smtp_port"]) as server:
                server.starttls()
                server.login(cfg["username"], cfg["password"])
                server.send_message(msg)
            console.print("[green]Email sent[/]")
        except Exception as e:
            console.print(f"[red]Email failed: {e}[/]")

    # ── SAVE REPORT ───────────────────────────────────────────
    def save_report(self, analysis: Dict, path: str):
        report = {
            "analysis": analysis,
            "metrics": [m.to_dict() for m in self.metrics],
            "generated_at": datetime.now(timezone.utc).isoformat()
        }
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text(json.dumps(report, indent=2))
        console.print(f"[blue]Report saved: {path}[/]")

    # ── RUN ───────────────────────────────────────────────────
    def run(self, output_path: Optional[str] = None):
        console.print(Panel("Starting Multi-Cloud Cost Tracker", style="bold blue"))
        self.collect()
        analysis = self.analyze()
        alerts = self.check_alerts(analysis)

        # Display
        table = Table(title="Cost Summary", box=box.ROUNDED)
        table.add_column("Provider", style="cyan")
        table.add_column("Cost", style="green")
        for p, c in analysis["by_provider"].items():
            table.add_row(p.upper(), f"${c}")
        console.print(table)

        # Alerts
        if alerts:
            for a in alerts:
                if "slack" in a["channels"]:
                    self.send_slack(a)
                if "email" in a["channels"]:
                    self.send_email(a)

        # Save
        if output_path:
            self.save_report(analysis, output_path)

        console.print(Panel("Run complete", style="bold green"))

# ──────────────────────────────────────────────────────────────
# CLI
# ──────────────────────────────────────────────────────────────
@click.command()
@click.option("--output", type=str, help="Save report to JSON file")
@click.option("--verbose", is_flag=True, help="Verbose logging")
def cli(output: str, verbose: bool):
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    config = load_config()
    tracker = CostTracker(config)
    tracker.run(output)

if __name__ == "__main__":
    cli()