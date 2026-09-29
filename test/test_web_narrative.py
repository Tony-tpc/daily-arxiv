"""API and rendering tests for long-form narrative views."""

from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from src.web import app as web_app


class WebNarrativeTests(unittest.TestCase):
    def setUp(self):
        web_app.app.config.update(TESTING=True)
        self.client = web_app.app.test_client()
        patcher = patch.dict(web_app.config, {'paper_discovery': {'enabled': False}})
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_cached_narrative_is_safely_rendered_without_running_analyzer(self):
        payload = _cached_payload()
        with patch.object(
            web_app, "load_json", return_value={"narrative_analysis": {"paper": payload}}
        ), patch.object(web_app, "NarrativeAnalyzer") as analyzer:
            response = self.client.get("/api/trends/narrative?view=paper")

        self.assertEqual(response.status_code, 200)
        analyzer.assert_not_called()
        data = response.get_json()
        rendered = data["sections"][0]["html"]
        self.assertNotIn("<script", rendered)
        self.assertNotIn('href="javascript:', rendered)
        self.assertIn("&lt;script&gt;", rendered)
        self.assertEqual(data["evidence_index"]["P01"]["url"], "")

    def test_cached_policy_evidence_uses_verified_https_url_and_issue_date(self):
        payload = _cached_payload()
        payload["evidence_index"]["POL01"] = {
            "title": "国家能源局政策",
            "source_type": "policy",
            "url": "http://www.nea.gov.cn/notice",
            "event_date": "2026-07-10",
            "excerpt": "目录项基本信息 制发日期: 2026-06-05 正文",
        }
        analysis = {"narrative_analysis": {"paper": payload}}
        audit = {"views": {"paper": {"evidence": {"POL01": {
            "document_id": "", "status": "verified",
            "final_url": "https://www.nea.gov.cn/notice",
        }}}}}
        with patch.object(web_app, "load_json", side_effect=[analysis, audit]):
            response = self.client.get("/api/trends/narrative?view=paper")

        evidence = response.get_json()["evidence_index"]["POL01"]
        self.assertEqual(evidence["url"], "https://www.nea.gov.cn/notice")
        self.assertEqual(evidence["event_date"], "2026-06-05")

    def test_evidence_without_a_matching_audit_is_not_clickable(self):
        payload = _cached_payload()
        payload["evidence_index"]["P01"]["url"] = "https://publisher.example/paper"
        analysis = {"narrative_analysis": {"paper": payload}}
        audit = {"views": {"paper": {"evidence": {}}}}
        with patch.object(web_app, "load_json", side_effect=[analysis, audit]):
            response = self.client.get("/api/trends/narrative?view=paper")

        evidence = response.get_json()["evidence_index"]["P01"]
        self.assertEqual(evidence["url"], "")
        self.assertEqual(evidence["link_status"], "not_audited")

    def test_cached_audit_disables_an_unverified_evidence_link(self):
        payload = _cached_payload()
        payload["view"] = "paper"
        payload["evidence_index"]["P01"]["document_id"] = "paper-1"
        payload["evidence_index"]["P01"]["url"] = "https://example.org/paper"
        analysis = {"narrative_analysis": {"paper": payload}}
        audit = {"views": {"paper": {"evidence": {"P01": {
            "document_id": "paper-1", "status": "http_404", "http_status": 404,
        }}}}}
        with patch.object(web_app, "load_json", side_effect=[analysis, audit]):
            response = self.client.get("/api/trends/narrative?view=paper")

        evidence = response.get_json()["evidence_index"]["P01"]
        self.assertEqual(evidence["url"], "")
        self.assertEqual(evidence["link_status"], "http_404")

    def test_cached_audit_disables_inconclusive_publisher_link(self):
        payload = _cached_payload()
        payload["view"] = "paper"
        payload["evidence_index"]["P01"]["document_id"] = "paper-1"
        payload["evidence_index"]["P01"]["url"] = "https://publisher.example/paper"
        analysis = {"narrative_analysis": {"paper": payload}}
        audit = {"views": {"paper": {"evidence": {"P01": {
            "document_id": "paper-1", "status": "http_403", "http_status": 403,
        }}}}}
        with patch.object(web_app, "load_json", side_effect=[analysis, audit]):
            response = self.client.get("/api/trends/narrative?view=paper")

        evidence = response.get_json()["evidence_index"]["P01"]
        self.assertEqual(evidence["url"], "")
        self.assertEqual(evidence["link_status"], "http_403")

    def test_refresh_uses_deterministic_analyzer_without_llm(self):
        corpus = Mock()
        corpus.load_observations.return_value = []
        analyzer = Mock()
        analyzer.generate_paper.return_value = _cached_payload()
        analyzer_class = Mock(return_value=analyzer)
        with patch.object(web_app, "load_json", return_value={}), \
             patch.object(web_app, "HistoricalCorpus", return_value=corpus), \
             patch.object(web_app, "_load_intelligence_documents", return_value=[]), \
             patch.object(web_app, "NarrativeAnalyzer", analyzer_class):
            response = self.client.get("/api/trends/narrative?view=paper&refresh=1")

        self.assertEqual(response.status_code, 200)
        analyzer_class.assert_called_once_with(web_app.config)
        analyzer.generate_paper.assert_called_once()
        self.assertNotIn("llm", analyzer_class.call_args.kwargs)

    def test_narrative_api_rejects_invalid_view_and_date(self):
        self.assertEqual(
            self.client.get("/api/trends/narrative?view=forecast").status_code,
            400,
        )
        self.assertEqual(
            self.client.get("/api/trends/narrative?view=paper&as_of=2026-02-31").status_code,
            400,
        )

    def test_policy_view_is_an_independent_cached_article(self):
        payload = {**_cached_payload(), 'view': 'policy', 'title': '政策分析'}
        with patch.object(web_app, '_load_current_analysis', return_value={'narrative_analysis': {'policy': payload}}):
            response = self.client.get('/api/trends/narrative?view=policy')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()['view'], 'policy')
        html = self.client.get('/').get_data(as_text=True)
        for route in ('paper-report', 'policy-analysis', 'analysis'):
            self.assertIn(f'data-section="{route}"', html)

    def test_page_uses_portable_chinese_web_font_stack(self):
        css = (
            Path(__file__).resolve().parents[1] / "static" / "css" / "style.css"
        ).read_text(encoding="utf-8")
        self.assertIn("'PingFang SC'", css)
        self.assertIn("'Microsoft YaHei'", css)
        self.assertIn("'Noto Sans CJK SC'", css)
        self.assertNotIn("font-family: SimSun", css)

    def test_coverage_ui_distinguishes_cited_evidence_from_corpus(self):
        javascript = (
            Path(__file__).resolve().parents[1] / "static" / "js" / "main.js"
        ).read_text(encoding="utf-8")
        self.assertIn("coverage.selected_evidence_count", javascript)
        self.assertIn("条引用证据", javascript)
        self.assertIn("条语料", javascript)


def _cached_payload():
    return {
        "schema_version": "1.0",
        "view": "paper",
        "as_of": "2026-07-15",
        "generated_at": "2026-07-15T09:00:00+00:00",
        "generation_status": "generated",
        "char_count": 4000,
        "coverage": {"source_counts": {"paper": 12}},
        "limitations": [],
        "sections": [{
            "id": "hotspots",
            "title": "当前研究热点",
            "markdown": "<script>alert(1)</script> [危险链接](javascript:alert(1)) 正文[P01]",
            "claims": [{"evidence_ids": ["P01"]}],
        }],
        "opportunities": [],
        "evidence_chains": [],
        "evidence_index": {
            "P01": {
                "title": "能源系统论文",
                "url": "javascript:alert(1)",
                "source_type": "paper",
            }
        },
    }


if __name__ == "__main__":
    unittest.main()
