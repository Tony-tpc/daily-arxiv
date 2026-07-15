"""Tests for resumable, event-dated historical backfill."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.history.backfill import BackfillService, FetchResult, HistoricalCorpus


class HistoricalCorpusTests(unittest.TestCase):
    def test_monthly_write_is_atomic_idempotent_and_portable(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            corpus = HistoricalCorpus(temp_dir)
            first = _document("paper-1", "2026-06-05", title="first")
            updated = _document("paper-1", "2026-06-05", title="updated")

            path = corpus.write_period(
                "openalex_search", "2026-06", FetchResult([first])
            )
            corpus.write_period(
                "openalex_search", "2026-06", FetchResult([updated])
            )

            payload = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(payload["document_count"], 1)
            self.assertEqual(payload["documents"][0]["title"], "updated")
            self.assertNotIn("\\", corpus.load_coverage()["entries"]["openalex_search:2026-06"]["location"])
            self.assertFalse(list(Path(temp_dir).rglob("*.tmp")))
            observations = corpus.load_observations(
                date_from="2026-06-01", date_to="2026-06-30"
            )
            self.assertEqual(observations[0]["document"]["id"], "paper-1")

    def test_backfill_resumes_completed_months_without_duplicate_fetches(self):
        calls = []

        def fetcher(period_start, period_end):
            calls.append((period_start, period_end))
            return FetchResult([
                _document(
                    f"paper-{period_start:%Y-%m}",
                    period_start.isoformat(),
                )
            ])

        with tempfile.TemporaryDirectory() as temp_dir:
            corpus = HistoricalCorpus(temp_dir)
            service = BackfillService(
                {"analysis": {"history_directory": temp_dir}},
                corpus=corpus,
                fetchers={"openalex_search": fetcher},
            )
            first = service.run(
                months=2, as_of="2026-07-15", sources=["openalex_search"]
            )
            second = service.run(
                months=2, as_of="2026-07-15", sources=["openalex_search"]
            )

            self.assertEqual(first["completed_periods"], 2)
            self.assertEqual(second["skipped_periods"], 2)
            self.assertEqual(len(calls), 2)
            self.assertEqual(
                corpus.load_coverage()["status_counts"]["complete"], 2
            )

    def test_unavailable_period_is_recorded_instead_of_fabricated(self):
        def failing_fetcher(_period_start, _period_end):
            raise RuntimeError("archive unavailable")

        with tempfile.TemporaryDirectory() as temp_dir:
            service = BackfillService(
                {"analysis": {"history_directory": temp_dir}},
                fetchers={"rss": failing_fetcher},
            )
            result = service.run(
                months=1, as_of="2026-07-15", sources=["rss"]
            )

            entry = result["coverage"]["entries"]["rss:2026-07"]
            self.assertEqual(entry["status"], "unavailable")
            self.assertEqual(entry["document_count"], 0)
            self.assertIn("archive unavailable", entry["errors"][0])

    def test_html_archive_is_fetched_once_then_partitioned_by_month(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            service = BackfillService(
                {"analysis": {"history_directory": temp_dir}}
            )
            documents = [
                {
                    "id": "policy-june",
                    "source_type": "policy",
                    "title": "能源政策",
                    "published_at": "2026-06-10",
                },
                {
                    "id": "policy-july",
                    "source_type": "policy",
                    "title": "电力政策",
                    "published_at": "2026-07-10",
                },
            ]
            with patch.object(
                service, "_fetch_period", return_value=FetchResult(documents)
            ) as fetch_period:
                service.run(months=2, as_of="2026-07-15", sources=["policy"])

            fetch_period.assert_called_once()
            corpus = HistoricalCorpus(temp_dir)
            self.assertEqual(
                len(corpus.load_observations(date_from="2026-06-01", date_to="2026-06-30")),
                1,
            )


def _document(document_id, published_at, *, title="energy agent"):
    return {
        "id": document_id,
        "source_type": "paper",
        "source_name": "OpenAlex",
        "title": title,
        "published_at": published_at,
        "tags": ["energy system"],
    }


if __name__ == "__main__":
    unittest.main()
