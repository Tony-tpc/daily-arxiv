"""JSON and SQLite storage backends for canonical document snapshots."""

from __future__ import annotations

import json
import os
import re
import sqlite3
import uuid
from abc import ABC, abstractmethod
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterator, List


@dataclass(frozen=True)
class SnapshotInfo:
    """Stable metadata returned after a snapshot is persisted."""

    snapshot_id: str
    snapshot_date: str
    source_type: str
    document_count: int
    created_at: str
    location: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class StorageBackend(ABC):
    """Backend contract for latest + immutable snapshot persistence."""

    @abstractmethod
    def save_snapshot(
        self,
        documents: List[Dict[str, Any]],
        *,
        snapshot_date: str | None = None,
        source_type: str | None = None,
        metadata: Dict[str, Any] | None = None,
    ) -> SnapshotInfo:
        raise NotImplementedError

    @abstractmethod
    def load_latest(self) -> Dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def load_snapshot(self, snapshot_id: str) -> Dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def query(
        self, *, source_type: str = "", topic: str = ""
    ) -> List[Dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def list_snapshots(
        self,
        *,
        date_from: str = "",
        date_to: str = "",
        source_type: str = "",
        topic: str = "",
    ) -> List[Dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def query_history(
        self,
        *,
        date_from: str = "",
        date_to: str = "",
        source_type: str = "",
        topic: str = "",
    ) -> List[Dict[str, Any]]:
        raise NotImplementedError


class JSONStorage(StorageBackend):
    """Atomic filesystem backend preserving latest.json and immutable snapshots."""

    def __init__(self, root_path: str | Path = "data/documents"):
        self.root_path = Path(root_path)
        self.snapshots_path = self.root_path / "snapshots"
        self.latest_path = self.root_path / "latest.json"
        self.manifest_path = self.root_path / "manifest.json"

    def save_snapshot(
        self,
        documents: List[Dict[str, Any]],
        *,
        snapshot_date: str | None = None,
        source_type: str | None = None,
        metadata: Dict[str, Any] | None = None,
    ) -> SnapshotInfo:
        self.snapshots_path.mkdir(parents=True, exist_ok=True)
        info = _snapshot_info(
            documents,
            snapshot_date=snapshot_date,
            source_type=source_type,
            location=self.root_path.as_posix(),
        )
        snapshot_path = self.snapshots_path / f"{info.snapshot_id}.json"
        persisted_info = SnapshotInfo(
            **{**info.to_dict(), "location": snapshot_path.as_posix()}
        )
        payload = {
            "schema_version": "1.0",
            **persisted_info.to_dict(),
            "metadata": metadata or {},
            "documents": documents,
        }
        _atomic_json_write(snapshot_path, payload)
        _atomic_json_write(self.latest_path, payload)
        self._update_manifest(payload)
        return persisted_info

    def load_latest(self) -> Dict[str, Any]:
        return _load_json(self.latest_path)

    def load_snapshot(self, snapshot_id: str) -> Dict[str, Any]:
        safe_id = _safe_snapshot_id(snapshot_id)
        return _load_json(self.snapshots_path / f"{safe_id}.json")

    def query(self, *, source_type: str = "", topic: str = "") -> List[Dict[str, Any]]:
        documents = self.load_latest().get("documents", [])
        return _filter_documents(documents, source_type=source_type, topic=topic)

    def list_snapshots(
        self,
        *,
        date_from: str = "",
        date_to: str = "",
        source_type: str = "",
        topic: str = "",
    ) -> List[Dict[str, Any]]:
        manifest = _load_json(self.manifest_path)
        entries = manifest.get("snapshots", [])
        if not entries and self.snapshots_path.exists():
            manifest = self.rebuild_manifest()
            entries = manifest.get("snapshots", [])
        return _filter_snapshot_entries(
            entries,
            date_from=date_from,
            date_to=date_to,
            source_type=source_type,
            topic=topic,
        )

    def query_history(
        self,
        *,
        date_from: str = "",
        date_to: str = "",
        source_type: str = "",
        topic: str = "",
    ) -> List[Dict[str, Any]]:
        observations = []
        for entry in self.list_snapshots(
            date_from=date_from,
            date_to=date_to,
            source_type=source_type,
            topic=topic,
        ):
            payload = self.load_snapshot(entry["snapshot_id"])
            for document in _filter_documents(
                payload.get("documents", []), source_type=source_type, topic=topic
            ):
                observations.append({
                    "snapshot_id": entry["snapshot_id"],
                    "snapshot_date": entry["snapshot_date"],
                    "created_at": entry["created_at"],
                    "document": document,
                })
        return observations

    def rebuild_manifest(self) -> Dict[str, Any]:
        """Rebuild the JSON index from durable snapshot files."""
        entries = []
        for path in sorted(self.snapshots_path.glob("*.json")):
            payload = _load_json(path)
            if payload.get("snapshot_id"):
                entries.append(_manifest_entry(payload))
        manifest = {
            "schema_version": "1.0",
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "snapshot_count": len(entries),
            "snapshots": sorted(entries, key=_snapshot_sort_key, reverse=True),
        }
        _atomic_json_write(self.manifest_path, manifest)
        return manifest

    def _update_manifest(self, payload: Dict[str, Any]) -> None:
        manifest = _load_json(self.manifest_path)
        entries = [
            item for item in manifest.get("snapshots", [])
            if item.get("snapshot_id") != payload.get("snapshot_id")
        ]
        entries.append(_manifest_entry(payload))
        _atomic_json_write(self.manifest_path, {
            "schema_version": "1.0",
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "snapshot_count": len(entries),
            "snapshots": sorted(entries, key=_snapshot_sort_key, reverse=True),
        })


class SQLiteStorage(StorageBackend):
    """Transactional SQLite backend retaining full canonical JSON payloads."""

    def __init__(self, database_path: str | Path = "data/arxiv.db"):
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def save_snapshot(
        self,
        documents: List[Dict[str, Any]],
        *,
        snapshot_date: str | None = None,
        source_type: str | None = None,
        metadata: Dict[str, Any] | None = None,
    ) -> SnapshotInfo:
        info = _snapshot_info(
            documents,
            snapshot_date=snapshot_date,
            source_type=source_type,
            location=self.database_path.as_posix(),
        )
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                """INSERT INTO snapshots
                (snapshot_id, snapshot_date, source_type, document_count, created_at, metadata_json)
                VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    info.snapshot_id,
                    info.snapshot_date,
                    info.source_type,
                    info.document_count,
                    info.created_at,
                    _json(metadata or {}),
                ),
            )
            connection.executemany(
                """INSERT INTO documents
                (snapshot_id, document_id, source_type, title, published_at, topics_text, payload_json)
                VALUES (?, ?, ?, ?, ?, ?, ?)""",
                [
                    (
                        info.snapshot_id,
                        str(document.get("id") or index),
                        str(document.get("source_type") or ""),
                        str(document.get("title") or ""),
                        str(document.get("published_at") or ""),
                        "\n".join(_document_topics(document)),
                        _json(document),
                    )
                    for index, document in enumerate(documents)
                ],
            )
            connection.execute(
                "INSERT OR REPLACE INTO state (key, value) VALUES ('latest_snapshot_id', ?)",
                (info.snapshot_id,),
            )
        return info

    def load_latest(self) -> Dict[str, Any]:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT value FROM state WHERE key = 'latest_snapshot_id'"
            ).fetchone()
        return self.load_snapshot(row[0]) if row else {}

    def load_snapshot(self, snapshot_id: str) -> Dict[str, Any]:
        with self._connect() as connection:
            snapshot = connection.execute(
                "SELECT * FROM snapshots WHERE snapshot_id = ?", (snapshot_id,)
            ).fetchone()
            if snapshot is None:
                return {}
            rows = connection.execute(
                "SELECT payload_json FROM documents WHERE snapshot_id = ? ORDER BY rowid",
                (snapshot_id,),
            ).fetchall()
        return {
            "schema_version": "1.0",
            "snapshot_id": snapshot["snapshot_id"],
            "snapshot_date": snapshot["snapshot_date"],
            "source_type": snapshot["source_type"],
            "document_count": snapshot["document_count"],
            "created_at": snapshot["created_at"],
            "metadata": json.loads(snapshot["metadata_json"] or "{}"),
            "documents": [json.loads(row["payload_json"]) for row in rows],
        }

    def query(self, *, source_type: str = "", topic: str = "") -> List[Dict[str, Any]]:
        latest = self.load_latest()
        return _filter_documents(
            latest.get("documents", []), source_type=source_type, topic=topic
        )

    def list_snapshots(
        self,
        *,
        date_from: str = "",
        date_to: str = "",
        source_type: str = "",
        topic: str = "",
    ) -> List[Dict[str, Any]]:
        clauses = []
        parameters: List[Any] = []
        if date_from:
            clauses.append("s.snapshot_date >= ?")
            parameters.append(date_from)
        if date_to:
            clauses.append("s.snapshot_date <= ?")
            parameters.append(date_to)
        if source_type:
            clauses.append(
                "(s.source_type = ? OR EXISTS (SELECT 1 FROM documents d "
                "WHERE d.snapshot_id = s.snapshot_id AND d.source_type = ?))"
            )
            parameters.extend([source_type, source_type])
        if topic:
            clauses.append(
                "EXISTS (SELECT 1 FROM documents d WHERE d.snapshot_id = s.snapshot_id "
                "AND lower(d.topics_text) LIKE ?)"
            )
            parameters.append(f"%{topic.casefold()}%")
        where = " WHERE " + " AND ".join(clauses) if clauses else ""
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT s.* FROM snapshots s" + where
                + " ORDER BY s.snapshot_date DESC, s.created_at DESC",
                parameters,
            ).fetchall()
        return [
            {
                "snapshot_id": row["snapshot_id"],
                "snapshot_date": row["snapshot_date"],
                "source_type": row["source_type"],
                "document_count": row["document_count"],
                "created_at": row["created_at"],
                "location": self.database_path.as_posix(),
                "metadata": json.loads(row["metadata_json"] or "{}"),
            }
            for row in rows
        ]

    def query_history(
        self,
        *,
        date_from: str = "",
        date_to: str = "",
        source_type: str = "",
        topic: str = "",
    ) -> List[Dict[str, Any]]:
        clauses = []
        parameters: List[Any] = []
        if date_from:
            clauses.append("s.snapshot_date >= ?")
            parameters.append(date_from)
        if date_to:
            clauses.append("s.snapshot_date <= ?")
            parameters.append(date_to)
        if source_type:
            clauses.append("d.source_type = ?")
            parameters.append(source_type)
        if topic:
            clauses.append("lower(d.topics_text) LIKE ?")
            parameters.append(f"%{topic.casefold()}%")
        where = " WHERE " + " AND ".join(clauses) if clauses else ""
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT s.snapshot_id, s.snapshot_date, s.created_at, d.payload_json "
                "FROM snapshots s JOIN documents d ON d.snapshot_id = s.snapshot_id"
                + where + " ORDER BY s.snapshot_date, s.created_at, d.rowid",
                parameters,
            ).fetchall()
        return [
            {
                "snapshot_id": row["snapshot_id"],
                "snapshot_date": row["snapshot_date"],
                "created_at": row["created_at"],
                "document": json.loads(row["payload_json"]),
            }
            for row in rows
        ]

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                PRAGMA journal_mode=WAL;
                PRAGMA foreign_keys=ON;
                CREATE TABLE IF NOT EXISTS snapshots (
                    snapshot_id TEXT PRIMARY KEY,
                    snapshot_date TEXT NOT NULL,
                    source_type TEXT NOT NULL,
                    document_count INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    metadata_json TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS documents (
                    snapshot_id TEXT NOT NULL,
                    document_id TEXT NOT NULL,
                    source_type TEXT NOT NULL,
                    title TEXT NOT NULL,
                    published_at TEXT NOT NULL,
                    topics_text TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    PRIMARY KEY (snapshot_id, document_id),
                    FOREIGN KEY (snapshot_id) REFERENCES snapshots(snapshot_id) ON DELETE CASCADE
                );
                CREATE INDEX IF NOT EXISTS idx_documents_source_type
                    ON documents(source_type);
                CREATE INDEX IF NOT EXISTS idx_snapshots_date
                    ON snapshots(snapshot_date, created_at);
                CREATE TABLE IF NOT EXISTS state (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
                """
            )

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()


def build_storage(
    config: Dict[str, Any], *, json_path: str | Path | None = None
) -> StorageBackend:
    """Create the configured backend; both supported choices are implemented."""
    settings = config.get("storage", {})
    backend_type = str(settings.get("type", "json")).lower()
    if backend_type == "json":
        root_path = json_path or settings.get("document_json_path", "data/documents")
        return JSONStorage(root_path)
    if backend_type == "sqlite":
        return SQLiteStorage(settings.get("sqlite_path", "data/arxiv.db"))
    raise ValueError(f"Unsupported storage type: {backend_type}")


def _snapshot_info(
    documents: List[Dict[str, Any]],
    *,
    snapshot_date: str | None,
    source_type: str | None,
    location: str,
) -> SnapshotInfo:
    created_at = datetime.now(timezone.utc).isoformat()
    resolved_date = snapshot_date or date.today().isoformat()
    types = {str(item.get("source_type") or "unknown") for item in documents}
    resolved_type = source_type or (next(iter(types)) if len(types) == 1 else "mixed")
    resolved_type = re.sub(r"[^A-Za-z0-9_-]+", "_", resolved_type).strip("_") or "unknown"
    snapshot_id = (
        f"{resolved_date}__{resolved_type}__"
        f"{datetime.now(timezone.utc).strftime('%H%M%S%f')}__{uuid.uuid4().hex[:6]}"
    )
    return SnapshotInfo(
        snapshot_id=snapshot_id,
        snapshot_date=resolved_date,
        source_type=resolved_type,
        document_count=len(documents),
        created_at=created_at,
        location=location,
    )


def _filter_documents(
    documents: List[Dict[str, Any]], *, source_type: str, topic: str
) -> List[Dict[str, Any]]:
    topic_key = str(topic or "").casefold()
    result = []
    for document in documents:
        if source_type and str(document.get("source_type") or "") != source_type:
            continue
        if topic_key and topic_key not in " ".join(_document_topics(document)).casefold():
            continue
        result.append(document)
    return result


def _document_topics(document: Dict[str, Any]) -> List[str]:
    values = []
    for field in ("tags", "themes", "research_direction", "keywords"):
        raw = document.get(field) or []
        values.extend(raw if isinstance(raw, list) else [raw])
    return [str(value) for value in values if str(value).strip()]


def _manifest_entry(payload: Dict[str, Any]) -> Dict[str, Any]:
    documents = payload.get("documents", [])
    source_counts: Dict[str, int] = {}
    topics = []
    for document in documents:
        source_type = str(document.get("source_type") or "unknown")
        source_counts[source_type] = source_counts.get(source_type, 0) + 1
        topics.extend(_document_topics(document))
    return {
        "snapshot_id": payload.get("snapshot_id"),
        "snapshot_date": payload.get("snapshot_date"),
        "source_type": payload.get("source_type"),
        "source_types": sorted(source_counts),
        "source_counts": source_counts,
        "document_count": payload.get("document_count", len(documents)),
        "topics": sorted(set(topics)),
        "created_at": payload.get("created_at"),
        "location": payload.get("location"),
        "metadata": payload.get("metadata", {}),
    }


def _filter_snapshot_entries(
    entries: List[Dict[str, Any]],
    *,
    date_from: str,
    date_to: str,
    source_type: str,
    topic: str,
) -> List[Dict[str, Any]]:
    result = []
    topic_key = topic.casefold()
    for entry in entries:
        snapshot_date = str(entry.get("snapshot_date") or "")
        if date_from and snapshot_date < date_from:
            continue
        if date_to and snapshot_date > date_to:
            continue
        source_types = entry.get("source_types", [])
        if source_type and source_type not in source_types and entry.get("source_type") != source_type:
            continue
        if topic_key and not any(topic_key in str(value).casefold() for value in entry.get("topics", [])):
            continue
        result.append(entry)
    return sorted(result, key=_snapshot_sort_key, reverse=True)


def _snapshot_sort_key(entry: Dict[str, Any]) -> tuple[str, str]:
    return str(entry.get("snapshot_date") or ""), str(entry.get("created_at") or "")


def _atomic_json_write(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    temporary.write_text(_json(payload), encoding="utf-8")
    os.replace(temporary, path)


def _load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2)


def _safe_snapshot_id(value: str) -> str:
    text = str(value or "")
    if not text or any(char not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-" for char in text):
        raise ValueError("Invalid snapshot id")
    return text
