"""Tests for evidence-grounded long-form trend narratives."""

from __future__ import annotations

import unittest

from src.analyzer.narrative_analyzer import NarrativeAnalyzer, legacy_llm_analysis


class _InvalidNarrativeClient:
    def __init__(self):
        self.calls = 0

    def generate(self, prompt, max_tokens=0):
        self.calls += 1
        return "## 当前研究热点\n很短的无效结论[BAD01]"


class NarrativeAnalyzerTests(unittest.TestCase):
    def setUp(self):
        self.config = {
            "negative_keywords": ["robot arm", "机械臂", "人形机器人"],
            "analysis": {"narrative": {"min_chars": 4000, "max_chars": 6000}},
        }

    def test_paper_narrative_restores_five_long_form_sections(self):
        payload = NarrativeAnalyzer(self.config).generate_paper(_paper_documents())

        self.assertEqual(payload["view"], "paper")
        self.assertEqual(
            [section["id"] for section in payload["sections"]],
            ["hotspots", "technical_evolution", "future_directions", "research_ideas", "summary"],
        )
        self.assertGreaterEqual(payload["char_count"], 4000)
        self.assertLessEqual(payload["char_count"], 6000)
        self.assertEqual(payload["coverage"]["source_counts"], {"paper": 15})
        self.assertNotIn("policy-1", str(payload))
        narrative = "".join(section["markdown"] for section in payload["sections"])
        self.assertNotIn("机械臂", narrative)
        self.assertNotIn("机器人", narrative)
        self.assertGreaterEqual(len(payload["opportunities"]), 5)
        allowed = set(payload["evidence_index"])
        for section in payload["sections"]:
            for claim in section["claims"]:
                self.assertTrue(set(claim["evidence_ids"]).issubset(allowed))

        legacy = legacy_llm_analysis(payload)
        self.assertIn("当前研究热点", payload["sections"][0]["title"])
        self.assertEqual(legacy["char_count"], payload["char_count"])
        self.assertIn("闭环", legacy["research_ideas"])

    def test_invalid_llm_output_falls_back_to_detailed_evidence_digest(self):
        client = _InvalidNarrativeClient()
        payload = NarrativeAnalyzer(self.config, client).generate_paper(_paper_documents())

        self.assertEqual(client.calls, 2)
        self.assertEqual(payload["generation_status"], "deterministic_digest")
        self.assertGreaterEqual(payload["char_count"], 4000)
        self.assertNotIn("BAD01", str(payload))

    def test_multi_source_narrative_balances_sources_and_builds_evidence_chains(self):
        payload = NarrativeAnalyzer(self.config).generate_multi_source(_multi_source_documents())

        self.assertEqual(payload["view"], "multi_source")
        self.assertEqual(payload["coverage"]["status"], "complete")
        self.assertEqual(
            payload["coverage"]["selected_source_counts"],
            {"paper": 15, "policy": 12, "news": 12, "industry_report": 12},
        )
        self.assertGreaterEqual(payload["char_count"], 4000)
        self.assertLessEqual(payload["char_count"], 6000)
        self.assertEqual(len(payload["evidence_chains"]), 5)
        self.assertTrue(all(len(chain["nodes"]) == 4 for chain in payload["evidence_chains"]))
        self.assertTrue(all(chain["causality_note"] for chain in payload["evidence_chains"]))
        prefixes = {key.rstrip("0123456789") for key in payload["evidence_index"]}
        self.assertEqual(prefixes, {"P", "POL", "N", "R"})

    def test_multi_source_narrative_discloses_domestic_source_gaps(self):
        documents = _multi_source_documents()
        documents = [
            item for item in documents
            if item["source_type"] not in {"news", "industry_report"}
        ] + [
            item for item in documents if item["source_type"] == "news"
        ][:1]
        payload = NarrativeAnalyzer(self.config).generate_multi_source(documents)

        self.assertEqual(payload["coverage"]["status"], "partial")
        self.assertTrue(any("国内新闻仅1条" in gap for gap in payload["coverage"]["gaps"]))
        self.assertTrue(any("行业报告仅0条" in gap for gap in payload["coverage"]["gaps"]))
        self.assertIn("证据缺口", str(payload["evidence_chains"]))
        self.assertGreaterEqual(payload["char_count"], 4000)


def _paper_documents():
    topics = [
        (
            "Multi-Agent Reinforcement Learning for Autonomous Microgrid Management",
            "A DEC-POMDP coordinates solar wind battery resources in an IEEE 33-bus microgrid.",
            "Multi-Agent Reinforcement Learning",
        ),
        (
            "Game-Theoretic Peer-to-Peer Energy Trading for Low-Carbon Microgrids",
            "A Stackelberg market clearing model compares social welfare and individual revenue.",
            "Electricity Market and Game Theory",
        ),
        (
            "Cyber-Physical Resilience Control under Adaptive Grid Attacks",
            "Safe reinforcement learning protects critical load and reports recovery time.",
            "Smart Grid Security and Resilience",
        ),
        (
            "Physics-Informed State Estimation and Load Forecasting",
            "A graph attention model reports calibration error and cross-condition generalization.",
            "Energy Load and Power Forecasting",
        ),
        (
            "Digital Twin Hardware-in-the-Loop Validation for Virtual Power Plants",
            "A co-simulation benchmark measures real-time error and controller constraint violations.",
            "Digital Twin and Engineering Validation",
        ),
    ]
    documents = []
    for index in range(15):
        title, abstract, category = topics[index % len(topics)]
        month = index % 12 + 1
        documents.append({
            "id": f"paper-{index + 1}",
            "source_type": "paper",
            "source_name": "OpenAlex",
            "title": f"{title} Study {index + 1}",
            "abstract": abstract,
            "summary": abstract,
            "categories": [category],
            "keywords": [category],
            "published_at": f"2025-{month:02d}-{index % 27 + 1:02d}",
            "url": f"https://example.org/paper-{index + 1}",
        })
    documents.extend([
        {
            "id": "policy-1", "source_type": "policy", "title": "虚拟电厂政策",
            "published_at": "2025-03-01",
        },
        {
            "id": "excluded-robot", "source_type": "paper", "title": "机械臂抓取控制",
            "abstract": "A robot arm manipulation study.", "published_at": "2025-04-01",
        },
    ])
    return documents


def _multi_source_documents():
    documents = _paper_documents()[:-2]
    source_specs = {
        "policy": ("国家能源局", "虚拟电厂与电力市场运行规则通知"),
        "news": ("人民网能源频道", "多地推进虚拟电厂参与需求响应"),
        "industry_report": ("国家能源局电力可靠性管理中心", "中国电力市场与供电可靠性报告"),
    }
    for source_type, (source_name, title) in source_specs.items():
        for index in range(12):
            month = index % 6 + 1
            documents.append({
                "id": f"{source_type}-{index + 1}",
                "source_type": source_type,
                "source_name": source_name,
                "title": f"{title} {index + 1}",
                "summary": (
                    "材料涉及微电网、源网荷储协同、低碳调度、电力市场、需求响应、"
                    "能源安全和数字孪生验证。"
                ),
                "published_at": f"2025-{month:02d}-{index % 27 + 1:02d}",
                "url": f"https://example.gov.cn/{source_type}-{index + 1}",
                "region": "CN",
            })
    return documents


if __name__ == "__main__":
    unittest.main()
