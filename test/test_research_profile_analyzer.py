"""Tests for user research-profile comparison."""

import unittest

from src.analyzer.research_profile_analyzer import ResearchProfileAnalyzer


class ResearchProfileAnalyzerTests(unittest.TestCase):
    def setUp(self):
        self.config = {
            'research_profile': {
                'topic': '能源系统具身智能',
                'focus': ['虚拟电厂自主决策'],
                'technical_routes': ['多智能体强化学习', '数字孪生驱动的能源设备感知'],
                'excluded_directions': ['机械臂'],
                'comparison': {
                    'strength_threshold': 60,
                    'gap_threshold': 30,
                    'follow_up_per_type': 2,
                },
            }
        }
        self.analyzer = ResearchProfileAnalyzer(self.config)

    def test_outputs_advantages_gaps_reinforcement_and_followups(self):
        result = self.analyzer.analyze(_documents(), {
            'directions': [{
                'direction': '虚拟电厂',
                'judgment': '三端共振',
                'judgment_code': 'triple_resonance',
            }]
        })

        self.assertEqual(result['status'], 'ready')
        self.assertIn('虚拟电厂自主决策', _names(result['advantages']))
        self.assertIn('数字孪生驱动的能源设备感知', _names(result['gaps']))
        self.assertIn(
            '数字孪生驱动的能源设备感知',
            {item['direction'] for item in result['reinforcement_directions']},
        )
        self.assertEqual(result['follow_up']['papers'][0]['id'], 'paper-1')
        self.assertEqual(result['follow_up']['policies'][0]['id'], 'policy-1')
        self.assertEqual(result['follow_up']['industry_cases'][0]['id'], 'industry-1')
        followed_ids = {
            item['id']
            for items in result['follow_up'].values()
            for item in items
        }
        self.assertNotIn('robot-1', followed_ids)

    def test_unconfigured_profile_returns_stable_shape(self):
        result = ResearchProfileAnalyzer({}).analyze(_documents())

        self.assertEqual(result['status'], 'unconfigured')
        self.assertEqual(result['coverage'], [])
        self.assertEqual(result['follow_up']['papers'], [])


def _documents():
    return [
        {
            'id': 'paper-1', 'source_type': 'paper',
            'title': '虚拟电厂多智能体强化学习自主决策',
            'importance_score': 90, 'url': 'https://arxiv.org/abs/1',
        },
        {
            'id': 'policy-1', 'source_type': 'policy',
            'title': '虚拟电厂参与需求响应政策',
            'importance_score': 85, 'url': 'https://www.nea.gov.cn/1',
        },
        {
            'id': 'industry-1', 'source_type': 'industry_report',
            'title': '能源智能体与虚拟电厂行业实践',
            'importance_score': 80, 'url': 'https://example.cn/1',
        },
        {
            'id': 'robot-1', 'source_type': 'paper',
            'title': '机械臂强化学习控制', 'importance_score': 99,
        },
    ]


def _names(items):
    return {item['name'] for item in items}


if __name__ == '__main__':
    unittest.main()
