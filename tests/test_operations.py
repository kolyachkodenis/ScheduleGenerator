from __future__ import annotations

import json
import logging
import unittest
from pathlib import Path

from schedule_generator.operations import AppConfig, JsonFormatter, OperationalMetrics


class AppConfigTests(unittest.TestCase):
    def test_environment_configuration_is_parsed(self) -> None:
        config = AppConfig.from_env(
            {
                "SG_ENVIRONMENT": "test",
                "SG_DATABASE": "tmp/test.db",
                "SG_HOST": "0.0.0.0",
                "SG_PORT": "9000",
                "SG_SECURE_COOKIE": "yes",
                "SG_LOG_LEVEL": "warning",
                "SG_LOG_FORMAT": "json",
            }
        )
        self.assertEqual(config.database, Path("tmp/test.db"))
        self.assertEqual(config.port, 9000)
        self.assertTrue(config.secure_cookie)
        self.assertEqual(config.log_level, "WARNING")

    def test_production_requires_cookie_and_metrics_protection(self) -> None:
        with self.assertRaisesRegex(ValueError, "SG_SECURE_COOKIE"):
            AppConfig.from_env({"SG_ENVIRONMENT": "production"})
        with self.assertRaisesRegex(ValueError, "SG_METRICS_TOKEN"):
            AppConfig.from_env(
                {"SG_ENVIRONMENT": "production", "SG_SECURE_COOKIE": "true"}
            )


class ObservabilityTests(unittest.TestCase):
    def test_metrics_are_aggregated_on_normalized_routes(self) -> None:
        metrics = OperationalMetrics()
        metrics.observe_http("GET", "/api/jobs/abc123", 200, 0.25)
        metrics.observe_http("GET", "/api/jobs/def456", 200, 0.75)
        metrics.observe_job("SUCCEEDED", 2.5)
        rendered = metrics.render()
        self.assertIn('route="/api/jobs/{id}"', rendered)
        self.assertIn('status="200"} 2', rendered)
        self.assertIn('status="SUCCEEDED"} 1', rendered)

    def test_json_formatter_preserves_operational_fields(self) -> None:
        record = logging.LogRecord(
            "schedule_generator.web",
            logging.INFO,
            __file__,
            1,
            "request completed",
            (),
            None,
        )
        record.event = "http.request"
        record.status = 200
        payload = json.loads(JsonFormatter().format(record))
        self.assertEqual(payload["event"], "http.request")
        self.assertEqual(payload["status"], 200)


if __name__ == "__main__":
    unittest.main()
