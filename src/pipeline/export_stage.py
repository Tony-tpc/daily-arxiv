"""Export stage for the stage-based daily pipeline."""

from __future__ import annotations

from pathlib import Path

from src.exporters.obsidian_exporter import ObsidianExporter
from src.integrations.zotero_client import ZoteroClient
from src.utils import get_date_string

from .context import PipelineContext


def run(context: PipelineContext) -> PipelineContext:
    """Write configured Markdown and Obsidian exports."""
    if context.stop_requested:
        return context

    if context.summary_report:
        context.logger.info(context.text("\n生成每日报告...", "\nGenerating daily report..."))
        report_path = f"data/summaries/report_{get_date_string()}.md"
        Path(report_path).parent.mkdir(parents=True, exist_ok=True)
        with open(report_path, 'w', encoding='utf-8') as handle:
            handle.write(context.summary_report)

        context.logger.info(context.text(f"📄 每日报告已保存到: {report_path}", f"📄 Daily report saved to: {report_path}"))
        context.artifacts['summary_report'] = report_path

    obsidian_config = context.config.get('outputs', {}).get('obsidian', {})
    documents = context.summarized_documents or context.normalized_records
    if obsidian_config.get('enabled', False) and documents:
        result = ObsidianExporter(context.config).export_documents(
            documents, export_date=get_date_string()
        )
        context.artifacts['obsidian_vault'] = result['vault_path']
        context.artifacts['obsidian_daily'] = result['daily_path']
        context.logger.info(context.text(
            f"📚 Obsidian 已导出 {result['count']} 条文档: {result['vault_path']}",
            f"📚 Exported {result['count']} documents to Obsidian: {result['vault_path']}",
        ))

    zotero_config = context.config.get('outputs', {}).get('zotero', {})
    if zotero_config.get('enabled', False) and documents:
        result = ZoteroClient(context.config).export_documents(documents)
        context.artifacts['zotero_csl_json'] = result['csl_json']
        context.artifacts['zotero_bibtex'] = result['bibtex']
        context.logger.info(context.text(
            f"📖 Zotero 交换文件已导出: {result['csl_json']}",
            f"📖 Zotero interchange files exported: {result['csl_json']}",
        ))
    return context
