"""Admission, import, enrichment and checkpoint regression contracts."""
import copy
import json
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import Mock, patch

import httpx
from src.academic_library import PaperLibrary, content_hash, merge_metadata
from src.history.paper_backfill import PaperBackfillService, month_ranges
from src.linking.deduplicator import Deduplicator
from src.sources.academic import PaperFetchResult, publication_in_range
from src.sources.institution_import import read_export, publication_type
from src.sources.openaire_adapter import OpenAIREAdapter
from src.sources.semantic_scholar_adapter import SemanticScholarAdapter
from src.sources.paper_quality import evaluate_paper_quality
from src.summarizer.document_summarizer import DocumentSummarizer
from test.test_paper_quality import QUALITY_CONFIG


def paper(**changes):
    return {'id': 'a', 'source_type': 'paper', 'source_name': 'OpenAlex',
            'source_record_provider': 'openalex_search', 'doi': '10.1000/a',
            'title': 'Multi-agent energy system control', 'authors': ['Alice'],
            'published': '2020-01-03', 'publication_type': 'article',
            'journal_name': 'IEEE Transactions on Smart Grid', 'journal_issn_l': '1949-3053',
            **changes}


class AcademicLibraryTests(unittest.TestCase):
    def test_crossref_null_date_components_preserve_valid_precision(self):
        from src.sources.crossref_adapter import publication_date
        self.assertEqual(publication_date({'published': {'date-parts': [[2025, None, None]]}}), '2025')
        self.assertEqual(publication_date({'published': {'date-parts': [[None]]},
            'issued': {'date-parts': [[2024, 2, 29]]}}), '2024-02-29')
        self.assertEqual(publication_date({'published': {'date-parts': []},
            'issued': {'date-parts': [[2025, 2, 30]]}}), '2025-02')
        self.assertEqual(publication_date({'published': {'date-parts': [None]}}), '')

    def test_secondary_export_types_cannot_hide_reviews_or_conferences(self):
        self.assertEqual(publication_type('Article; Early Access'), 'journal-article')
        self.assertEqual(publication_type('Article; Proceedings Paper'), 'proceedings-article')
        self.assertEqual(publication_type('JOUR; Review'), 'review')
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.config = copy.deepcopy(QUALITY_CONFIG)
        self.config['paper_discovery'] = {'enabled': True, 'library_directory': self.temp.name,
            'checkpoint_directory': str(Path(self.temp.name) / 'checkpoints'),
            'enrichment': {'enabled': False}}
        self.config['analysis'] = {'history_directory': str(Path(self.temp.name) / 'history')}

    def test_cross_source_supplementation_precedes_admission(self):
        library = PaperLibrary(self.config)
        incomplete = paper(publication_type='', journal_name='', journal_issn_l='', abstract='Energy control results')
        self.assertEqual(library.ingest([incomplete])['admitted_count'], 0)
        complete = paper(id='b', source_record_provider='crossref', source_name='Crossref')
        report = library.ingest([complete])
        self.assertEqual((report['raw_count'], report['unique_count'], report['admitted_count']), (2, 1, 1))
        admitted = library.load()[0]
        self.assertEqual(admitted['abstract'], incomplete['abstract'])
        self.assertEqual(set(admitted['discovered_via']), {'openalex_search', 'crossref'})

    def test_raw_survives_enrichment_failure(self):
        self.config['paper_discovery']['enrichment']['enabled'] = True
        library = PaperLibrary(self.config)
        with patch.object(library, 'enrich', side_effect=RuntimeError('network')):
            with self.assertRaises(RuntimeError):
                library.ingest([paper()])
        self.assertEqual(len(json.loads(library.raw_path.read_text())['records']), 1)

    def test_metadata_cache_survives_a_later_no_enrich_run(self):
        library = PaperLibrary(self.config)
        library.ingest([paper()])
        (library.root / 'enrichment.json').write_text(json.dumps({'10.1000/a': {
            'record': paper(abstract='Previously supplemented abstract'),
            'checked_at': '2026-09-29T00:00:00+00:00'}}), encoding='utf-8')
        library.ingest([], enrich=False)
        self.assertEqual(library.load()[0]['abstract'], 'Previously supplemented abstract')

    def test_missing_cas_evidence_and_review_remain_outside_library(self):
        records = [paper(id='a', doi='10.1000/a', publication_type='review'),
                   paper(id='b', doi='10.1000/b', is_retracted=True),
                   paper(id='c', doi='10.1000/c', journal_issn_l='0000-0000')]
        report = PaperLibrary(self.config).ingest(records)
        self.assertEqual(report['admitted_count'], 0)
        self.assertEqual(report['rejection_reasons'], {'not_original_research': 1, 'retracted': 1, 'cas_partition_unverified': 1})
        del self.config['paper_quality']['approved_venues'][0]['edition_year']
        self.assertFalse(evaluate_paper_quality(paper(), self.config)['allowed'])

    def test_review_evidence_survives_publisher_type_merge(self):
        records = [paper(publication_type='review'), paper(id='b', source_record_provider='crossref', publication_type='journal-article')]
        self.assertEqual(PaperLibrary(self.config).ingest(records)['admitted_count'], 0)

    def test_abstract_review_and_generic_radio_energy_do_not_qualify(self):
        library = PaperLibrary(self.config)
        report = library.ingest([paper(abstract='This paper presents a comprehensive review of energy systems.'),
            paper(id='radio', doi='10.1000/radio', title='Energy-efficient radio resource control',
                  abstract='Reinforcement learning optimizes wireless data transmission energy.',
                  categories=['Smart Grid and Power Systems']),
            paper(id='brief', doi='10.1000/brief', title='Advances in energy system control',
                  abstract='This article provides a brief review of distributed control.')])
        self.assertEqual(report['admitted_count'], 0)
        self.assertEqual(report['rejection_reasons']['outside_research_scope'], 1)
        self.assertEqual(report['rejection_reasons']['not_original_research'], 2)

    def test_different_dois_cannot_merge_through_title_or_bridge(self):
        records = [paper(), paper(id='bridge', doi=''), paper(id='other', doi='10.1000/b')]
        unique, _ = Deduplicator(self.config).deduplicate(records)
        self.assertEqual(len(unique), 2)
        self.assertEqual({r['doi'] for r in unique}, {'10.1000/a', '10.1000/b'})

    def test_no_doi_identity_requires_author_and_year(self):
        records = [paper(id='a', doi=''), paper(id='b', doi='', authors=['Bob']),
                   paper(id='c', doi='', published='2021')]
        self.assertEqual(len(Deduplicator(self.config).deduplicate(records)[0]), 3)

    def test_metadata_merge_checks_doi_and_formal_version(self):
        original = paper(publication_type='preprint', journal_name='', journal_issn_l='')
        self.assertEqual(merge_metadata(original, paper(doi='10.1000/b')), original)
        self.assertEqual(merge_metadata(original, paper())['publication_type'], 'article')

    def test_summary_is_reused_only_for_unchanged_content(self):
        library = PaperLibrary(self.config)
        library.ingest([paper(abstract='First abstract')])
        admitted = library.load()[0]
        admitted.update(summary='Summary', summarized_at='2025-01-01', summary_content_hash=content_hash(admitted))
        library.save_summaries([admitted])
        library.ingest([])
        self.assertEqual(library.load()[0]['summary'], 'Summary')
        library.ingest([paper(abstract='Changed abstract')])
        self.assertNotEqual(library.load()[0].get('summary'), 'Summary')

    def test_missing_abstract_never_calls_llm(self):
        client = Mock()
        result = DocumentSummarizer(self.config, client).summarize_document(paper(summary='Old unsupported summary'))
        client.generate.assert_not_called()
        self.assertEqual(result['summary_status'], 'missing_abstract')
        self.assertEqual(result['core_viewpoints'], [])

    def test_all_institutional_formats_are_idempotent(self):
        fixtures = {
            'sample.ris': 'TY  - JOUR\nTI  - Multi-agent energy system control\nDO  - 10.1000/a\nJO  - IEEE Transactions on Smart Grid\nSN  - 1949-3053\nPY  - 2020\nAU  - Alice\nAB  - Energy control results\nER  -\n',
            'sample.bib': '@article{a, title={Multi-agent energy system control}, doi={10.1000/a}, journal={IEEE Transactions on Smart Grid}, issn={1949-3053}, year={2020}, author={Alice}, abstract={Energy control results}}',
            'sample.csv': 'Title,DOI,Source title,ISSN,Year,Document Type,Authors,Abstract\nMulti-agent energy system control,10.1000/a,IEEE Transactions on Smart Grid,1949-3053,2020,Article,Alice,Energy control results\n',
            'sample.txt': 'FN Clarivate\nPT J\nTI Multi-agent energy system control\nSO IEEE Transactions on Smart Grid\nSN 1949-3053\nDI 10.1000/a\nPY 2020\nDT Article\nAU Alice\nAB Energy control results\nER\nEF\n'}
        library = PaperLibrary(self.config)
        for filename, body in fixtures.items():
            path = Path(self.temp.name) / filename
            path.write_text(body, encoding='utf-8')
            records = read_export(path, 'Institution database')
            self.assertEqual(records[0]['doi'], '10.1000/a')
            library.ingest(records)
            report = library.ingest(records)
            self.assertEqual(report['admitted_count'], 1)
        self.assertEqual(report['raw_count'], 4)
        self.assertEqual(report['unique_count'], 1)

    def test_month_boundaries_and_partial_publication_dates(self):
        self.assertEqual(list(month_ranges(date(2020, 2, 28), date(2020, 3, 1))),
                         [('2020-02-28', '2020-02-29'), ('2020-03-01', '2020-03-01')])
        for published, expected in [('2020', True), ('2020-02-29', True), ('2020-03-01', False), ('', False)]:
            self.assertEqual(publication_in_range({'published': published}, '2020-02-01', '2020-02-29'), expected)

    def test_history_budget_and_resume_never_claim_partial_complete(self):
        adapter = Mock()
        adapter.settings = {}
        adapter.queries.return_value = []
        adapter.readiness.return_value = 'ready'
        adapter.fetch_range.side_effect = [PaperFetchResult([paper()], 'partial', metadata={'requests': 1}),
                                          PaperFetchResult([paper()], 'complete', metadata={'requests': 1})]
        registry = Mock()
        registry.create.return_value = adapter
        with patch('src.history.paper_backfill.build_source_registry', return_value=registry):
            service = PaperBackfillService(self.config)
            first = service.run('2020-01-01', '2020-01-31', sources=['openalex_search'], max_requests=1)
            self.assertEqual(len(first['incomplete_partitions']), 1)
            second = service.run('2020-01-01', '2020-01-31', sources=['openalex_search'], max_requests=1)
            self.assertEqual(second['incomplete_partitions'], [])
            third = service.run('2020-01-01', '2020-01-31', sources=['openalex_search'], max_requests=1)
            self.assertEqual(third['requests_this_run'], 0)

    def test_openaire_and_semantic_scholar_metadata(self):
        record = OpenAIREAdapter.work_to_record({'id': '1', 'mainTitle': 'Energy control', 'pids': None,
            'descriptions': ['An abstract'], 'container': None, 'instances': [{'type': 'Review', 'urls': []}]})
        self.assertEqual(record['publication_type'], 'review')
        record = SemanticScholarAdapter.work_to_record({'paperId': 'x', 'title': 'Energy control',
            'publicationTypes': ['JournalArticle', 'Review'], 'externalIds': {'DOI': '10.1000/A'}})
        self.assertEqual(record['publication_type'], 'review')
        self.assertEqual(record['doi'], '10.1000/a')
        with patch.dict('os.environ', {'SEMANTIC_SCHOLAR_API_KEY': ''}):
            adapter = SemanticScholarAdapter(self.config)
            self.addCleanup(adapter.close)
            result = adapter.fetch_range('2020-01-01', '2020-01-31')
            self.assertEqual(result.status, 'unavailable')
            self.assertIn('missing_api_key', result.errors[0])

    def test_web_reads_cumulative_library_and_quality_report(self):
        from src.web import app as web
        PaperLibrary(self.config).ingest([paper(abstract='Energy control results')])
        with patch.object(web, 'config', self.config):
            client = web.app.test_client()
            payload = client.get('/api/papers?per_page=1').get_json()
            self.assertEqual(payload['total'], 1)
            self.assertEqual(payload['papers'][0]['quality_gate']['edition_year'], 2025)
            self.assertEqual(client.get('/api/papers/quality').get_json()['abstract_completeness'], 1.0)

    def test_old_analysis_cannot_bypass_new_admission_evidence(self):
        from src.web import app as web
        with patch.object(web, 'config', self.config), patch.object(web, 'load_json', return_value={'paper_count': 99}):
            self.assertEqual(web._load_current_analysis(), {})

    def test_reference_traversal_resumes_to_two_levels(self):
        from src.history.citations import trace_citations
        library = PaperLibrary(self.config)
        library.ingest([paper(openalex_id='https://openalex.org/W0')])
        self.config['paper_discovery']['citations'] = {'reference_depth': 2, 'citing_depth': 0}
        def lookup(identifier):
            number = int(identifier[-1])
            return paper(id=identifier, doi=f'10.1000/ref{number}',
                         journal_issn_l='9999-9999', references=[f'https://openalex.org/W{number+1}'])
        with patch('src.history.citations.OpenAlexSearchAdapter') as adapter_class, \
             patch('src.history.citations.SemanticScholarAdapter') as semantic:
            semantic.return_value.readiness.return_value = 'missing_api_key'
            adapter_class.return_value.lookup.side_effect = lookup
            trace_citations(self.config, max_requests=1)
            progress = json.loads((library.root / 'citation_progress.json').read_text())
            self.assertEqual(progress['queue'][0]['depth'], 1)
            trace_citations(self.config, max_requests=10)
            self.assertEqual(adapter_class.return_value.lookup.call_count, 3)
            self.assertEqual(library.load()[0]['doi'], '10.1000/a')
            self.assertEqual(len(library.load()), 1)

    def test_openaire_cursor_and_semantic_bulk_token(self):
        for adapter_type, source, payloads in [
            (OpenAIREAdapter, 'openaire', [
                {'results': [{'id': 'a', 'mainTitle': 'Energy control', 'publicationDate': '2020-01-01'}],
                 'header': {'nextCursor': 'next'}}, {'results': [], 'header': {}}]),
            (SemanticScholarAdapter, 'semantic_scholar', [
                {'data': [{'paperId': 'b', 'title': 'Energy control', 'year': 2020}], 'token': 'next'}, {'data': []}])]:
            calls = []
            config = copy.deepcopy(self.config)
            config['sources'] = {source: {'api_key': 'test', 'search_terms': ['energy'],
                'max_pages_per_run': 2, 'request_interval_seconds': 0}}
            adapter = adapter_type(config)
            adapter.client.close()
            def handler(request):
                calls.append(dict(request.url.params))
                return httpx.Response(200, json=payloads.pop(0))
            adapter.client = httpx.Client(transport=httpx.MockTransport(handler))
            result = adapter.fetch_range('2020-01-01', '2020-01-31')
            adapter.close()
            self.assertEqual(result.status, 'complete')
            self.assertEqual(len(result.records), 1)
            self.assertEqual(calls[1].get('cursor') or calls[1].get('token'), 'next')
