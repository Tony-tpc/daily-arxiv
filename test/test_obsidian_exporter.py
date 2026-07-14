#!/usr/bin/env python3
"""Tests for the vault-friendly Obsidian exporter."""

import sys
import tempfile
import unittest
from pathlib import Path

import yaml


project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.exporters.obsidian_exporter import ObsidianExporter, safe_filename


class ObsidianExporterTests(unittest.TestCase):
    def test_exports_all_directories_frontmatter_and_standard_links(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            exporter = ObsidianExporter({
                'outputs': {'obsidian': {'vault_path': temp_dir, 'use_markdown_links': True}}
            })
            documents = _documents()

            result = exporter.export_documents(documents, export_date='2026-07-14')

            for directory in [
                'papers', 'policies', 'news', 'industry_reports', 'daily', 'weekly'
            ]:
                self.assertTrue(Path(temp_dir, directory).is_dir())
            self.assertEqual(result['count'], 4)
            self.assertTrue(Path(result['daily_path']).is_file())

            paper_path = exporter.document_path(documents[0])
            content = paper_path.read_text(encoding='utf-8')
            frontmatter_text = content.split('---', 2)[1]
            frontmatter = yaml.safe_load(frontmatter_text)
            self.assertEqual(frontmatter['source_type'], 'paper')
            self.assertEqual(frontmatter['priority'], 'high')
            self.assertEqual(frontmatter['published_at'], '2026-07-01')
            self.assertEqual(frontmatter['related_topics'], ['虚拟电厂'])
            self.assertIn('[中国虚拟电厂政策](../policies/', content)
            self.assertNotIn('[[', content)

            daily = Path(result['daily_path']).read_text(encoding='utf-8')
            self.assertIn('## papers', daily)
            self.assertIn('## policies', daily)
            self.assertIn('../papers/', daily)

    def test_weekly_index_and_windows_safe_filename(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            exporter = ObsidianExporter({
                'outputs': {'obsidian': {'vault_path': temp_dir}}
            })
            weekly_path = exporter.export_weekly(_documents(), '2026-W29')

            self.assertTrue(Path(weekly_path).is_file())
            self.assertEqual(safe_filename('政策：源/网*荷?储'), '政策-源-网-荷-储')


def _documents():
    shared = {
        'summary': '摘要',
        'tags': ['虚拟电厂'],
        'themes': ['能源系统'],
        'published_at': '2026-07-01',
        'reading_suggestion': {
            'why_relevant': '与能源具身智能相关',
            'read_priority': 'high',
            'recommended_action': '精读',
            'related_topics': ['虚拟电厂'],
        },
    }
    policy = {
        **shared,
        'id': 'policy-1',
        'source_type': 'policy',
        'source_name': '国家能源局',
        'title': '中国虚拟电厂政策',
        'url': 'https://www.nea.gov.cn/policy-1',
    }
    paper = {
        **shared,
        'id': 'paper-1',
        'source_type': 'paper',
        'source_name': 'arXiv',
        'title': 'Energy Agent Paper',
        'url': 'https://arxiv.org/abs/2607.00001',
        'related_documents': [{
            'id': 'policy-1',
            'source_type': 'policy',
            'title': '中国虚拟电厂政策',
            'url': policy['url'],
            'relationship': 'paper_policy',
            'reason': '共享标签：虚拟电厂',
        }],
    }
    return [
        paper,
        policy,
        {**shared, 'id': 'news-1', 'source_type': 'news', 'source_name': '人民网', 'title': '国内能源新闻'},
        {**shared, 'id': 'report-1', 'source_type': 'industry_report', 'source_name': '中国电力企业联合会', 'title': '能源行业报告'},
    ]


if __name__ == '__main__':
    unittest.main()
