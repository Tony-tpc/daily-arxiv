#!/usr/bin/env python3
"""Tests for top-level policy, news, and industry report directories."""

import sys
import unittest
from pathlib import Path
from unittest.mock import patch


project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.web import app as web_app


class WebDirectoryTests(unittest.TestCase):
    def setUp(self):
        web_app.app.config.update(TESTING=True)
        self.client = web_app.app.test_client()

    def test_index_exposes_three_peer_navigation_directories(self):
        response = self.client.get('/')

        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn('data-section="papers"', html)
        self.assertIn('data-section="policies"', html)
        self.assertIn('data-section="news"', html)
        self.assertIn('data-section="industry-reports"', html)
        self.assertIn('中国政策', html)
        self.assertIn('国内新闻', html)
        self.assertIn('行业报告', html)

    def test_document_directory_filters_source_type_search_and_priority(self):
        documents = [
            {
                'id': 'policy-high',
                'source_type': 'policy',
                'source_name': '国家能源局',
                'title': '虚拟电厂参与电力市场政策',
                'summary': '面向源网荷储协同。',
                'published_at': '2026-07-01',
                'url': 'https://www.nea.gov.cn/policy-high',
                'issuing_body': '国家能源局',
                'policy_level': 'national',
                'policy_strength': 'high',
                'region': 'CN',
            },
            {
                'id': 'news-1',
                'source_type': 'news',
                'source_name': '人民网',
                'title': '能源新闻',
                'media_name': '人民网',
            },
        ]

        with patch.object(web_app, '_load_intelligence_documents', return_value=documents):
            response = self.client.get(
                '/api/documents?source_type=policy&search=虚拟电厂&priority=high'
            )

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload['source_type'], 'policy')
        self.assertEqual(payload['total'], 1)
        self.assertEqual(payload['documents'][0]['id'], 'policy-high')
        self.assertEqual(payload['documents'][0]['web_card']['source_type'], 'policy')

    def test_empty_directory_is_successful_and_invalid_type_is_rejected(self):
        with patch.object(web_app, '_load_intelligence_documents', return_value=[]):
            empty = self.client.get('/api/documents?source_type=industry_report')
        invalid = self.client.get('/api/documents?source_type=robot')

        self.assertEqual(empty.status_code, 200)
        self.assertEqual(empty.get_json()['documents'], [])
        self.assertEqual(invalid.status_code, 400)


if __name__ == '__main__':
    unittest.main()
