#!/usr/bin/env python3
"""Tests for mixed-source, structured document summarization."""

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch


project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.summarizer.document_summarizer import DocumentSummarizer
from src.summarizer.paper_summarizer import PaperSummarizer


def _response(**overrides):
    payload = {
        "summary": "这是一段面向中国研究场景的结构化概括。",
        "core_viewpoints": ["观点一", "观点二"],
        "research_relevance": "与能源系统中的智能决策研究直接相关。",
        "worth_reading": True,
        "follow_up_suggestions": ["核对原始数据", "加入专题跟踪"],
    }
    payload.update(overrides)
    return json.dumps(payload, ensure_ascii=False)


class DocumentSummarizerTests(unittest.TestCase):
    def setUp(self):
        self.client = Mock(model="mock-model")
        self.client.generate.return_value = _response()
        self.config = {
            "tracking_topics": [
                "virtual power plant",
                "embodied intelligence for energy systems",
            ],
            "research_profile": {
                "focus": ["能源智能体与物理能源设备交互"],
                "excluded_directions": ["机器人操控", "机械臂"],
            },
            "summarization": {"max_input_chars": 2000, "max_tokens": 600},
        }
        self.summarizer = DocumentSummarizer(self.config, llm_client=self.client)

    def test_uses_source_specific_prompt_for_every_supported_type(self):
        expected_terms = {
            "paper": "研究问题、方法与数据",
            "policy": "中国政策",
            "news": "已发生事实",
            "industry_report": "关键数据",
        }
        for source_type, expected_term in expected_terms.items():
            with self.subTest(source_type=source_type):
                self.summarizer.summarize_document(
                    {
                        "id": source_type,
                        "source_type": source_type,
                        "source_name": "国内来源",
                        "title": f"{source_type} title",
                        "raw_text": "document body",
                    }
                )
                prompt = self.client.generate.call_args.kwargs["prompt"]
                self.assertIn(expected_term, prompt)
                self.assertIn("virtual power plant", prompt)
                self.assertIn("机械臂", prompt)

    def test_returns_web_ready_structured_fields(self):
        result = self.summarizer.summarize_document(
            {
                "id": "policy-1",
                "source_type": "policy",
                "source_name": "国家发展改革委",
                "title": "政策标题",
                "raw_text": "政策正文",
                "url": "https://www.ndrc.gov.cn/example",
            }
        )

        self.assertFalse(result["summary_error"])
        self.assertEqual(result["core_viewpoints"], ["观点一", "观点二"])
        self.assertTrue(result["worth_reading"])
        self.assertEqual(result["web_card"]["summary"], result["summary"])
        self.assertEqual(result["web_card"]["core_viewpoints"], result["core_viewpoints"])
        self.assertEqual(
            result["web_card"]["follow_up_suggestions"],
            result["follow_up_suggestions"],
        )

    def test_legacy_paper_api_uses_abstract_and_authors(self):
        summarizer = PaperSummarizer(self.config, llm_client=self.client)
        result = summarizer.summarize_paper(
            {
                "id": "2501.00001",
                "title": "Legacy paper",
                "abstract": "Legacy abstract text",
                "authors": ["Alice", "Bob"],
            }
        )

        prompt = self.client.generate.call_args.kwargs["prompt"]
        self.assertIn("Legacy abstract text", prompt)
        self.assertEqual(result["authors_or_orgs"], ["Alice", "Bob"])
        self.assertEqual(result["summary_prompt_type"], "paper")

    def test_invalid_llm_output_has_stable_fallback_card(self):
        self.client.generate.return_value = "not json"
        result = self.summarizer.summarize_document(
            {
                "id": "news-1",
                "source_type": "news",
                "source_name": "人民网",
                "title": "新闻标题",
                "raw_text": "用于回退展示的新闻正文。",
            }
        )

        self.assertTrue(result["summary_error"])
        self.assertEqual(result["summary"], "用于回退展示的新闻正文。")
        self.assertFalse(result["worth_reading"])
        self.assertEqual(result["web_card"]["research_relevance"], "待人工复核")

    def test_batch_snapshot_contains_document_and_legacy_keys(self):
        self.client.get_provider_name.return_value = "Mock"
        with tempfile.TemporaryDirectory() as temp_dir, patch(
            "src.summarizer.document_summarizer.get_data_path",
            side_effect=lambda config, subdir: str(Path(temp_dir, subdir)),
        ):
            results = self.summarizer.summarize_documents(
                [
                    {
                        "id": "report-1",
                        "source_type": "industry_report",
                        "source_name": "国内研究机构",
                        "title": "行业报告",
                        "raw_text": "报告内容",
                    }
                ],
                show_progress=False,
            )
            latest = json.loads(
                Path(temp_dir, "summaries", "latest.json").read_text(encoding="utf-8")
            )

        self.assertEqual(len(results), 1)
        self.assertEqual(latest["documents"], latest["papers"])
        self.assertEqual(latest["documents"], latest["summaries"])


if __name__ == "__main__":
    unittest.main()
