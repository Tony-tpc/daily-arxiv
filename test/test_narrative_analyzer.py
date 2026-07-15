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
        self.assertNotIn("机械臂", "".join(section["markdown"] for section in payload["sections"]))
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


if __name__ == "__main__":
    unittest.main()
