"""Tests for the website report reader and API."""

import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

from src.web import app as web_app
from test.test_paper_quality import QUALITY_CONFIG


class WebReportTests(unittest.TestCase):
    def setUp(self):
        web_app.app.config.update(TESTING=True)
        self.client = web_app.app.test_client()
        patcher = patch.dict(web_app.config, {**QUALITY_CONFIG, 'paper_discovery': {'enabled': False}})
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_report_reader_is_a_peer_navigation_view(self):
        response = self.client.get('/')
        html = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn('data-section="reports"', html)
        self.assertIn('id="reports-section"', html)
        self.assertIn('id="report-type"', html)
        self.assertIn('id="intelligence-report"', html)
        self.assertIn('研究报告', html)

        script = (Path(__file__).resolve().parents[1] / 'static' / 'js' / 'main.js').read_text(
            encoding='utf-8'
        )
        self.assertIn('renderReportEvidence', script)
        self.assertIn("startsWith('appendix_')", script)

    def test_latest_report_api_supports_weekly_and_rejects_invalid_type(self):
        report = {
            'report_type': 'weekly',
            'title': '中国能源具身智能研究信息周报',
            'sections': [],
        }
        with patch.object(web_app, '_load_latest_report', return_value=report):
            response = self.client.get('/api/reports/latest?report_type=weekly')
        invalid = self.client.get('/api/reports/latest?report_type=daily')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()['report_type'], 'weekly')
        self.assertEqual(invalid.status_code, 400)

    def test_latest_report_fallback_generates_read_only_preview(self):
        documents = [{
            'id': 'paper-1', 'source_type': 'paper', 'title': '能源智能体',
            'published_at': date.today().isoformat(), 'importance_score': 80,
            'publication_type': 'article',
            'journal_name': 'IEEE Transactions on Smart Grid',
            'journal_issn_l': '1949-3053',
        }]
        with patch.object(web_app, '_load_intelligence_documents', return_value=documents), \
             patch.object(web_app, 'load_json', return_value={}):
            report = web_app._load_latest_report('weekly')

        self.assertEqual(report['report_type'], 'weekly')
        self.assertEqual(report['document_count'], 1)
        self.assertEqual(
            report['sections'][0]['items'][0]['heading'], '证据覆盖与结论边界'
        )
        appendix = next(
            section for section in report['sections']
            if section['key'] == 'appendix_papers'
        )
        self.assertEqual(appendix['items'][0]['heading'], '能源智能体')


if __name__ == '__main__':
    unittest.main()
