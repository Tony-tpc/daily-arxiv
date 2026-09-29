"""Tests for cache-safe visual assets used by the web dashboard."""

import unittest
from unittest.mock import Mock, patch

from src.web import app as web_app


class WebVisualAssetTests(unittest.TestCase):
    def setUp(self):
        web_app.app.config.update(TESTING=True)
        self.client = web_app.app.test_client()
        patcher = patch.dict(web_app.config, {'paper_discovery': {'enabled': False}})
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_wordcloud_url_uses_file_version_to_avoid_stale_fonts(self):
        analysis = {
            'wordcloud_path': 'data/analysis/wordcloud_2026-07-15.png',
            'generated_at': '2026-07-15T08:00:00',
        }
        with patch.object(web_app, 'load_json', return_value=analysis), patch(
            'src.web.app.Path.stat', return_value=Mock(st_mtime_ns=123500000000)
        ):
            response = self.client.get('/api/wordcloud')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.get_json()['url'],
            '/images/wordcloud_2026-07-15.png?v=123500000000',
        )

    def test_topic_photographs_and_fallback_are_served_locally(self):
        for name in ('solar', 'wind', 'grid', 'storage', 'city', 'industry'):
            for suffix in ('', '-thumb'):
                with self.subTest(name=name, suffix=suffix):
                    with self.client.get(f'/static/images/energy/{name}{suffix}.webp') as response:
                        self.assertEqual(response.status_code, 200)
                        self.assertEqual(response.mimetype, 'image/webp')
                        self.assertEqual(response.data[8:12], b'WEBP')
        with self.client.get('/static/images/energy/placeholder.svg') as fallback:
            self.assertEqual(fallback.status_code, 200)
            self.assertEqual(fallback.mimetype, 'image/svg+xml')

    def test_self_hosted_font_and_reading_covers_load_without_image_api(self):
        with self.client.get('/static/fonts/InterVariable.woff2') as font:
            self.assertEqual(font.status_code, 200)
            self.assertEqual(font.mimetype, 'font/woff2')
            self.assertEqual(font.data[:4], b'wOF2')
        html = self.client.get('/').get_data(as_text=True)
        self.assertIn('class="overview-hero"', html)
        self.assertIn('data-energy-image', html)
        self.assertIn('fonts/InterVariable.woff2', html)
        self.assertNotIn('images.unsplash.com', html)


if __name__ == '__main__':
    unittest.main()
