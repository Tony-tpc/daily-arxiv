"""Tests for high-impact journal whitelist admission."""

import unittest

from src.sources.paper_normalizer import normalize_paper_records
from src.sources.paper_quality import (
    enrich_openalex_venue_metadata,
    evaluate_paper_quality,
)


QUALITY_CONFIG = {
    "paper_quality": {
        "enabled": True,
        "require_formal_journal_article": True,
        "accepted_publication_types": ["article", "journal-article"],
        "maximum_allowed_quartile": "Q2",
        "approved_venues": [
            {
                "id": "smart_grid",
                "name": "IEEE Transactions on Smart Grid",
                "issn_l": "1949-3053",
                "quartile": "Q1",
            },
            {
                "id": "power_systems",
                "name": "IEEE Transactions on Power Systems",
                "issn_l": "0885-8950",
                "quartile": "Q2",
            },
            {
                "id": "low_rank_example",
                "name": "Low Rank Energy Journal",
                "issn_l": "1234-5678",
                "quartile": "Q3",
            },
        ],
    }
}


class PaperQualityTests(unittest.TestCase):
    def test_maps_openalex_formal_venue_metadata(self):
        record = {"id": "W1", "title": "Energy coordination"}
        work = {
            "type": "article",
            "primary_location": {
                "source": {
                    "display_name": "IEEE Transactions on Smart Grid",
                    "issn_l": "1949-3053",
                    "issn": ["1949-3053", "1949-3061"],
                    "host_organization_name": "IEEE",
                }
            },
        }

        enriched = enrich_openalex_venue_metadata(record, work)

        self.assertEqual(enriched["publication_type"], "article")
        self.assertEqual(enriched["journal_name"], "IEEE Transactions on Smart Grid")
        self.assertEqual(enriched["journal_issn_l"], "1949-3053")
        self.assertEqual(enriched["journal_publisher"], "IEEE")

    def test_allows_configured_q1_and_q2_journals(self):
        q1 = evaluate_paper_quality({
            "publication_type": "article",
            "journal_name": "IEEE Transactions on Smart Grid",
            "journal_issn_l": "1949-3053",
        }, QUALITY_CONFIG)
        q2 = evaluate_paper_quality({
            "publication_type": "journal-article",
            "journal_name": "IEEE Transactions on Power Systems",
            "journal_issn_l": "0885-8950",
        }, QUALITY_CONFIG)

        self.assertTrue(q1["allowed"])
        self.assertEqual(q1["quartile"], "Q1")
        self.assertTrue(q2["allowed"])
        self.assertEqual(q2["quartile"], "Q2")

    def test_rejects_preprint_unknown_or_low_quartile_papers(self):
        preprint = evaluate_paper_quality({
            "publication_type": "preprint",
            "journal_name": "IEEE Transactions on Smart Grid",
            "journal_issn_l": "1949-3053",
        }, QUALITY_CONFIG)
        unknown = evaluate_paper_quality({
            "publication_type": "article",
            "journal_name": "Unknown Energy Journal",
            "journal_issn_l": "0000-0000",
        }, QUALITY_CONFIG)
        low_rank = evaluate_paper_quality({
            "publication_type": "article",
            "journal_name": "Low Rank Energy Journal",
            "journal_issn_l": "1234-5678",
        }, QUALITY_CONFIG)

        self.assertEqual(preprint["reason"], "not_a_formal_journal_article")
        self.assertEqual(unknown["reason"], "venue_not_whitelisted")
        self.assertEqual(low_rank["reason"], "venue_below_quartile_threshold")

    def test_rejects_conflicting_issn_even_when_name_matches(self):
        decision = evaluate_paper_quality({
            "publication_type": "article",
            "journal_name": "IEEE Transactions on Smart Grid",
            "journal_issn_l": "9999-9999",
        }, QUALITY_CONFIG)

        self.assertFalse(decision["allowed"])
        self.assertEqual(decision["reason"], "venue_not_whitelisted")

    def test_normalizer_keeps_only_admitted_papers(self):
        records = [
            {
                "id": "W1",
                "title": "Multi-agent energy control",
                "categories": ["Energy systems"],
                "entry_url": "https://doi.org/10.1000/W1",
                "publication_type": "article",
                "journal_name": "IEEE Transactions on Smart Grid",
                "journal_issn_l": "1949-3053",
            },
            {
                "id": "W2",
                "title": "Unreviewed energy control",
                "categories": ["Energy systems"],
                "entry_url": "https://arxiv.org/abs/2601.00001",
                "publication_type": "preprint",
            },
        ]

        admitted = normalize_paper_records(records, "openalex_search", QUALITY_CONFIG)

        self.assertEqual([paper["id"] for paper in admitted], ["W1"])
        self.assertEqual(admitted[0]["quality_gate"]["venue_id"], "smart_grid")


if __name__ == "__main__":
    unittest.main()
