"""Tests for weekly/stage report generation and persistence."""

import json
import tempfile
import unittest
from pathlib import Path

import markdown

from src.reporting.intelligence_report_generator import IntelligenceReportGenerator
from src.reporting.research_report_generator import ResearchReportGenerator


class ResearchReportGeneratorTests(unittest.TestCase):
    def test_legacy_import_remains_compatible(self):
        self.assertIs(IntelligenceReportGenerator, ResearchReportGenerator)

    def test_weekly_report_is_topic_first_with_source_appendices(self):
        generator = ResearchReportGenerator({'reporting': {'max_items_per_section': 4}})
        report = generator.generate(
            _documents(),
            _analysis(),
            report_type='weekly',
            period_start='2026-07-08',
            period_end='2026-07-14',
        )

        self.assertEqual(report['report_type'], 'weekly')
        self.assertEqual(report['document_count'], 4)
        self.assertEqual(
            [section['key'] for section in report['sections']],
            [
                'future_outlook', 'topic_decision_cards', 'cross_source_transmission',
                'near_term_forecast', 'strategic_scenarios', 'research_actions',
                'monitoring', 'appendix_papers', 'appendix_policies',
                'appendix_news', 'appendix_industry_reports',
            ],
        )
        self.assertEqual(report['schema_version'], '2.0')
        self.assertIn('未来趋势总览', report['markdown'])
        self.assertIn('低置信情景', report['markdown'])
        self.assertIn('反证条件', report['markdown'])
        self.assertIn('科研行动建议', report['markdown'])
        self.assertNotIn('研究价值 90.0', report['markdown'])
        rendered = markdown.markdown(report['markdown'])
        self.assertNotIn('href="javascript:', rendered)
        self.assertNotIn('<script', rendered)

    def test_stage_report_saves_json_markdown_and_latest_atomically(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            generator = ResearchReportGenerator({
                'reporting': {'directory': temp_dir},
            })
            report = generator.generate(
                _documents(),
                _analysis(),
                report_type='stage',
                period_start='2026-06-15',
                period_end='2026-07-14',
            )
            paths = generator.save(report)

            self.assertTrue(Path(paths['json']).is_file())
            self.assertTrue(Path(paths['markdown']).is_file())
            self.assertTrue(Path(paths['latest_json']).is_file())
            saved = json.loads(Path(paths['latest_json']).read_text(encoding='utf-8'))
            self.assertEqual(saved['report_type'], 'stage')
            self.assertEqual(saved['report_id'], 'stage_2026-06-15_2026-07-14')

    def test_invalid_report_period_is_rejected(self):
        generator = ResearchReportGenerator()
        with self.assertRaisesRegex(ValueError, 'period_start'):
            generator.generate(
                [], {}, report_type='weekly',
                period_start='2026-07-14', period_end='2026-07-01',
            )


def _documents():
    return [
        {
            'id': 'paper-1', 'source_type': 'paper', 'title': '<b>[能源](javascript:alert(1))论文</b>',
            'summary': '面向虚拟电厂的自主决策。', 'published_at': '2026-07-14',
            'importance_score': 90, 'url': 'javascript:alert(1)',
        },
        {
            'id': 'policy-1', 'source_type': 'policy', 'title': '虚拟电厂政策',
            'summary': '国家能源局推动需求响应。', 'published_at': '2026-07-13',
            'importance_score': 88, 'issuing_body': '国家能源局',
            'url': 'https://www.nea.gov.cn/policy-1',
        },
        {
            'id': 'news-1', 'source_type': 'news', 'title': '国内示范新闻',
            'published_at': '2026-07-12', 'importance_score': 70,
        },
        {
            'id': 'industry-1', 'source_type': 'industry_report', 'title': '电网行业报告',
            'published_at': '2026-07-11', 'importance_score': 82,
        },
    ]


def _analysis():
    return {
        'trend_forecast': {
            'schema_version': '2.0',
            'as_of': '2026-07-14',
            'data_quality': {
                'document_count': 4, 'history_month_count': 2,
                'gaps': ['历史月份不足'],
            },
            'forecasts': [{
                'topic_id': 'grid_coordination', 'topic': '源网荷储与虚拟电厂协同',
                'mode': 'scenario_only', 'trajectory': 'rising', 'confidence': 'low',
                'metrics': {
                    'velocity': 0.2, 'acceleration': 0.1, 'persistence': 0.5,
                    'source_diversity': 3,
                },
                'drivers': ['论文、政策与国内案例均出现'],
                'data_gaps': ['可用月份 2/12'],
                'evidence_ids': ['paper-1', 'policy-1'],
                'counter_signals': ['历史月份不足'],
                'watch_indicators': ['可调资源聚合规模'],
                'research_action': '建立源网荷储多主体协同基准。',
                'projections': [],
            }],
            'scenarios': [{
                'topic_id': 'grid_coordination', 'topic': '源网荷储与虚拟电厂协同',
                'confidence': 'low', 'base_case': '保持探索',
                'upside': '跨来源连续增长', 'downside': '验证指标没有改善',
                'evidence_ids': ['paper-1', 'policy-1'],
                'counter_signals': ['历史月份不足'],
                'research_action': '建立协同基准。',
            }],
            'lead_lag': [{
                'topic_id': 'grid_coordination', 'topic': '源网荷储与虚拟电厂协同',
                'status': 'supported', 'lag_months': 2,
                'limitation': '时间顺序不等同于因果关系',
                'sequence': [
                    {'source_type': 'paper', 'onset': '2026-01-01'},
                    {'source_type': 'policy', 'onset': '2026-03-01'},
                ],
            }],
        },
        'temporal_trends': {
            'windows': {
                '7': {
                    'current_document_count': 4,
                    'topic_momentum': [
                        {'name': '虚拟电厂', 'delta': 3, 'status': 'rising'}
                    ],
                }
            }
        },
        'cross_source_analysis': {
            'directions': [{
                'direction': '虚拟电厂',
                'judgment_code': 'triple_resonance',
                'judgment': '三端共振',
                'rationale': '论文、政策与产业信号同步增强。',
            }]
        },
        'research_profile_analysis': {
            'advantages': [{
                'name': '虚拟电厂自主决策',
                'explanation': '已有优势：覆盖分 80.0，找到 3 条外部证据。',
            }],
            'gaps': [{
                'name': '数字孪生驱动的能源设备感知',
                'explanation': '存在差距：覆盖分 0.0，找到 0 条外部证据。',
            }],
            'reinforcement_directions': [{
                'direction': '数字孪生驱动的能源设备感知',
                'reason': '需要补充中国能源场景证据。',
                'priority': 'high',
            }],
            'follow_up': {
                'papers': [{
                    'title': '能源智能体论文', 'source_type': 'paper',
                    'url': 'https://arxiv.org/abs/1', 'reason': '匹配虚拟电厂',
                }],
                'policies': [],
                'industry_cases': [],
            },
        },
    }


if __name__ == '__main__':
    unittest.main()
