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
build_frontmatter = output_templates.build_frontmatter
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


if __name__ == "__main__":
    unittest.main()
