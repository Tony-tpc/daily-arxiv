"""Regression tests for source-specific scheduling and durable job state."""

import json
import logging
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from scheduler import (
    build_job_specs,
    build_source_config,
    register_source_jobs,
    run_source_job,
)


class SchedulerOrchestrationTests(unittest.TestCase):
    def _config(self, temp_dir):
        return {
            "app": {"language": "zh"},
            "sources": {
                "arxiv": {"enabled": True},
                "openalex_search": {"enabled": True},
                "rss": {"enabled": True},
                "policy": {"enabled": True},
                "industry_report": {"enabled": True},
            },
            "scheduler": {
                "enabled": True,
                "timezone": "Asia/Shanghai",
                "status_path": str(Path(temp_dir, "scheduler_status.json")),
                "task_log_path": str(Path(temp_dir, "scheduler_jobs.jsonl")),
                "retry": {
                    "max_attempts": 2,
                    "base_delay_seconds": 0,
                    "max_delay_seconds": 0,
                },
            },
        }

    def test_default_jobs_cover_required_source_frequencies(self):
        specs = build_job_specs({"scheduler": {}})
        indexed = {item["id"]: item for item in specs}

        self.assertEqual(indexed["academic_weekly"]["sources"], ["arxiv", "openalex_search", "crossref", "openaire", "semantic_scholar"])
        self.assertEqual(indexed["news_8h"]["hours"], 8)
        self.assertEqual(indexed["policy_daily"]["trigger"], "cron")
        self.assertEqual(indexed["industry_weekly"]["day_of_week"], "mon")

    def test_source_config_is_isolated_and_incremental(self):
        original = {"sources": {name: {"enabled": True} for name in (
            "arxiv", "openalex_search", "rss", "policy", "industry_report"
        )}}

        isolated = build_source_config(original, ["policy"])

        self.assertTrue(isolated["sources"]["policy"]["enabled"])
        self.assertFalse(isolated["sources"]["rss"]["enabled"])
        self.assertTrue(isolated["runtime"]["merge_with_latest"])
        self.assertTrue(original["sources"]["rss"]["enabled"])

    def test_retry_succeeds_and_persists_jsonl_and_status(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config = self._config(temp_dir)
            attempts = []

            def runner(context):
                attempts.append(1)
                if len(attempts) == 1:
                    raise RuntimeError("temporary outage")
                context.source_records = {"rss": [{"id": "news-1"}]}
                context.normalized_records = [{"id": "news-1", "source_type": "news"}]
                context.artifacts = {"linked_documents": "snapshot.json"}
                return context

            result = run_source_job(
                "news_8h",
                ["rss"],
                config=config,
                logger=logging.getLogger("test.scheduler.retry"),
                pipeline_runner=runner,
                sleep_func=lambda _seconds: None,
            )

            status = json.loads(Path(config["scheduler"]["status_path"]).read_text(encoding="utf-8"))
            events = [
                json.loads(line)
                for line in Path(config["scheduler"]["task_log_path"]).read_text(encoding="utf-8").splitlines()
            ]
            self.assertTrue(result["success"])
            self.assertEqual(result["attempts"], 2)
            self.assertEqual(status["jobs"]["news_8h"]["status"], "succeeded")
            self.assertIn("retry_scheduled", [event["event"] for event in events])

    def test_terminal_failure_is_returned_without_raising(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            config = self._config(temp_dir)
            runner = Mock(side_effect=RuntimeError("source unavailable"))

            result = run_source_job(
                "policy_daily",
                ["policy"],
                config=config,
                logger=logging.getLogger("test.scheduler.failure"),
                pipeline_runner=runner,
                sleep_func=lambda _seconds: None,
            )

            status = json.loads(Path(config["scheduler"]["status_path"]).read_text(encoding="utf-8"))
            self.assertFalse(result["success"])
            self.assertEqual(result["attempts"], 2)
            self.assertEqual(status["jobs"]["policy_daily"]["status"], "failed")
            self.assertEqual(runner.call_count, 2)

    def test_registration_uses_cron_and_interval_triggers(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            scheduler = Mock()
            config = self._config(temp_dir)
            specs = register_source_jobs(
                scheduler,
                config,
                logging.getLogger("test.scheduler.registration"),
            )

        calls = scheduler.add_job.call_args_list
        self.assertEqual(len(specs), 4)
        self.assertEqual(len(calls), 4)
        triggers = {call.kwargs["id"]: call.kwargs["trigger"] for call in calls}
        self.assertIsInstance(triggers["academic_weekly"], CronTrigger)
        self.assertIsInstance(triggers["news_8h"], IntervalTrigger)
        self.assertEqual(calls[0].kwargs["max_instances"], 1)


if __name__ == "__main__":
    unittest.main()
