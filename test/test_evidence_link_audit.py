"""Tests for deterministic cached-evidence link verification."""

import unittest

from src.verification.evidence_link_audit import VERIFIED, audit_evidence_index


class _Response:
    def __init__(self, status_code, url, content):
        self.status_code = status_code
        self.url = url
        self.content = content
        self.encoding = "utf-8"


class EvidenceLinkAuditTests(unittest.TestCase):
    def test_audit_accepts_matching_final_title_and_rejects_bad_links(self):
        index = {
            "POL01": {
                "document_id": "policy-1",
                "source_type": "policy",
                "title": "能源领域节能降碳行动计划",
                "url": "http://www.nea.gov.cn/policy",
            },
            "N01": {
                "document_id": "news-1",
                "source_type": "news",
                "title": "虚拟电厂建设动态",
                "url": "https://example.cn/news",
            },
            "R01": {
                "document_id": "report-1",
                "source_type": "industry_report",
                "title": "行业报告",
                "url": "javascript:alert(1)",
            },
        }

        def fetch(url):
            if "nea.gov.cn" in url:
                return _Response(
                    200,
                    "https://www.nea.gov.cn/policy",
                    b'<title>\xe8\x83\xbd\xe6\xba\x90\xe9\xa2\x86\xe5\x9f\x9f\xe8\x8a\x82\xe8\x83\xbd\xe9\x99\x8d\xe7\xa2\xb3\xe8\xa1\x8c\xe5\x8a\xa8\xe8\xae\xa1\xe5\x88\x92 - \xe5\x9b\xbd\xe5\xae\xb6\xe8\x83\xbd\xe6\xba\x90\xe5\xb1\x80</title>',
                )
            return _Response(404, url, b'<title>Not found</title>')

        result = audit_evidence_index(index, fetch=fetch)

        self.assertEqual(result["POL01"]["status"], VERIFIED)
        self.assertEqual(result["POL01"]["final_url"], "https://www.nea.gov.cn/policy")
        self.assertEqual(result["N01"]["status"], "http_404")
        self.assertEqual(result["R01"]["status"], "invalid_url")
