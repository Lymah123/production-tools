import unittest
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from cost_tracker import CostTracker, CostMetric, CostAlert


class TestCostMetric(unittest.TestCase):
    def test_cost_metric_creation(self):
        metric = CostMetric("ec2", "aws", 150.50)
        self.assertEqual(metric.service, "ec2")
        self.assertEqual(metric.provider, "aws")
        self.assertEqual(metric.cost, 150.50)
        self.assertIsInstance(metric.timestamp, datetime)


class TestCostAlert(unittest.TestCase):
    def test_cost_alert_creation(self):
        alert = CostAlert(1000.0, "daily", ["ec2"], ["email"])
        self.assertEqual(alert.threshold, 1000.0)
        self.assertEqual(alert.period, "daily")
        self.assertEqual(alert.services, ["ec2"])
        self.assertEqual(alert.channels, ["email"])


class TestCostTracker(unittest.TestCase):
    def setUp(self):
        self.config = {
            "providers": {
                "aws": {"enabled": False, "region": "us-east-1"},
                "gcp": {"enabled": False, "project_id": "test-project"},
                "azure": {"enabled": False, "subscription_id": "test-sub"}
            },
            "alerts": [
                {
                    "threshold": 1000.0,
                    "period": "daily",
                    "services": ["ec2"],
                    "notification_channels": ["email"]
                }
            ]
        }
        self.tracker = CostTracker(self.config)

    def test_tracker_initialization(self):
        self.assertIsNotNone(self.tracker)
        self.assertEqual(len(self.tracker.alerts), 1)
        self.assertEqual(self.tracker.alerts[0].threshold, 1000.0)

    def test_load_alerts(self):
        alerts = self.tracker._load_alerts()
        self.assertEqual(len(alerts), 1)
        self.assertIsInstance(alerts[0], CostAlert)

    def test_fetch_aws_disabled(self):
        """Test that AWS fetch returns empty when disabled"""
        metrics = self.tracker.fetch_aws()
        self.assertEqual(metrics, [])

    def test_fetch_gcp_disabled(self):
        """Test that GCP fetch returns empty when disabled"""
        metrics = self.tracker.fetch_gcp()
        self.assertEqual(metrics, [])

    def test_fetch_azure_disabled(self):
        """Test that Azure fetch returns empty when disabled"""
        metrics = self.tracker.fetch_azure()
        self.assertEqual(metrics, [])

    def test_collect_all_disabled(self):
        """Test collect with all providers disabled"""
        metrics = self.tracker.collect()
        self.assertIsInstance(metrics, list)
        self.assertEqual(len(metrics), 0)

    @patch('boto3.client')
    def test_fetch_aws_error_handling(self, mock_client):
        """Test AWS fetch handles errors gracefully"""
        self.config["providers"]["aws"]["enabled"] = True
        tracker = CostTracker(self.config)
        
        # Mock boto3.client to raise an exception
        mock_client.side_effect = Exception("Connection error")
        metrics = tracker.fetch_aws()
        
        self.assertEqual(metrics, [])

    @patch('boto3.client')
    def test_fetch_aws_with_data(self, mock_client):
        """Test AWS fetch with mock data"""
        self.config["providers"]["aws"]["enabled"] = True
        tracker = CostTracker(self.config)
        
        # Mock successful AWS response
        mock_ce = MagicMock()
        mock_ce.get_cost_and_usage.return_value = {
            "ResultsByTime": [{
                "Groups": [
                    {
                        "Keys": ["Amazon EC2"],
                        "Metrics": {"UnblendedCost": {"Amount": "150.50"}}
                    }
                ]
            }]
        }
        mock_client.return_value = mock_ce
        
        metrics = tracker.fetch_aws()
        
        self.assertIsInstance(metrics, list)
        self.assertGreater(len(metrics), 0)

    def test_analyze_empty_metrics(self):
        """Test analyze with no metrics"""
        self.tracker.metrics = []
        result = self.tracker.analyze()
        
        self.assertIsInstance(result, dict)
        self.assertIn("total_cost", result)
        self.assertEqual(result["total_cost"], 0)


class TestCostTrackerIntegration(unittest.TestCase):
    """Integration tests for full workflow"""
    
    def test_full_workflow_no_providers(self):
        """Test complete workflow with no providers enabled"""
        config = {
            "providers": {
                "aws": {"enabled": False},
                "gcp": {"enabled": False},
                "azure": {"enabled": False}
            },
            "alerts": []
        }
        
        tracker = CostTracker(config)
        metrics = tracker.collect()
        
        self.assertIsInstance(metrics, list)
        self.assertEqual(len(metrics), 0)


if __name__ == '__main__':
    unittest.main(verbosity=2)