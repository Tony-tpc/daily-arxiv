"""Tests for the website report reader and API."""

import unittest
from unittest.mock import patch

from src.web import app as web_app


class WebReportTests(unittest.TestCase):
    def setUp(self):
        web_app.app.config.update(TESTING=True)
        self.client = web_app.app.test_client()

    def test_report_reader_is_a_peer_navigation_view(self):
        response = self.client.get('/')
        html = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn('data-section="reports"', html)
        self.assertIn('id="reports-section"', html)
        self.assertIn('id="report-type"', html)
        self.assertIn('id="intelligence-report"', html)
        self.assertIn('情报报告', html)

    def test_latest_report_api_supports_weekly_and_rejects_invalid_type(self):
        report = {
            'report_type': 'weekly',
            'title': '中国能源具身智能研究情报周报',
            'sections': [],
        }
        with patch.object(web_app, '_load_latest_report', return_value=report):
            response = self.client.get('/api/reports/latest?report_type=weekly')
        invalid = self.client.get('/api/reports/latest?report_type=daily')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()['report_type'], 'weekly')
        self.assertEqual(invalid.status_code, 400)


if __name__ == '__main__':
    unittest.main()
