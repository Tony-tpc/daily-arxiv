#!/usr/bin/env python3
"""Tests for the unified document schema."""

import sys
import unittest
from pathlib import Path


project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.models.document_schema import DocumentSchema, SourceType, create_document


class DocumentSchemaTests(unittest.TestCase):
    def test_create_valid_paper_document(self):
        document = create_document(
            SourceType.PAPER,
            id="arxiv-1234.5678",
            source_name="arXiv",
            title="A Multi-Source Research Tracker",
            authors_or_orgs=["Alice", "Bob"],
            categories=["cs.AI"],
            arxiv_id="1234.5678",
        )

        self.assertEqual(document.source_type, "paper")
        self.assertEqual(document.categories, ["cs.AI"])
        self.assertEqual(document.reading_suggestion.read_priority, "medium")

    def test_from_dict_builds_nested_structures(self):
        payload = {
            "id": "policy-001",
            "source_type": "policy",
            "source_name": "NDRC",
            "title": "Policy Support for Embodied Intelligence",
            "issuing_body": "NDRC",
            "reading_suggestion": {
                "why_relevant": "Touches embodied AI infrastructure",
                "read_priority": "high",
                "recommended_action": "deep_read",
                "related_topics": ["embodied intelligence"],
            },
            "provenance": {
                "collected_via": "policy_adapter",
                "source_record_id": "policy-001",
                "fetch_url": "https://example.com/policy-001",
            },
        }

        document = DocumentSchema.from_dict(payload)

        self.assertEqual(document.issuing_body, "NDRC")
        self.assertEqual(document.reading_suggestion.read_priority, "high")
        self.assertEqual(document.provenance.collected_via, "policy_adapter")

    def test_validate_rejects_missing_news_media_name(self):
        with self.assertRaises(ValueError):
            create_document(
                SourceType.NEWS,
                id="news-001",
                source_name="Some News Source",
                title="Embodied Robotics Update",
            )


if __name__ == "__main__":
    unittest.main()
