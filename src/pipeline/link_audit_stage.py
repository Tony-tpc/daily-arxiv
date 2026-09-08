"""Persist external-link verification after the analysis artifact is written."""

from __future__ import annotations

from pathlib import Path

from .context import PipelineContext
from src.verification.evidence_link_audit import audit_analysis_file


def run(context: PipelineContext) -> PipelineContext:
    """Audit cached evidence links without placing network activity in the web request path."""
    if context.stop_requested:
        return context
    settings = context.config.get('verification', {}).get('evidence_links', {})
    if not isinstance(settings, dict) or not settings.get('enabled', True):
        return context
    analysis_path = str(settings.get('analysis_path', 'data/analysis/latest.json'))
    output_path = str(settings.get('cache_path', 'data/cache/evidence_link_audit.json'))
    if not Path(analysis_path).is_file():
        context.logger.warning(context.text(
            f"证据链接核验已跳过：未找到分析产物 {analysis_path}",
            f"Evidence-link audit skipped: analysis artifact not found at {analysis_path}",
        ))
        return context
    try:
        result = audit_analysis_file(
            analysis_path,
            output_path,
            timeout_seconds=float(settings.get('request_timeout_seconds', 15)),
            max_workers=int(settings.get('max_workers', 6)),
        )
        context.artifacts['evidence_link_audit'] = output_path
        context.logger.info(context.text(
            f"证据链接核验已完成：{len(result.get('views', {}))} 个分析视图",
            f"Evidence-link audit completed for {len(result.get('views', {}))} analysis views",
        ))
    except Exception as exc:
        context.logger.warning(context.text(
            f"证据链接核验失败，页面将保留未经核验状态：{exc}",
            f"Evidence-link audit failed; the page will retain unverified status: {exc}",
        ))
    return context
