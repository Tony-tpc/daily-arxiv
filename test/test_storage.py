#!/usr/bin/env python3
"""Tests for JSON and SQLite canonical document storage backends."""

import sys
import tempfile
import unittest
from pathlib import Path


project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.storage.base import JSONStorage, SQLiteStorage, build_storage


class StorageBackendTests(unittest.TestCase):
    def test_json_storage_writes_latest_and_immutable_snapshot_atomically(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            storage = JSONStorage(temp_dir)
            documents = _documents()

            info = storage.save_snapshot(
                documents,
                snapshot_date='2026-07-14',
                metadata={'stage': 'summarized'},
            )

            self.assertTrue(Path(info.location).is_file())
            self.assertTrue(Path(temp_dir, 'latest.json').is_file())
            self.assertEqual(storage.load_latest()['documents'], documents)
            self.assertEqual(
                storage.load_snapshot(info.snapshot_id)['metadata']['stage'], 'summarized'
            )
            self.assertEqual(storage.query(source_type='policy')[0]['id'], 'policy-1')
            self.assertEqual(storage.query(topic='虚拟电厂')[0]['id'], 'paper-1')
            self.assertFalse(list(Path(temp_dir).rglob('*.tmp')))
            with self.assertRaises(ValueError):
                storage.load_snapshot('../escape')

    def test_sqlite_storage_roundtrip_and_latest_pointer(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            database = Path(temp_dir, 'intelligence.db')
            storage = SQLiteStorage(database)
            first = storage.save_snapshot(_documents(), snapshot_date='2026-07-13')
            second_docs = [_documents()[1]]
            second = storage.save_snapshot(second_docs, snapshot_date='2026-07-14')

            self.assertTrue(database.is_file())
            self.assertEqual(storage.load_snapshot(first.snapshot_id)['document_count'], 2)
            self.assertEqual(storage.load_latest()['snapshot_id'], second.snapshot_id)
            self.assertEqual(storage.query(source_type='policy'), second_docs)
            self.assertEqual(storage.query(topic='missing'), [])

    def test_storage_factory_rejects_unknown_backend(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            json_storage = build_storage(
                {'storage': {'type': 'json', 'document_json_path': temp_dir}}
            )
            sqlite_storage = build_storage(
                {'storage': {'type': 'sqlite', 'sqlite_path': str(Path(temp_dir, 'db.sqlite'))}}
            )
            self.assertIsInstance(json_storage, JSONStorage)
            self.assertIsInstance(sqlite_storage, SQLiteStorage)
            with self.assertRaises(ValueError):
                build_storage({'storage': {'type': 'memory'}})


def _documents():
    return [
        {
            'id': 'paper-1',
            'source_type': 'paper',
            'title': '虚拟电厂论文',
            'tags': ['虚拟电厂'],
            'themes': ['能源系统'],
        },
        {
            'id': 'policy-1',
            'source_type': 'policy',
            'title': '储能政策',
            'tags': ['储能'],
        },
    ]


if __name__ == '__main__':
    unittest.main()
