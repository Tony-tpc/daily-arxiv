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
                Mock(run=lambda ctx: _record(calls, 'summarize', ctx)),
                Mock(run=lambda ctx: _record(calls, 'export', ctx)),
                Mock(run=lambda ctx: _record(calls, 'extract', ctx)),
                Mock(run=lambda ctx: _record(calls, 'analyze', ctx)),
            ]
            run_pipeline(context)

        self.assertEqual(calls, ['fetch', 'normalize', 'ranking', 'summarize', 'export', 'extract', 'analyze'])

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

    def test_analyze_stage_uses_context_records(self):
        context = create_pipeline_context(self.config, self.logger, self.text)
        context.papers = [{'id': 'paper-1', 'raw': True}]
        context.normalized_records = [{'id': 'paper-1', 'normalized': True}]
        context.summarized_papers = [{'id': 'paper-1', 'summary': 'done'}]

        analyzer_instance = Mock()
        analyzer_instance.analyze.return_value = {'ok': True}

        with patch('src.summarizer.llm_factory.LLMClientFactory.create_client', return_value=Mock()), \
             patch('src.analyzer.trend_analyzer.TrendAnalyzer', return_value=analyzer_instance):
            from src.pipeline import analyze_stage
            analyze_stage.run(context)

        analyzer_instance.analyze.assert_called_once_with(context.normalized_records, context.summarized_papers)

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


def _mark_stop(context):
    context.stop_requested = True
    return context


def _record(calls, name, context):
    calls.append(name)
    return context


if __name__ == '__main__':
    unittest.main()
