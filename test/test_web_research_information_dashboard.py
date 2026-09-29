"""Tests for the unified multi-source research-information dashboard."""

import unittest
from unittest.mock import patch

from src.web import app as web_app


class WebResearchInformationDashboardTests(unittest.TestCase):
    def setUp(self):
        web_app.app.config.update(TESTING=True)
        self.client = web_app.app.test_client()

    def test_home_exposes_reading_filters_and_three_trend_views(self):
        response = self.client.get('/')
        html = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        for element_id in (
            'today-recommendations', 'home-source-filter', 'home-topic-filter',
            'home-priority-filter', 'home-date-from', 'home-date-to',
            'trend-chart', 'source-comparison-chart', 'entity-trend-chart',
            'narrative-content', 'narrative-opportunities', 'narrative-chains',
        ):
            self.assertIn(f'id="{element_id}"', html)
        self.assertIn('重点信息', html)
        self.assertIn('多源信息速览', html)

    def test_unified_api_filters_source_topic_priority_and_date(self):
        documents = [
            {
                'id': 'policy-current', 'source_type': 'policy',
                'source_name': '国家能源局', 'issuing_body': '国家能源局',
                'title': '虚拟电厂参与需求响应政策',
                'raw_text': '推动储能系统参与能源管理。',
                'published_at': '2026-07-10', 'policy_strength': 'high',
                'policy_level': 'national', 'region': 'CN',
                'tags': ['虚拟电厂'], 'url': 'https://www.nea.gov.cn/current',
            },
            {
                'id': 'policy-old', 'source_type': 'policy',
                'source_name': '地方部门', 'title': '虚拟电厂旧政策',
                'published_at': '2025-01-01', 'tags': ['虚拟电厂'],
            },
            {
                'id': 'paper-1', 'source_type': 'paper', 'source_name': 'arXiv',
                'title': 'Virtual power plant control', 'published_at': '2026-07-12',
                'tags': ['虚拟电厂'],
            },
        ]
        with patch.object(web_app, '_load_intelligence_documents', return_value=documents):
            response = self.client.get(
                '/api/research-information?source_type=policy&topic=虚拟电厂'
                '&priority=high&date_from=2026-07-01&date_to=2026-07-14'
            )

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload['total'], 1)
        self.assertEqual(payload['documents'][0]['id'], 'policy-current')
        self.assertEqual(payload['source_counts'], {'policy': 1})
        self.assertEqual(payload['filters']['topic'], '虚拟电厂')

    def test_legacy_information_route_remains_available(self):
        with patch.object(web_app, '_load_intelligence_documents', return_value=[]):
            response = self.client.get('/api/intelligence')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()['documents'], [])

    def test_directory_api_supports_topic_and_date_range(self):
        documents = [
            {
                'id': 'news-in', 'source_type': 'news', 'source_name': '人民网',
                'media_name': '人民网', 'title': '虚拟电厂示范',
                'published_at': '2026-07-10', 'tags': ['虚拟电厂'],
            },
            {
                'id': 'news-out', 'source_type': 'news', 'source_name': '人民网',
                'media_name': '人民网', 'title': '储能项目',
                'published_at': '2026-06-01', 'tags': ['储能'],
            },
        ]
        with patch.object(web_app, '_load_intelligence_documents', return_value=documents):
            response = self.client.get(
                '/api/documents?source_type=news&topic=虚拟电厂&date_from=2026-07-01'
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual([item['id'] for item in response.get_json()['documents']], ['news-in'])


if __name__ == '__main__':
    unittest.main()
