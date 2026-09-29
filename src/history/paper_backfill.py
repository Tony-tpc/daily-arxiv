"""Monthly paper discovery with a shared request budget and durable coverage."""
from __future__ import annotations
import copy
import hashlib
import json
from datetime import date, timedelta
from src.academic_library import PaperLibrary
from src.sources.academic import INDEX_SOURCES, atomic_json, read_json
from src.sources.registry import build_source_registry


def month_ranges(start: date, end: date):
    if start > end:
        raise ValueError('date_from must not exceed date_to')
    current = start
    while current <= end:
        following = (current.replace(day=28) + timedelta(days=4)).replace(day=1)
        yield current.isoformat(), min(end, following - timedelta(days=1)).isoformat()
        current = following


class PaperBackfillService:
    def __init__(self, config: dict):
        self.config = copy.deepcopy(config)
        self.library = PaperLibrary(config)

    def run(self, date_from: str, date_to: str, *, sources=None, max_requests=120,
            force=False, enrich=True) -> dict:
        selected = list(INDEX_SOURCES if sources is None else sources)
        if any(s not in INDEX_SOURCES for s in selected):
            raise ValueError('Unsupported paper source')
        periods = list(month_ranges(date.fromisoformat(date_from), date.fromisoformat(date_to)))
        if max_requests < 0:
            raise ValueError('max_requests must be nonnegative')
        coverage_path = self.library.root / 'coverage.json'
        coverage = read_json(coverage_path, {})
        registry = build_source_registry(self.config)
        adapters = {source: registry.create(source) for source in selected}
        tasks, records, failed = [], [], set()
        try:
            for source, adapter in adapters.items():
                adapter.settings['max_pages_per_run'] = 1
                query_hash = hashlib.sha256(json.dumps([vars(q) for q in adapter.queries()], sort_keys=True).encode()).hexdigest()
                for start, end in periods:
                    key = f'{source}:{start}:{end}'
                    if force or key not in coverage or coverage[key].get('query_set_hash') != query_hash:
                        coverage[key] = {'source': source, 'from': start, 'to': end,
                                         'status': 'pending', 'requests': 0, 'errors': [], 'query_set_hash': query_hash}
                    if adapter.readiness() != 'ready':
                        coverage[key].update(status='unavailable', errors=[adapter.readiness()])
                    elif coverage[key]['status'] != 'complete':
                        tasks.append((key, source, start, end))
            # Breadth first over sources and years, then progress fairly on later runs.
            calls = 0
            while calls < max_requests:
                pending = sorted((t for t in tasks if t[0] not in failed and coverage[t[0]]['status'] != 'complete'),
                    key=lambda t: (coverage[t[0]].get('requests', 0), t[2][5:7], t[2][:4], selected.index(t[1])))
                if not pending:
                    break
                key, source, start, end = pending[0]
                result = adapters[source].fetch_range(start, end, force=force and coverage[key]['requests'] == 0)
                used = result.metadata.get('requests', 0)
                calls += used
                coverage[key] = {**coverage[key], 'status': result.status, 'errors': result.errors,
                                 'requests': coverage[key].get('requests', 0) + used,
                                 'queries': result.metadata.get('queries', [])}
                records.extend(result.records)
                atomic_json(coverage_path, coverage)
                if result.errors or (used == 0 and result.status != 'complete'):
                    failed.add(key)
            report = self.library.ingest(records, enrich=enrich, coverage=coverage)
            # Reuse the historical corpus for admitted observations only.
            from src.history.backfill import HistoricalCorpus, FetchResult
            corpus = HistoricalCorpus(self.config.get('analysis', {}).get('history_directory', 'data/history'))
            papers = self.library.load()
            for start, end in periods:
                month_papers = [p for p in papers if start <= str(p.get('published_at', ''))[:10] <= end]
                states = [coverage[f'{s}:{start}:{end}']['status'] for s in selected]
                corpus.write_period('paper_library', start[:7], FetchResult(month_papers,
                    'complete' if states and all(s == 'complete' for s in states) else 'partial',
                    metadata={'from': start, 'to': end, 'sources': selected}))
            return {**report, 'requests_this_run': calls}
        finally:
            for adapter in adapters.values():
                adapter.close()
