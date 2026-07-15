"""Tests for cache-safe visual assets used by the web dashboard."""

import unittest
from unittest.mock import patch

from src.web import app as web_app


class WebVisualAssetTests(unittest.TestCase):
    def setUp(self):
        web_app.app.config.update(TESTING=True)
        self.client = web_app.app.test_client()

    def test_wordcloud_url_uses_file_version_to_avoid_stale_fonts(self):
        analysis = {
            'wordcloud_path': 'data/analysis/wordcloud_2026-07-15.png',
            'generated_at': '2026-07-15T08:00:00',
        }
        with patch.object(web_app, 'load_json', return_value=analysis), patch(
            'src.web.app.os.path.getmtime', return_value=123.5
        ):
            response = self.client.get('/api/wordcloud')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.get_json()['url'],
            '/images/wordcloud_2026-07-15.png?v=123500000000',
        )


if __name__ == '__main__':
    unittest.main()
