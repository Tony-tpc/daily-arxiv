"""Tests for the post-analysis evidence link-audit stage."""

import logging
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.pipeline.context import create_pipeline_context
from src.pipeline import link_audit_stage


class LinkAuditStageTests(unittest.TestCase):
    def setUp(self):
        self.context = create_pipeline_context(
            {"verification": {"evidence_links": {"enabled": True}}},
            logging.getLogger("test.link-audit-stage"),
            lambda zh, en: zh,
        )

    def test_stage_runs_audit_after_an_analysis_artifact_exists(self):
        with tempfile.TemporaryDirectory() as directory:
            analysis_path = Path(directory) / "analysis.json"
            cache_path = Path(directory) / "audit.json"
            analysis_path.write_text("{}", encoding="utf-8")
            self.context.config["verification"]["evidence_links"].update({
                "analysis_path": str(analysis_path),
                "cache_path": str(cache_path),
                "request_timeout_seconds": 5,
                "max_workers": 2,
            })
            with patch(
                "src.pipeline.link_audit_stage.audit_analysis_file",
                return_value={"views": {"paper": {}}},
            ) as audit:
                result = link_audit_stage.run(self.context)

        self.assertIs(result, self.context)
        audit.assert_called_once_with(
            str(analysis_path), str(cache_path), timeout_seconds=5.0, max_workers=2,
        )
        self.assertEqual(self.context.artifacts["evidence_link_audit"], str(cache_path))

    def test_stage_skips_when_analysis_artifact_is_absent(self):
        self.context.config["verification"]["evidence_links"]["analysis_path"] = "missing.json"
        with patch("src.pipeline.link_audit_stage.audit_analysis_file") as audit:
            link_audit_stage.run(self.context)

        audit.assert_not_called()
