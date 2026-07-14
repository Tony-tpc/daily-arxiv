"""Read-only Zotero Local API client and bibliographic export helpers."""

from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path
from typing import Any, Dict, List

import httpx


SUPPORTED_EXPORT_FORMATS = {"csljson", "bibtex"}


class ZoteroLocalAPIError(RuntimeError):
    """Raised when the local Zotero API is unavailable or disabled."""


class ZoteroClient:
    """Use Zotero's GET-only local API without mutating the user's library."""

    def __init__(self, config: Dict[str, Any], client: httpx.Client | None = None):
        settings = config.get("outputs", {}).get("zotero", {})
        self.base_url = str(
            settings.get("base_url", "http://localhost:23119/api")
        ).rstrip("/")
        self.user_id = str(settings.get("user_id", 0))
        self.timeout = float(settings.get("timeout_seconds", 5))
        self.export_directory = Path(
            settings.get("export_directory", "data/zotero")
        )
        self.client = client or httpx.Client(timeout=self.timeout)
        self.headers = {"Zotero-API-Version": "3"}

    def healthcheck(self) -> Dict[str, Any]:
        """Return local API version headers after a read-only probe."""
        response = self._get("")
        payload = response.json() if response.content else {}
        return {
            "ok": True,
            "api_version": response.headers.get("Zotero-API-Version", "3"),
            "schema_version": response.headers.get("Zotero-Schema-Version", ""),
            "payload": payload,
        }

    def list_items(
        self,
        *,
        query: str = "",
        item_type: str = "",
        tag: str = "",
        since: int | None = None,
        limit: int | None = None,
        top_only: bool = True,
    ) -> List[Dict[str, Any]]:
        """Read items from the locally logged-in user's library."""
        endpoint = f"users/{self.user_id}/items" + ("/top" if top_only else "")
        params: Dict[str, Any] = {"format": "json"}
        if query:
            params["q"] = query
        if item_type:
            params["itemType"] = item_type
        if tag:
            params["tag"] = tag
        if since is not None:
            params["since"] = int(since)
        if limit is not None:
            params["limit"] = max(1, int(limit))
        payload = self._get(endpoint, params=params).json()
        return payload if isinstance(payload, list) else [payload]

    def export_library(
        self,
        export_format: str,
        *,
        query: str = "",
        limit: int = 100,
    ) -> str | List[Dict[str, Any]]:
        """Ask Zotero's translator layer for CSL-JSON or BibTeX."""
        export_format = self._validate_format(export_format)
        params: Dict[str, Any] = {"format": export_format, "limit": max(1, int(limit))}
        if query:
            params["q"] = query
        response = self._get(f"users/{self.user_id}/items", params=params)
        return response.json() if export_format == "csljson" else response.text

    def map_paper_to_item(self, document: Dict[str, Any]) -> Dict[str, Any]:
        """Map a canonical paper to a Zotero-compatible journalArticle payload."""
        if document.get("source_type", "paper") != "paper":
            raise ValueError("Only paper documents can be mapped to Zotero items")
        citekey = str(document.get("citekey") or generate_citekey(document))
        authors = document.get("authors_or_orgs") or document.get("authors") or []
        tags = list(dict.fromkeys([
            *(document.get("tags") or []), *(document.get("categories") or [])
        ]))
        return {
            "itemType": "journalArticle",
            "title": str(document.get("title") or ""),
            "creators": [
                {"creatorType": "author", "name": str(author)}
                for author in authors if str(author).strip()
            ],
            "abstractNote": str(document.get("summary") or document.get("raw_text") or ""),
            "date": str(document.get("published_at") or document.get("published") or ""),
            "DOI": str(document.get("doi") or ""),
            "url": str(document.get("url") or document.get("entry_url") or ""),
            "tags": [{"tag": str(tag)} for tag in tags if str(tag).strip()],
            "extra": f"Citation Key: {citekey}",
            "citekey": citekey,
        }

    def documents_to_csl_json(self, documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Convert canonical paper records to portable CSL-JSON."""
        records = []
        for document in documents:
            if document.get("source_type", "paper") != "paper":
                continue
            item = self.map_paper_to_item(document)
            year = _year(item["date"])
            records.append({
                "id": item["citekey"],
                "type": "article-journal",
                "title": item["title"],
                "author": [{"literal": creator["name"]} for creator in item["creators"]],
                "issued": {"date-parts": [[year]]} if year else {},
                "DOI": item["DOI"],
                "URL": item["url"],
                "abstract": item["abstractNote"],
                "keyword": ", ".join(tag["tag"] for tag in item["tags"]),
                "citation-key": item["citekey"],
            })
        return records

    def documents_to_bibtex(self, documents: List[Dict[str, Any]]) -> str:
        """Convert canonical paper records to deterministic UTF-8 BibTeX."""
        entries = []
        for document in documents:
            if document.get("source_type", "paper") != "paper":
                continue
            item = self.map_paper_to_item(document)
            fields = {
                "title": item["title"],
                "author": " and ".join(creator["name"] for creator in item["creators"]),
                "year": str(_year(item["date"]) or ""),
                "doi": item["DOI"],
                "url": item["url"],
                "abstract": item["abstractNote"],
                "keywords": ", ".join(tag["tag"] for tag in item["tags"]),
            }
            lines = [f"@article{{{item['citekey']},"]
            populated = [(key, value) for key, value in fields.items() if value]
            for index, (key, value) in enumerate(populated):
                comma = "," if index < len(populated) - 1 else ""
                lines.append(f"  {key} = {{{_bibtex_escape(value)}}}{comma}")
            lines.append("}")
            entries.append("\n".join(lines))
        return "\n\n".join(entries) + ("\n" if entries else "")

    def export_documents(self, documents: List[Dict[str, Any]]) -> Dict[str, str]:
        """Write portable CSL-JSON and BibTeX without changing Zotero state."""
        self.export_directory.mkdir(parents=True, exist_ok=True)
        csl_path = self.export_directory / "papers.csl.json"
        bibtex_path = self.export_directory / "papers.bib"
        csl_path.write_text(
            json.dumps(self.documents_to_csl_json(documents), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        bibtex_path.write_text(self.documents_to_bibtex(documents), encoding="utf-8")
        return {"csl_json": str(csl_path), "bibtex": str(bibtex_path)}

    def _get(self, endpoint: str, params: Dict[str, Any] | None = None) -> httpx.Response:
        url = self.base_url + (f"/{endpoint.lstrip('/')}" if endpoint else "/")
        try:
            response = self.client.get(url, params=params, headers=self.headers)
            if response.status_code == 403:
                raise ZoteroLocalAPIError(
                    "Zotero Local API is disabled; enable it in Settings → Advanced."
                )
            response.raise_for_status()
            return response
        except httpx.HTTPError as exc:
            raise ZoteroLocalAPIError(f"Zotero Local API request failed: {exc}") from exc

    @staticmethod
    def _validate_format(export_format: str) -> str:
        normalized = str(export_format or "").lower()
        if normalized not in SUPPORTED_EXPORT_FORMATS:
            raise ValueError(f"Unsupported Zotero export format: {export_format}")
        return normalized


def generate_citekey(document: Dict[str, Any]) -> str:
    authors = document.get("authors_or_orgs") or document.get("authors") or ["anon"]
    first_author = str(authors[0] if authors else "anon").strip()
    author_token = first_author.split()[-1] if first_author else "anon"
    year = str(_year(document.get("published_at") or document.get("published")) or "nd")
    title_tokens = re.findall(r"[A-Za-z0-9\u4e00-\u9fff]+", str(document.get("title") or ""))
    title_token = title_tokens[0] if title_tokens else "item"
    raw = f"{author_token}{year}{title_token}"
    return re.sub(r"[^A-Za-z0-9\u4e00-\u9fff_-]", "", raw)[:80] or f"item{date.today().year}"


def _year(value: Any) -> int | None:
    match = re.search(r"(?:19|20)\d{2}", str(value or ""))
    return int(match.group(0)) if match else None


def _bibtex_escape(value: Any) -> str:
    return str(value or "").replace("\\", "\\\\").replace("{", "\\{").replace("}", "\\}")
