#!/usr/bin/env python3
"""Tests for output template and field standards."""

import importlib
import sys
import unittest
from pathlib import Path


project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.models.document_schema import SourceType, create_document


output_templates = importlib.import_module("src.exporters.output_templates")
OUTPUT_JSON_SCHEMA_VERSION = output_templates.OUTPUT_JSON_SCHEMA_VERSION
READING_SUGGESTION_FIELDS = output_templates.READING_SUGGESTION_FIELDS
WEB_CARD_FIELDS = output_templates.WEB_CARD_FIELDS
build_frontmatter = output_templates.build_frontmatter
build_web_card_payload = output_templates.build_web_card_payload
render_markdown_card = output_templates.render_markdown_card


class OutputTemplateTests(unittest.TestCase):
    def test_build_frontmatter_for_paper(self):
        document = create_document(
            SourceType.PAPER,
            id="paper-001",
            source_name="arXiv",
            title="Paper Title",
            arxiv_id="2501.00001",
            categories=["cs.AI"],
            tags=["embodied-intelligence"],
            reading_suggestion={
                "why_relevant": "Matches tracked topic",
                "read_priority": "high",
                "recommended_action": "deep_read",
                "related_topics": ["robotics"],
            },
        )

        frontmatter = build_frontmatter(document.to_dict())
        self.assertEqual(frontmatter["schema_version"], OUTPUT_JSON_SCHEMA_VERSION)
        self.assertEqual(frontmatter["arxiv_id"], "2501.00001")
        self.assertEqual(frontmatter["reading_suggestion"]["read_priority"], "high")

    def test_render_markdown_card_for_policy(self):
        document = create_document(
            SourceType.POLICY,
            id="policy-001",
            source_name="NDRC",
            title="Policy Title",
            issuing_body="NDRC",
            summary="Policy summary",
            url="https://example.com/policy",
            reading_suggestion={
                "why_relevant": "Supports energy AI",
                "read_priority": "high",
                "recommended_action": "deep_read",
                "related_topics": ["energy systems"],
            },
        )

        markdown = render_markdown_card(document.to_dict())
        self.assertIn("issuing_body: NDRC", markdown)
        self.assertIn("## 政策概述", markdown)
        self.assertIn("Supports energy AI", markdown)

    def test_reading_suggestion_field_spec(self):
        self.assertEqual(
            READING_SUGGESTION_FIELDS,
            ["why_relevant", "read_priority", "recommended_action", "related_topics"],
        )

    def test_build_web_card_payload_for_paper(self):
        document = create_document(
            SourceType.PAPER,
            id="paper-001",
            source_name="arXiv",
            title="Paper Title",
            summary="Normalized summary",
            core_viewpoints=["Point one"],
            research_relevance="Direct match",
            worth_reading=True,
            follow_up_suggestions=["Read methods"],
            raw_text="Fallback abstract",
            authors_or_orgs=["Alice", "Bob", "Carol", "Dave"],
            arxiv_id="2501.00001",
            categories=["cs.AI"],
            tags=["energy"],
            reading_suggestion={
                "why_relevant": "Matches tracked topic",
                "read_priority": "high",
                "recommended_action": "deep_read",
                "related_topics": ["robotics"],
            },
        )

        payload = build_web_card_payload(
            document,
            raw_record={
                "entry_url": "https://arxiv.org/abs/2501.00001",
                "pdf_url": "https://arxiv.org/pdf/2501.00001",
                "citation_count": 42,
                "openalex_primary_topic": "Energy systems",
                "openalex_institutions": ["Tsinghua University"],
                "openalex_referenced_works_count": 12,
                "journal_name": "IEEE Transactions on Smart Grid",
                "journal_issn_l": "1949-3053",
                "quality_gate": {
                    "allowed": True,
                    "reason": "whitelisted_q1_q2_journal",
                    "quartile": "Q1",
                },
            },
        )

        self.assertEqual(sorted(payload.keys()), sorted(WEB_CARD_FIELDS))
        self.assertEqual(payload["links"]["pdf_url"], "https://arxiv.org/pdf/2501.00001")
        self.assertEqual(payload["author_line"], "Alice, Bob, Carol et al.")
        self.assertEqual(payload["badges"], ["cs.AI", "energy"])
        self.assertEqual(payload["core_viewpoints"], ["Point one"])
        self.assertEqual(payload["research_relevance"], "Direct match")
        self.assertTrue(payload["worth_reading"])
        self.assertEqual(payload["follow_up_suggestions"], ["Read methods"])
        self.assertEqual(payload["source_metadata"]["citation_count"], 42)
        self.assertEqual(payload["source_metadata"]["openalex_primary_topic"], "Energy systems")
        self.assertEqual(payload["source_metadata"]["journal_name"], "IEEE Transactions on Smart Grid")
        self.assertEqual(payload["source_metadata"]["journal_quartile"], "Q1")


if __name__ == "__main__":
    unittest.main()
