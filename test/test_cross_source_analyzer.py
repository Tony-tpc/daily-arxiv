"""Tests for academic-policy-industry direction comparison."""

import unittest

from src.analyzer.cross_source_analyzer import CrossSourceAnalyzer


class CrossSourceAnalyzerTests(unittest.TestCase):
    def setUp(self):
        self.analyzer = CrossSourceAnalyzer({
            'analysis': {
                'cross_source': {
                    'strong_threshold': 60,
                    'resonance_threshold': 55,
                    'weak_threshold': 40,
                }
            }
        })

    def test_generates_all_required_direction_judgments(self):
        documents = [
            _document('paper-a1', 'paper', '学术方向', 90, citations=80),
            _document('paper-a2', 'paper', '学术方向', 85, citations=30),
            _document('policy-p', 'policy', '政策方向', 85, policy_strength='high'),
            _document('industry-i', 'industry_report', '产业方向', 85),
            _document('paper-r', 'paper', '共振方向', 85, citations=20),
            _document('policy-r', 'policy', '共振方向', 85, policy_strength='high'),
            _document('industry-r', 'industry_report', '共振方向', 85),
        ]

        result = self.analyzer.analyze(documents)
        judgments = {
            item['direction']: item['judgment'] for item in result['directions']
        }

        self.assertEqual(judgments['学术方向'], '学术领先但政策/行业弱')
        self.assertEqual(judgments['政策方向'], '政策驱动增强')
        self.assertEqual(judgments['产业方向'], '行业高度关注')
        self.assertEqual(judgments['共振方向'], '三端共振')
        self.assertEqual(result['summary']['triple_resonance_directions'], ['共振方向'])

    def test_filters_generic_topics_and_keeps_explainable_evidence(self):
        result = self.analyzer.analyze([
            {
                **_document('policy-1', 'policy', '虚拟电厂', 88, policy_strength='high'),
                'themes': ['能源系统', '政策治理'],
                'tags': ['虚拟电厂'],
                'title': '虚拟电厂参与电力市场政策',
                'url': 'https://www.nea.gov.cn/policy-1',
            }
        ])

        self.assertEqual(result['direction_count'], 1)
        direction = result['directions'][0]
        self.assertEqual(direction['direction'], '虚拟电厂')
        self.assertEqual(direction['evidence_counts']['policy'], 1)
        self.assertGreaterEqual(direction['scores']['policy_support'], 60)
        self.assertIn('政策支持', direction['rationale'])
        self.assertEqual(direction['representative_documents'][0]['id'], 'policy-1')

    def test_empty_input_has_stable_summary(self):
        result = self.analyzer.analyze([])

        self.assertEqual(result['direction_count'], 0)
        self.assertEqual(result['directions'], [])
        self.assertEqual(result['summary']['judgment_distribution'], {})
        self.assertEqual(result['summary']['highest_research_value'], '')


def _document(document_id, source_type, topic, score, **extra):
    breakdown = {
        'novelty': score,
        'policy_importance': score,
        'industry_relevance': score,
    }
    return {
        'id': document_id,
        'source_type': source_type,
        'source_name': source_type,
        'title': document_id,
        'research_direction': [topic],
        'importance_score': score,
        'ranking_score_breakdown': breakdown,
        **extra,
    }


if __name__ == '__main__':
    unittest.main()
