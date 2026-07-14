#!/usr/bin/env python3
"""Tests for the stage-based pipeline runner."""

import logging
import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch


project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.pipeline.context import create_pipeline_context
from src.pipeline.runner import run_pipeline


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.config = {
            'app': {'language': 'zh'},
            'arxiv': {
                'categories': ['cs.AI'],
                'days_back': 2,
                'fallback_days_back': 7,
            },
            'knowledge_extraction': {'enabled': True},
        }
        self.logger = logging.getLogger('test.pipeline')
        self.text = lambda zh, en: zh

    def test_run_pipeline_stops_when_fetch_requests_stop(self):
        context = create_pipeline_context(self.config, self.logger, self.text)

        with patch('importlib.import_module') as import_module:
            fetch_module = Mock(run=lambda ctx: _mark_stop(ctx))
            normalize_module = Mock(run=Mock())
            summarize_module = Mock(run=Mock())
            import_module.side_effect = [fetch_module, normalize_module, summarize_module]

            result = run_pipeline(context)

            self.assertTrue(result.stop_requested)
            normalize_module.run.assert_not_called()
            summarize_module.run.assert_not_called()

    def test_run_pipeline_executes_stages_in_order(self):
        context = create_pipeline_context(self.config, self.logger, self.text)
        calls = []

        with patch('importlib.import_module') as import_module:
            import_module.side_effect = [
                Mock(run=lambda ctx: _record(calls, 'fetch', ctx)),
                Mock(run=lambda ctx: _record(calls, 'normalize', ctx)),
                Mock(run=lambda ctx: _record(calls, 'ranking', ctx)),
                Mock(run=lambda ctx: _record(calls, 'linking', ctx)),
                Mock(run=lambda ctx: _record(calls, 'summarize', ctx)),
                Mock(run=lambda ctx: _record(calls, 'export', ctx)),
                Mock(run=lambda ctx: _record(calls, 'extract', ctx)),
                Mock(run=lambda ctx: _record(calls, 'cross_source', ctx)),
                Mock(run=lambda ctx: _record(calls, 'analyze', ctx)),
                Mock(run=lambda ctx: _record(calls, 'report', ctx)),
            ]
            run_pipeline(context)

        self.assertEqual(calls, [
            'fetch', 'normalize', 'ranking', 'linking', 'summarize', 'export',
            'extract', 'cross_source', 'analyze', 'report',
        ])

    def test_fetch_stage_retries_with_fallback_window(self):
        context = create_pipeline_context(self.config, self.logger, self.text)
        adapter = Mock()
        adapter.source_config = {'days_back': 2, 'fallback_days_back': 7}
        adapter.fetch.side_effect = [[], [{'id': 'paper-1'}]]
        adapter.validate.return_value = None
        adapter.print_summary.return_value = None
        registry = Mock()
        registry.get_enabled_sources.return_value = ['arxiv']
        registry.create.return_value = adapter

        with patch('importlib.import_module') as import_module:
            import_module.return_value = Mock(build_source_registry=Mock(return_value=registry))
            from src.pipeline import fetch_stage
            fetch_stage.run(context)

        self.assertEqual(adapter.fetch.call_args_list[0].kwargs['days_back'], 2)
        self.assertEqual(adapter.fetch.call_args_list[1].kwargs['days_back'], 7)
        self.assertEqual(context.papers, [{'id': 'paper-1'}])

    def test_fetch_stage_collects_every_enabled_source(self):
        context = create_pipeline_context(self.config, self.logger, self.text)
        paper_adapter = Mock(source_config={})
        paper_adapter.fetch.return_value = [{'id': 'paper-1'}]
        policy_adapter = Mock(source_config={})
        policy_adapter.fetch.return_value = [{'id': 'policy-1'}]
        registry = Mock()
        registry.get_enabled_sources.return_value = ['openalex_search', 'policy']
        registry.create.side_effect = lambda name: {
            'openalex_search': paper_adapter,
            'policy': policy_adapter,
        }[name]

        with patch('importlib.import_module') as import_module:
            import_module.return_value = Mock(build_source_registry=Mock(return_value=registry))
            from src.pipeline import fetch_stage
            fetch_stage.run(context)

        self.assertEqual(set(context.source_records), {'openalex_search', 'policy'})
        self.assertEqual([item['id'] for item in context.papers], ['paper-1', 'policy-1'])
        paper_adapter.fetch.assert_called_once_with()
        policy_adapter.fetch.assert_called_once_with()

    def test_ranking_stage_prioritizes_domestic_energy_policy(self):
        context = create_pipeline_context(self.config, self.logger, self.text)
        context.normalized_records = [
            {
                'id': 'other-1',
                'source_type': 'news',
                'source_name': '普通来源',
                'title': '无关内容',
            },
            {
                'id': 'policy-1',
                'source_type': 'policy',
                'source_name': '国家能源局',
                'title': '虚拟电厂参与需求响应政策',
                'raw_text': '储能系统参与能源管理。',
                'url': 'https://www.nea.gov.cn/example',
                'issuing_body': '国家能源局',
                'policy_strength': 'high',
                'policy_level': 'national',
                'region': 'CN',
            },
        ]

        from src.pipeline import ranking_stage
        ranking_stage.run(context)

        self.assertEqual(context.normalized_records[0]['id'], 'policy-1')
        self.assertEqual(
            context.normalized_records[0]['reading_suggestion']['recommended_action'],
            '精读',
        )
        self.assertIn('ranking_score_breakdown', context.normalized_records[1])

    def test_summarize_stage_falls_back_to_raw_papers_on_failure(self):
        context = create_pipeline_context(self.config, self.logger, self.text)
        context.papers = [{'id': 'paper-1'}]
        context.normalized_records = [{'id': 'paper-1'}]

        with patch('src.pipeline.summarize_stage.PaperSummarizer', side_effect=RuntimeError('boom')):
            from src.pipeline import summarize_stage
            summarize_stage.run(context)

        self.assertEqual(context.summarized_papers, context.normalized_records)

    def test_normalize_stage_sets_canonical_records(self):
        context = create_pipeline_context(self.config, self.logger, self.text)
        context.papers = [{'id': 'paper-1'}]
        context.source_adapter = Mock()
        context.source_adapter.normalize.return_value = [{'id': 'normalized-1'}]

        from src.pipeline import normalize_stage
        normalize_stage.run(context)

        self.assertEqual(context.normalized_records, [{'id': 'normalized-1'}])

    def test_normalize_stage_combines_sources_and_canonicalizes_legacy_paper(self):
        context = create_pipeline_context(self.config, self.logger, self.text)
        paper_adapter = Mock()
        paper_adapter.normalize.return_value = [{
            'id': 'W1',
            'title': 'Energy paper',
            'authors': ['Alice'],
            'published': 2026,
            'entry_url': 'https://openalex.org/W1',
            'categories': ['Energy'],
        }]
        policy_adapter = Mock()
        policy_adapter.normalize.return_value = [{
            'id': 'policy-1',
            'source_type': 'policy',
            'source_name': '国家能源局',
            'title': '政策',
        }]
        context.enabled_sources = ['openalex_search', 'policy']
        context.source_adapters = {
            'openalex_search': paper_adapter,
            'policy': policy_adapter,
        }
        context.source_records = {
            'openalex_search': [{'id': 'W1'}],
            'policy': [{'id': 'policy-1'}],
        }

        from src.pipeline import normalize_stage
        normalize_stage.run(context)

        self.assertEqual(len(context.normalized_records), 2)
        self.assertEqual(context.normalized_records[0]['source_type'], 'paper')
        self.assertEqual(context.normalized_records[0]['source_name'], 'OpenAlex')
        self.assertEqual(context.normalized_records[1]['source_type'], 'policy')

    def test_analyze_stage_uses_context_records(self):
        context = create_pipeline_context(self.config, self.logger, self.text)
        context.papers = [{'id': 'paper-1', 'raw': True}]
        context.normalized_records = [{'id': 'paper-1', 'normalized': True}]
        context.summarized_papers = [{'id': 'paper-1', 'summary': 'done'}]
        context.cross_source_result = {'direction_count': 1}

        analyzer_instance = Mock()
        analyzer_instance.analyze.return_value = {'ok': True}
        storage_instance = Mock()
        storage_instance.query_history.return_value = [{'snapshot_date': '2026-07-14'}]

        with patch('src.summarizer.llm_factory.LLMClientFactory.create_client', return_value=Mock()), \
             patch('src.analyzer.trend_analyzer.TrendAnalyzer', return_value=analyzer_instance), \
             patch('src.storage.base.build_storage', return_value=storage_instance):
            from src.pipeline import analyze_stage
            analyze_stage.run(context)

        analyzer_instance.analyze.assert_called_once_with(
            context.normalized_records,
            context.summarized_papers,
            history_observations=storage_instance.query_history.return_value,
            cross_source_analysis=context.cross_source_result,
        )
        query_kwargs = storage_instance.query_history.call_args.kwargs
        self.assertLess(query_kwargs['date_from'], query_kwargs['date_to'])

    def test_cross_source_stage_uses_enriched_documents(self):
        context = create_pipeline_context(self.config, self.logger, self.text)
        context.normalized_records = [{'id': 'raw'}]
        context.summarized_documents = [{
            'id': 'paper-1',
            'source_type': 'paper',
            'research_direction': ['虚拟电厂'],
            'importance_score': 80,
        }]

        from src.pipeline import cross_source_stage
        cross_source_stage.run(context)

        self.assertEqual(context.cross_source_result['direction_count'], 1)
        self.assertEqual(
            context.cross_source_result['directions'][0]['direction'], '虚拟电厂'
        )

    def test_report_stage_persists_web_ready_report(self):
        context = create_pipeline_context(self.config, self.logger, self.text)
        context.config['reporting'] = {'enabled': True, 'default_type': 'weekly'}
        context.summarized_documents = [{
            'id': 'paper-1',
            'source_type': 'paper',
            'title': '能源智能体论文',
            'published_at': '2026-07-14',
        }]
        context.analysis_result = {'temporal_trends': {}}
        generator = Mock()
        generator.generate.return_value = {'report_id': 'weekly-test'}
        generator.save.return_value = {
            'json': 'data/reports/weekly-test.json',
            'markdown': 'data/reports/weekly-test.md',
        }

        with patch(
            'src.pipeline.report_stage.IntelligenceReportGenerator',
            return_value=generator,
        ):
            from src.pipeline import report_stage
            report_stage.run(context)

        generator.generate.assert_called_once_with(
            context.summarized_documents,
            context.analysis_result,
            report_type='weekly',
        )
        self.assertEqual(context.report_result['report_id'], 'weekly-test')
        self.assertEqual(
            context.artifacts['intelligence_report_markdown'],
            'data/reports/weekly-test.md',
        )

    def test_extract_stage_keeps_local_tags_when_llm_extraction_fails(self):
        context = create_pipeline_context(self.config, self.logger, self.text)
        context.summarized_documents = [
            {
                'id': 'policy-1',
                'source_type': 'policy',
                'title': '国家能源局推动虚拟电厂参与需求响应',
                'raw_text': '北京开展储能系统示范。',
                'issuing_body': '国家能源局',
            }
        ]

        with patch(
            'src.pipeline.extract_stage.KnowledgeExtractor',
            side_effect=RuntimeError('llm unavailable'),
        ):
            from src.pipeline import extract_stage
            extract_stage.run(context)

        document = context.summarized_documents[0]
        self.assertIn('虚拟电厂', document['tags'])
        self.assertIn('国家能源局', document['entities'])
        self.assertEqual(context.knowledge_result['tag_extraction']['mode'], 'deterministic')

    def test_normalize_stage_persists_normalized_snapshot(self):
        context = create_pipeline_context(self.config, self.logger, self.text)
        context.papers = [{'id': 'paper-1'}]
        context.source_adapter = Mock()
        context.source_adapter.normalize.return_value = [{'id': 'paper-1', 'openalex_id': 'W1'}]

        from src.pipeline import normalize_stage
        normalize_stage.run(context)

        context.source_adapter.save_enriched_snapshot.assert_called_once_with(context.normalized_records)

    def test_linking_stage_updates_context_and_persists_snapshot(self):
        context = create_pipeline_context(self.config, self.logger, self.text)
        context.normalized_records = [
            {
                'id': 'paper-1', 'source_type': 'paper', 'source_name': 'arXiv',
                'title': '虚拟电厂研究', 'url': 'https://example.cn/paper',
                'tags': ['虚拟电厂'],
            },
            {
                'id': 'policy-1', 'source_type': 'policy', 'source_name': '国家能源局',
                'title': '虚拟电厂政策', 'url': 'https://example.cn/policy',
                'tags': ['虚拟电厂'],
            },
        ]

        backend = Mock()
        backend.save_snapshot.return_value = Mock(location='data/documents/snapshots/one.json')
        with patch('src.pipeline.linking_stage.build_storage', return_value=backend):
            from src.pipeline import linking_stage
            linking_stage.run(context)

        self.assertEqual(context.linking_result['relation_count'], 1)
        self.assertEqual(len(context.normalized_records[0]['related_documents']), 1)
        backend.save_snapshot.assert_called_once()
        self.assertEqual(
            context.artifacts['linked_documents'],
            'data/documents/snapshots/one.json',
        )

    def test_export_stage_runs_obsidian_without_summary_report(self):
        context = create_pipeline_context(self.config, self.logger, self.text)
        context.config['outputs'] = {
            'obsidian': {'enabled': True, 'vault_path': 'unused-in-mock'}
        }
        context.summarized_documents = [{'id': 'paper-1', 'source_type': 'paper'}]
        exporter = Mock()
        exporter.export_documents.return_value = {
            'vault_path': 'vault',
            'daily_path': 'vault/daily/2026-07-14.md',
            'count': 1,
        }

        with patch('src.pipeline.export_stage.ObsidianExporter', return_value=exporter):
            from src.pipeline import export_stage
            export_stage.run(context)

        exporter.export_documents.assert_called_once()
        self.assertEqual(context.artifacts['obsidian_vault'], 'vault')

    def test_export_stage_writes_zotero_exchange_files_without_api_write(self):
        context = create_pipeline_context(self.config, self.logger, self.text)
        context.config['outputs'] = {'zotero': {'enabled': True}}
        context.summarized_documents = [{'id': 'paper-1', 'source_type': 'paper'}]
        client = Mock()
        client.export_documents.return_value = {
            'csl_json': 'data/zotero/papers.csl.json',
            'bibtex': 'data/zotero/papers.bib',
        }

        with patch('src.pipeline.export_stage.ZoteroClient', return_value=client):
            from src.pipeline import export_stage
            export_stage.run(context)

        client.export_documents.assert_called_once_with(context.summarized_documents)
        self.assertEqual(
            context.artifacts['zotero_bibtex'], 'data/zotero/papers.bib'
        )


def _mark_stop(context):
    context.stop_requested = True
    return context


def _record(calls, name, context):
    calls.append(name)
    return context


if __name__ == '__main__':
    unittest.main()
