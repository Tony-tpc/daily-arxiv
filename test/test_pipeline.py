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

        with patch('src.pipeline.runner.fetch_stage.run') as fetch_run, \
             patch('src.pipeline.runner.normalize_stage.run') as normalize_run, \
             patch('src.pipeline.runner.summarize_stage.run') as summarize_run:
            fetch_run.side_effect = lambda ctx: _mark_stop(ctx)

            result = run_pipeline(context)

            self.assertTrue(result.stop_requested)
            normalize_run.assert_not_called()
            summarize_run.assert_not_called()

    def test_run_pipeline_executes_stages_in_order(self):
        context = create_pipeline_context(self.config, self.logger, self.text)
        calls = []

        with patch('src.pipeline.runner.fetch_stage.run', side_effect=lambda ctx: _record(calls, 'fetch', ctx)), \
             patch('src.pipeline.runner.normalize_stage.run', side_effect=lambda ctx: _record(calls, 'normalize', ctx)), \
             patch('src.pipeline.runner.summarize_stage.run', side_effect=lambda ctx: _record(calls, 'summarize', ctx)), \
             patch('src.pipeline.runner.export_stage.run', side_effect=lambda ctx: _record(calls, 'export', ctx)), \
             patch('src.pipeline.runner.extract_stage.run', side_effect=lambda ctx: _record(calls, 'extract', ctx)), \
             patch('src.pipeline.runner.analyze_stage.run', side_effect=lambda ctx: _record(calls, 'analyze', ctx)):
            run_pipeline(context)

        self.assertEqual(calls, ['fetch', 'normalize', 'summarize', 'export', 'extract', 'analyze'])

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

    def test_summarize_stage_falls_back_to_raw_papers_on_failure(self):
        context = create_pipeline_context(self.config, self.logger, self.text)
        context.papers = [{'id': 'paper-1'}]

        with patch('src.pipeline.summarize_stage.PaperSummarizer', side_effect=RuntimeError('boom')):
            from src.pipeline import summarize_stage
            summarize_stage.run(context)

        self.assertEqual(context.summarized_papers, context.papers)


def _mark_stop(context):
    context.stop_requested = True
    return context


def _record(calls, name, context):
    calls.append(name)
    return context


if __name__ == '__main__':
    unittest.main()
