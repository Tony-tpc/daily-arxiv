"""Persist the cumulative verified paper library before any LLM operation."""
from src.academic_library import PaperLibrary
from src.sources.academic import PAPER_SOURCES
from src.storage.base import build_storage


def run(context):
    if context.stop_requested or not context.config.get('paper_discovery', {}).get('enabled', False):
        return context
    records, coverage = [], {}
    for source, batch in context.source_records.items():
        if source not in PAPER_SOURCES:
            continue
        records.extend({**r, 'source_record_provider': source} for r in batch)
        if source == 'arxiv':
            records.extend({**r, 'source_record_provider': source} for r in context.normalized_by_source.get(source, []))
        result = getattr(context.source_adapters.get(source), 'last_fetch_result', None)
        if result is not None:
            coverage[f'incremental:{source}'] = {'status': result.status, 'errors': result.errors,
                                               **result.metadata}
    for source, error in context.source_errors.items():
        if source in PAPER_SOURCES and f'incremental:{source}' not in coverage:
            coverage[f'incremental:{source}'] = {'status': 'unavailable', 'errors': [error]}
    library = PaperLibrary(context.config)
    library.ingest(records, coverage=coverage)
    context.normalized_records = [r for r in context.normalized_records if r.get('source_type') != 'paper'] + library.load()
    context.papers = list(context.normalized_records)
    build_storage(context.config).save_snapshot(context.normalized_records)
    context.artifacts['paper_quality_report'] = str(library.root / 'quality_report.json')
    context.stop_requested = not bool(context.normalized_records)
    return context
