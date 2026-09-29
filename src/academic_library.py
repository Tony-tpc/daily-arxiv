"""Durable paper corpus, metadata supplementation, admission and coverage reporting."""
from __future__ import annotations
import hashlib
import json
import re
from collections import Counter
from datetime import datetime, timezone, timedelta
from pathlib import Path

import httpx
from src.linking.deduplicator import Deduplicator
from src.sources.academic import atomic_json, read_json, record_key, clean_doi
from src.sources.paper_normalizer import normalize_paper_records, is_excluded_paper
from src.sources.paper_quality import evaluate_paper_quality


def content_hash(record: dict) -> str:
    body = {key: record.get(key) for key in ('title', 'abstract', 'raw_text', 'authors_or_orgs', 'publication_type')}
    return hashlib.sha256(json.dumps(body, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def in_research_scope(record: dict, config: dict) -> bool:
    if is_excluded_paper(record, config):
        return False
    settings = config.get('paper_discovery', {})
    if not settings.get('require_topic_match', True):
        return True
    text = ' '.join([str(record.get('title') or ''), str(record.get('abstract') or record.get('raw_text') or ''),
                     ' '.join(record.get('categories') or [])]).casefold()
    energy = settings.get('energy_terms', ['energy system', 'energy systems', 'energy management',
             'energy storage', 'energy trading', 'energy market', 'electricity', 'power system',
             'power systems', 'power grid', 'microgrid', 'microgrids', 'virtual power plant',
             'demand response', 'battery management', 'battery charging', 'state of charge',
             'photovoltaic', 'renewable energy', 'distributed energy resource', 'distributed generation',
             'smart grid', 'wind power', 'wind farm', 'solar power', 'frequency regulation',
             'energy hub', 'integrated energy', 'building energy', 'energy building', 'demand-side',
             'power market', '储能', '能源', '电力', '电网', '微电网'])
    methods = settings.get('method_terms', ['reinforcement learning', 'multi-agent', 'multiagent', 'control',
              'autonomous', 'game', 'bidding', 'mechanism', 'digital twin', 'optimization', 'optimisation',
              '强化学习', '多智能体', '控制', '博弈', '自主', '优化', '数字孪生'])
    def match(term):
        return bool(re.search(r'(?<![a-z])' + re.escape(term.casefold()) + r'(?![a-z])', text))
    return any(match(t) for t in energy) and any(match(t) for t in methods)


class PaperLibrary:
    """Raw records survive rejection and are re-evaluated when evidence changes."""
    def __init__(self, config: dict):
        self.config = config
        self.settings = config.get('paper_discovery', {})
        self.root = Path(self.settings.get('library_directory', 'data/library'))
        self.raw_path = self.root / 'records.json'
        self.admitted_path = self.root / 'admitted.json'

    def load(self) -> list[dict]:
        papers = read_json(self.admitted_path, {}).get('papers', [])
        verified = [{**p, 'quality_gate': evaluate_paper_quality(p, self.config)} for p in papers]
        return [p for p in verified if p['quality_gate']['allowed'] and in_research_scope(p, self.config)]

    def state_token(self) -> str:
        """Invalidate derived reports when admissions or partition evidence change."""
        from src.sources.paper_quality import venue_evidence
        state = {'library': read_json(self.admitted_path, {}).get('updated_at'),
                 'evidence': venue_evidence(self.config)}
        return hashlib.sha256(json.dumps(state, sort_keys=True, ensure_ascii=False).encode()).hexdigest()

    def ingest(self, records: list[dict], *, enrich: bool = True, coverage: dict | None = None) -> dict:
        raw = read_json(self.raw_path, {}).get('records', [])
        indexed = {(r.get('source_record_provider') or r.get('source_name', ''), str(r.get('id'))): r for r in raw}
        for record in records:
            provider = record.get('source_record_provider') or record.get('source_name', '')
            indexed[(provider, str(record.get('id')))] = {**indexed.get((provider, str(record.get('id'))), {}), **record}
        raw = list(indexed.values())
        # Persist first, even when network enrichment or downstream processing fails.
        atomic_json(self.raw_path, {'records': raw})
        normalized, normalization_errors = [], []
        for record in raw:
            try:
                normalized.extend(normalize_paper_records([record], record.get('source_record_provider', 'institution_import'),
                                                         self.config, enforce_quality=False))
            except (ValueError, TypeError) as exc:
                normalization_errors.append({'id': record.get('id'), 'error': type(exc).__name__})
        linker = Deduplicator(self.config)
        unique, _ = linker.deduplicate(normalized)
        cached_metadata = read_json(self.root / 'enrichment.json', {})
        unique = [merge_metadata(r, cached_metadata[clean_doi(r.get('doi'))]['record'])
                  if clean_doi(r.get('doi')) in cached_metadata else r for r in unique]
        enrichment_errors = []
        if enrich and self.settings.get('enrichment', {}).get('enabled', False):
            unique, enrichment_errors = self.enrich(unique)
        summaries = read_json(self.root / 'summaries.json', {})
        admitted, rejected = [], Counter()
        journal_gaps = Counter()
        for record in unique:
            if not in_research_scope(record, self.config):
                rejected['outside_research_scope'] += 1
                continue
            decision = evaluate_paper_quality(record, self.config)
            record['quality_gate'] = decision
            if not decision['allowed']:
                rejected[decision['reason']] += 1
                if decision['reason'] == 'cas_partition_unverified':
                    journal_gaps[record.get('journal_name') or 'unknown'] += 1
                continue
            record['id'] = 'paper_' + hashlib.sha256(record_key(record).encode()).hexdigest()[:24]
            record['abstract_status'] = 'available' if record.get('abstract') or record.get('raw_text') else 'missing'
            fingerprint = content_hash(record)
            cached = summaries.get(record['id'], {})
            if cached.get('summary_content_hash') == fingerprint and not cached.get('summary_error'):
                record.update(cached)
            admitted.append(record)
        timestamp = datetime.now(timezone.utc).isoformat()
        atomic_json(self.admitted_path, {'papers': admitted, 'updated_at': timestamp})
        known_coverage = read_json(self.root / 'coverage.json', {})
        known_coverage.update(coverage or {})
        atomic_json(self.root / 'coverage.json', known_coverage)
        from src.sources.academic import INDEX_SOURCES
        sources = sorted(set(INDEX_SOURCES) | {r.get('source_record_provider') or r.get('source_name') or 'unknown' for r in raw})
        source_counts = {}
        for source in sources:
            source_counts[source] = {
                'raw_count': sum((r.get('source_record_provider') or r.get('source_name')) == source for r in raw),
                'unique_contribution': sum(r.get('discovered_via') == [source] for r in unique),
                'admitted_contribution': sum(source in r.get('discovered_via', []) for r in admitted),
            }
        abstract_count = sum(p['abstract_status'] == 'available' for p in admitted)
        report = {'updated_at': timestamp, 'raw_count': len(raw), 'unique_count': len(unique),
            'admitted_count': len(admitted), 'abstract_count': abstract_count,
            'normalization_errors': normalization_errors, 'normalization_filtered_count': len(raw) - len(normalized),
            'abstract_completeness': abstract_count / len(admitted) if admitted else None,
            'sources': source_counts, 'rejection_reasons': dict(rejected),
            'unavailable_sources': sorted({v.get('source') or k.split(':')[-1] for k, v in known_coverage.items()
                if v.get('status') == 'unavailable' and any('missing_api_key' in str(e) for e in v.get('errors', []))}),
            'unverified_journals': journal_gaps.most_common(100), 'enrichment_errors': enrichment_errors,
            'years': dict(sorted(Counter(str(p.get('published_at', ''))[:4] for p in admitted).items())),
            'topics': dict(Counter(t for p in admitted for t in p.get('categories', [])).most_common(30)),
            'cas_editions': sorted({p.get('quality_gate', {}).get('edition_year') for p in admitted if p.get('quality_gate', {}).get('edition_year')}),
            'coverage': known_coverage,
            'incomplete_partitions': [k for k, v in known_coverage.items() if v.get('status') != 'complete']}
        atomic_json(self.root / 'quality_report.json', report)
        self._write_report(report)
        return report

    def enrich(self, records: list[dict]) -> tuple[list[dict], list[str]]:
        from src.sources.openalex_search_adapter import OpenAlexSearchAdapter
        from src.sources.crossref_adapter import CrossrefAdapter
        cache_path = self.root / 'enrichment.json'
        cache = read_json(cache_path, {})
        budget = int(self.settings.get('enrichment', {}).get('max_records_per_run', 100))
        clients = [CrossrefAdapter(self.config), OpenAlexSearchAdapter(self.config)]
        errors = []
        output = []
        try:
            prioritized = sorted(records, key=lambda r: (cache.get(clean_doi(r.get('doi')), {}).get('checked_at', ''),
                not (in_research_scope(r, self.config) and evaluate_paper_quality(r, self.config)['allowed']),
                not in_research_scope(r, self.config)))
            for original in prioritized:
                record = dict(original)
                doi = clean_doi(record.get('doi'))
                if not doi:
                    output.append(record)
                    continue
                cached = cache.get(doi)
                if cached:
                    record = merge_metadata(record, cached['record'])
                needs = not (record.get('abstract') or record.get('raw_text')) or not record.get('journal_name') or not record.get('publication_type')
                recent = cached and datetime.fromisoformat(cached['checked_at']) > datetime.now(timezone.utc) - timedelta(days=7)
                if needs and not recent and budget > 0:
                    budget -= 1
                    success = True
                    for client in clients:
                        try:
                            extra = client.lookup('doi:' + doi if client.source_name == 'openalex_search' else doi)
                            record = merge_metadata(record, extra)
                        except (httpx.HTTPError, ValueError, KeyError) as exc:
                            code = exc.response.status_code if isinstance(exc, httpx.HTTPStatusError) else type(exc).__name__
                            if code != 404:
                                success = False
                                errors.append(f'{client.source_name}:{code}')
                    cache[doi] = {'record': record, 'checked_at': datetime.now(timezone.utc).isoformat(), 'success': success}
                    atomic_json(cache_path, cache)
                output.append(record)
        finally:
            for client in clients:
                client.close()
        return output, errors

    def save_summaries(self, papers: list[dict]) -> None:
        cache = read_json(self.root / 'summaries.json', {})
        fields = ('summary', 'core_viewpoints', 'research_relevance', 'worth_reading', 'follow_up_suggestions',
                  'summarized_at', 'summary_content_hash', 'summary_error', 'summary_status', 'web_card')
        for paper in papers:
            if paper.get('source_type') == 'paper' and paper.get('summary_content_hash'):
                cache[paper['id']] = {k: paper[k] for k in fields if k in paper}
        atomic_json(self.root / 'summaries.json', cache)
        current = {p['id']: p for p in self.load()}
        current.update({p['id']: p for p in papers if p.get('source_type') == 'paper' and p['id'] in current})
        atomic_json(self.admitted_path, {'papers': list(current.values()), 'updated_at': datetime.now(timezone.utc).isoformat()})

    def _write_report(self, report: dict) -> None:
        lines = ['# 论文采集质量报告', '', f"生成时间：{report['updated_at']}", '',
                 f"原始记录 {report['raw_count']}；去重后 {report['unique_count']}；合格论文 {report['admitted_count']}；有摘要 {report['abstract_count']}。", '',
                 '| 渠道 | 原始记录 | 独有论文 | 合格论文贡献 |', '|---|---:|---:|---:|']
        for source, values in report['sources'].items():
            lines.append(f"| {source} | {values['raw_count']} | {values['unique_contribution']} | {values['admitted_contribution']} |")
        lines += ['', '拒收原因：' + json.dumps(report['rejection_reasons'], ensure_ascii=False), '',
                  '年份覆盖：' + json.dumps(report['years'], ensure_ascii=False), '',
                  '主题覆盖：' + json.dumps(report['topics'], ensure_ascii=False), '',
                  '尚缺分区证据的期刊：' + json.dumps(report['unverified_journals'], ensure_ascii=False), '',
                  '不可用来源：' + json.dumps(report['unavailable_sources'], ensure_ascii=False), '',
                  '补证错误：' + json.dumps(report['enrichment_errors'], ensure_ascii=False), '',
                  f"未完成分片：{len(report['incomplete_partitions'])}（详见同目录 quality_report.json）。",
                  '', '数量按唯一论文统计；渠道贡献可重叠。采集完整性与分区准入分别记录。']
        (self.root / 'quality_report.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')


def merge_metadata(record: dict, extra: dict) -> dict:
    """Merge only identity-confirmed metadata; retain original provider attribution."""
    if clean_doi(record.get('doi')) != clean_doi(extra.get('doi')):
        return record
    merged = dict(record)
    for key, value in extra.items():
        if key not in {'id', 'source_name', 'source_record_provider', 'field_sources'} and not merged.get(key) and value:
            merged[key] = value
    merged['is_retracted'] = bool(record.get('is_retracted') or extra.get('is_retracted'))
    if extra.get('publication_type') in {'review', 'editorial', 'retraction', 'correction'} or (extra.get('publication_type') in {'article', 'journal-article'} and extra.get('journal_name') and record.get('publication_type') in {'', None, 'preprint'}):
        merged['publication_type'] = extra['publication_type']
    merged['raw_text'] = merged.get('abstract') or merged.get('raw_text', '')
    provenance = dict(merged.get('field_sources') or {})
    for field, source in extra.get('field_sources', {}).items():
        source_key = 'journal_name' if field == 'journal' else field
        if not record.get(source_key) and extra.get(source_key):
            provenance[field] = source
    merged['field_sources'] = provenance
    return merged
