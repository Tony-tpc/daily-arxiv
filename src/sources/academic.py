"""Fair, resumable pagination for scholarly indexes; budgets never truncate coverage."""
from __future__ import annotations

import hashlib
import json
import os
import re
import time
import uuid
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import httpx
from .base import BaseSourceAdapter

PAPER_SOURCES = {"arxiv", "openalex_search", "crossref", "openaire", "semantic_scholar", "institution_import"}
INDEX_SOURCES = ("openalex_search", "crossref", "openaire", "semantic_scholar")


def atomic_json(path: str | Path, payload: Any) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(temporary, path)


def read_json(path: str | Path, default: Any = None) -> Any:
    path = Path(path)
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


def clean_doi(value: Any) -> str:
    return re.sub(r"^(?:https?://(?:dx\.)?doi\.org/|doi:\s*)", "", str(value or "").strip(), flags=re.I).lower()


def record_key(record: dict) -> str:
    doi = clean_doi(record.get("doi"))
    return f"doi:{doi}" if doi else f"{record.get('source_record_provider', '')}:{record.get('id', '')}"


def unique_records(records: list[dict]) -> list[dict]:
    merged: dict[str, dict] = {}
    for record in records:
        key = record_key(record)
        if key not in merged:
            merged[key] = dict(record)
        else:
            for name, value in record.items():
                if not merged[key].get(name) and value:
                    merged[key][name] = value
    return list(merged.values())


@dataclass
class PaperQuery:
    key: str
    term: str = ""
    issn: str = ""
    relation: str = ""
    seed: str = ""


@dataclass
class PaperPage:
    records: list[dict]
    next_cursor: str | None
    total: int | None = None


@dataclass
class PaperFetchResult:
    records: list[dict] = field(default_factory=list)
    status: str = "complete"
    errors: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


