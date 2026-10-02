"""Transactional sidecar store; public readers never create or migrate a database."""
from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path


class HotspotStore:
    def __init__(self, config: dict, *, readonly: bool = False):
        self.path = Path(config.get('hotspots', {}).get('state_path', 'data/hotspots/state.sqlite3'))
        self.readonly = readonly
        if not readonly:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.connect() as db:
                db.executescript('''
                    CREATE TABLE IF NOT EXISTS documents (
                        id TEXT PRIMARY KEY, content_hash TEXT NOT NULL, payload TEXT NOT NULL,
                        editorial TEXT NOT NULL DEFAULT '{}', group_id TEXT, updated_at TEXT NOT NULL);
                    CREATE TABLE IF NOT EXISTS groups (
                        id TEXT PRIMARY KEY, kind TEXT NOT NULL, title TEXT NOT NULL);
                    CREATE TABLE IF NOT EXISTS cache (key TEXT PRIMARY KEY, response TEXT NOT NULL);
                    CREATE TABLE IF NOT EXISTS sources (id TEXT PRIMARY KEY, payload TEXT NOT NULL);
                    CREATE TABLE IF NOT EXISTS snapshots (
                        hour TEXT PRIMARY KEY, payload TEXT NOT NULL);
                    CREATE TABLE IF NOT EXISTS audits (key TEXT PRIMARY KEY, payload TEXT NOT NULL);
                    CREATE TABLE IF NOT EXISTS analysis_profiles (
                        id TEXT PRIMARY KEY, content_hash TEXT NOT NULL, version TEXT NOT NULL,
                        document TEXT NOT NULL, profile TEXT NOT NULL, status TEXT NOT NULL,
                        topic_id TEXT, error TEXT NOT NULL DEFAULT '');
                    CREATE TABLE IF NOT EXISTS analysis_topics (
                        id TEXT PRIMARY KEY, kind TEXT NOT NULL, definition TEXT NOT NULL,
                        input_hash TEXT NOT NULL DEFAULT '', analysis TEXT NOT NULL DEFAULT '{}',
                        error TEXT NOT NULL DEFAULT '');
                    CREATE TABLE IF NOT EXISTS digests (id TEXT PRIMARY KEY, input_hash TEXT NOT NULL, payload TEXT NOT NULL);
                ''')

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path.resolve().as_uri() + '?mode=ro', uri=True, timeout=30) if self.readonly else sqlite3.connect(self.path, timeout=30)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    def rows(self, sql: str, args: tuple = ()) -> list[dict]:
        if not self.path.exists():
            return []
        with self.connect() as db:
            return [dict(row) for row in db.execute(sql, args)]

    def execute(self, sql: str, args: tuple = ()) -> None:
        with self.connect() as db:
            db.execute(sql, args)

    def documents(self) -> list[dict]:
        return [{**row, 'document': json.loads(row['payload']), 'editorial': json.loads(row['editorial'])}
                for row in self.rows('SELECT * FROM documents ORDER BY updated_at,id')]

    def cached(self, key: str) -> str | None:
        rows = self.rows('SELECT response FROM cache WHERE key=?', (key,))
        return rows[0]['response'] if rows else None

    def save_document(self, document: dict, digest: str, editorial: dict, at: str, group_id: str | None = None) -> None:
        self.execute('INSERT OR REPLACE INTO documents VALUES (?,?,?,?,?,?)',
                     (document['id'], digest, json.dumps(document, ensure_ascii=False),
                      json.dumps(editorial, ensure_ascii=False), group_id, at))

    def latest(self) -> dict:
        rows = self.rows('SELECT payload FROM snapshots ORDER BY hour DESC LIMIT 1')
        return json.loads(rows[0]['payload']) if rows else {}