class PagedPaperAdapter(BaseSourceAdapter):
    """Providers implement one page; checkpoints commit records and cursor together."""

    def __init__(self, config: dict):
        super().__init__(config)
        self.settings = dict(config.get("sources", {}).get(self.source_name, {}))
        self.discovery = config.get("paper_discovery", {})
        self.client = httpx.Client(timeout=float(self.settings.get("request_timeout_seconds", 30)))
        self.last_fetch_result = PaperFetchResult()
        self._last_request = 0.0

    @property
    def source_config(self) -> dict:
        return self.settings

    @property
    def page_size(self) -> int:
        return min(100, max(1, int(self.settings.get("per_page", 100))))

    def validate(self) -> None:
        if int(self.settings.get("per_page", 100)) < 1:
            raise ValueError("per_page must be positive")

    def readiness(self) -> str:
        return "ready"

    def close(self) -> None:
        self.client.close()

    def get_json(self, url: str, params: dict | None = None, headers: dict | None = None) -> dict:
        attempts = max(1, int(self.settings.get("max_attempts", 3)))
        interval = float(self.settings.get("request_interval_seconds", 1))
        for attempt in range(attempts):
            time.sleep(max(0, interval - (time.monotonic() - self._last_request)))
            self._last_request = time.monotonic()
            try:
                response = self.client.get(url, params=params, headers=headers)
                if response.status_code not in {429, 500, 502, 503, 504}:
                    response.raise_for_status()
                    return response.json()
                if attempt == attempts - 1:
                    response.raise_for_status()
                delay = response.headers.get("Retry-After", "")
                delay = float(delay) if delay.isdigit() else 2 ** (attempt + 1)
            except httpx.TransportError:
                if attempt == attempts - 1:
                    raise
                delay = 2 ** (attempt + 1)
            time.sleep(min(float(self.settings.get("max_retry_delay_seconds", 30)), delay))
        raise RuntimeError("request retry exhausted")

    def queries(self) -> list[PaperQuery]:
        terms = self.settings.get("search_terms") or self.discovery.get("search_terms", [])
        queries = [PaperQuery(f"topic:{term}", term=str(term)) for term in dict.fromkeys(terms)]
        if self.settings.get("journal_search", True):
            from .paper_quality import approved_venue_issns
            queries += [PaperQuery(f"journal:{issn}", issn=issn) for issn in approved_venue_issns(self.config)]
        return queries

    def fetch(self, **kwargs: Any) -> list[dict]:
        end = date.today()
        start = end - timedelta(days=int(self.settings.get("recent_days", 90)))
        self.last_fetch_result = self.fetch_range(start.isoformat(), end.isoformat())
        self.save_raw_snapshot(self.last_fetch_result.records)
        return self.last_fetch_result.records

    def fetch_range(self, date_from: str, date_to: str, *, queries: list[PaperQuery] | None = None,
                    force: bool = False) -> PaperFetchResult:
        if date.fromisoformat(date_from) > date.fromisoformat(date_to):
            raise ValueError("date_from must not exceed date_to")
        if self.readiness() != "ready":
            return PaperFetchResult(status="unavailable", errors=[self.readiness()], metadata={"source": self.source_name})
        queries = self.queries() if queries is None else queries
        if not queries:
            return PaperFetchResult(status="unavailable", errors=["no_queries_or_verified_journals"])
        root = Path(self.discovery.get("checkpoint_directory", "data/state/paper_discovery")) / self.source_name
        states = []
        for query in queries:
            signature = {"version": 1, "query": vars(query), "from": date_from, "to": date_to, "page_size": self.page_size}
            key = hashlib.sha256(json.dumps(signature, sort_keys=True).encode()).hexdigest()
            path = root / f"{key}.json"
            state = read_json(path, {})
            if not state or force:
                state = {"signature": signature, "cursor": "*", "records": [], "pages": 0, "complete": False}
            states.append((query, path, state))
        budget = max(1, int(self.settings.get("max_pages_per_run", self.discovery.get("max_pages_per_run", 40))))
        calls = 0
        errors: list[str] = []
        failed: set[str] = set()
        while calls < budget:
            pending = sorted((s for s in states if not s[2]["complete"] and s[0].key not in failed),
                             key=lambda s: (s[2]["pages"], s[0].key))
            if not pending:
                break
            query, path, state = pending[0]
            calls += 1
            try:
                page = self.fetch_page(query, date_from, date_to, state["cursor"])
                if page.next_cursor == state["cursor"] and page.records:
                    raise ValueError("provider repeated a nonempty cursor")
                records = [r for r in page.records if publication_in_range(r, date_from, date_to)]
                state["records"] = unique_records(state["records"] + records)
                state.update(cursor=page.next_cursor, complete=page.next_cursor is None,
                             pages=state["pages"] + 1, total=page.total, error="",
                             updated_at=datetime.now(timezone.utc).isoformat())
                atomic_json(path, state)
            except (httpx.HTTPError, ValueError, KeyError, TypeError) as exc:
                code = exc.response.status_code if isinstance(exc, httpx.HTTPStatusError) else type(exc).__name__
                message = f"{query.key}: {code}"
                if code in {400, 404, 410} and state["cursor"] != "*":
                    state["cursor"] = "*"
                state["error"] = message
                atomic_json(path, state)
                failed.add(query.key)
                errors.append(message)
        records = unique_records([r for _, _, state in states for r in state["records"]])
        complete = all(state["complete"] for _, _, state in states)
        status = "complete" if complete else "partial" if records or not errors else "unavailable"
        return PaperFetchResult(records, status, errors, {
            "source": self.source_name, "from": date_from, "to": date_to, "requests": calls,
            "raw_count": len(records), "queries": [{"key": q.key, "complete": s["complete"],
            "pages": s["pages"], "records": len(s["records"]), "error": s.get("error", "")} for q, _, s in states],
        })

    def fetch_page(self, query: PaperQuery, date_from: str, date_to: str, cursor: str) -> PaperPage:
        raise NotImplementedError

    def normalize(self, records: list[dict]) -> list[dict]:
        from .paper_normalizer import normalize_paper_records
        return normalize_paper_records(records, self.source_name, self.config, enforce_quality=False)

    def save_raw_snapshot(self, records: list[dict]) -> None:
        root = Path(self.discovery.get("raw_directory", "data/raw/academic")) / self.source_name
        atomic_json(root / "latest.json", {"source": self.source_name, "papers": records,
                    "coverage": self.last_fetch_result.metadata, "status": self.last_fetch_result.status,
                    "errors": self.last_fetch_result.errors})


def publication_in_range(record: dict, start: str, end: str) -> bool:
    value = str(record.get("published_at") or record.get("published") or "")[:10]
    return bool(value and start[:len(value)] <= value <= end[:len(value)])
