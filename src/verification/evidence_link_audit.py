"""Audit cached narrative evidence links outside the request path."""

from __future__ import annotations

import argparse
import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, Mapping
from urllib.parse import urlsplit, urlunsplit

import httpx

from src.sources.policy_adapter import canonicalize_official_policy_url


AUDIT_SCHEMA_VERSION = "1.0"
VERIFIED = "verified"


def audit_evidence_index(
    evidence_index: Mapping[str, Mapping[str, Any]],
    *,
    timeout_seconds: float = 15.0,
    max_workers: int = 6,
    fetch: Callable[[str], Any] | None = None,
) -> Dict[str, Dict[str, Any]]:
    """Return deterministic link health records for one narrative evidence index.

    Network calls happen only when this explicit audit is run; the web request path
    consumes the saved result and never calls external sites itself.
    """
    items = [(str(key), value) for key, value in evidence_index.items() if isinstance(value, Mapping)]
    if fetch is not None:
        return {key: _audit_item(key, item, fetch) for key, item in items}

    with httpx.Client(
        timeout=timeout_seconds,
        follow_redirects=True,
        headers={"User-Agent": "daily-arxiv-evidence-audit/1.0"},
    ) as client:
        def request(url: str) -> httpx.Response:
            return client.get(url)

        records: Dict[str, Dict[str, Any]] = {}
        with ThreadPoolExecutor(max_workers=max(1, max_workers)) as executor:
            futures = {
                executor.submit(_audit_item, key, item, request): key
                for key, item in items
            }
            for future in as_completed(futures):
                key = futures[future]
                records[key] = future.result()
    return {key: records[key] for key, _ in items}


def audit_analysis_file(
    analysis_path: str | Path = "data/analysis/latest.json",
    output_path: str | Path = "data/cache/evidence_link_audit.json",
    *,
    timeout_seconds: float = 15.0,
    max_workers: int = 6,
) -> Dict[str, Any]:
    """Audit each cached narrative view and atomically save its local health cache."""
    source = Path(analysis_path)
    payload = json.loads(source.read_text(encoding="utf-8"))
    narratives = payload.get("narrative_analysis") or {}
    views: Dict[str, Dict[str, Any]] = {}
    for view, narrative in narratives.items():
        if not isinstance(narrative, Mapping):
            continue
        index = narrative.get("evidence_index") or {}
        if not isinstance(index, Mapping):
            continue
        views[str(view)] = {
            "evidence": audit_evidence_index(
                index,
                timeout_seconds=timeout_seconds,
                max_workers=max_workers,
            )
        }
    result = {
        "schema_version": AUDIT_SCHEMA_VERSION,
        "audited_at": datetime.now(timezone.utc).isoformat(),
        "analysis_generated_at": str(payload.get("generated_at") or ""),
        "views": views,
    }
    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    temporary.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(destination)
    return result


def _audit_item(
    evidence_id: str,
    item: Mapping[str, Any],
    fetch: Callable[[str], Any],
) -> Dict[str, Any]:
    source_type = str(item.get("source_type") or "")
    original_url = str(item.get("url") or "").strip()
    request_url = canonicalize_official_policy_url(original_url) if source_type == "policy" else original_url
    record: Dict[str, Any] = {
        "evidence_id": evidence_id,
        "document_id": str(item.get("document_id") or ""),
        "source_type": source_type,
        "original_url": original_url,
        "request_url": request_url,
        "status": "invalid_url",
        "http_status": None,
        "final_url": "",
        "page_title": "",
    }
    if not _is_http_url(request_url):
        return record
    try:
        response = fetch(request_url)
    except Exception as exc:  # Network availability is evidence metadata, not a crash.
        record["status"] = "request_error"
        record["error"] = type(exc).__name__
        return record

    status_code = int(getattr(response, "status_code", 0) or 0)
    final_url = str(getattr(response, "url", request_url) or request_url)
    page_title = _extract_page_title(response)
    record.update({
        "http_status": status_code,
        "final_url": final_url if _is_http_url(final_url) else "",
        "page_title": page_title,
    })
    if status_code != 200:
        record["status"] = f"http_{status_code or 'error'}"
    elif not page_title:
        record["status"] = "title_unavailable"
    elif _titles_match(str(item.get("title") or ""), page_title):
        record["status"] = VERIFIED
    else:
        record["status"] = "title_mismatch"
    return record


def _is_http_url(value: str) -> bool:
    return urlsplit(str(value or "")).scheme.casefold() in {"http", "https"}


def _extract_page_title(response: Any) -> str:
    content = getattr(response, "content", b"")
    if isinstance(content, str):
        html = content
    else:
        raw = bytes(content or b"")
        head = raw[:8192].decode("latin-1", errors="ignore")
        declared = re.search(r"charset\s*=\s*[\"']?([a-zA-Z0-9_-]+)", head, re.IGNORECASE)
        encodings = [declared.group(1)] if declared else []
        encodings.extend([getattr(response, "encoding", ""), "utf-8", "gb18030"])
        html = ""
        for encoding in dict.fromkeys(value for value in encodings if value):
            try:
                html = raw.decode(str(encoding), errors="strict")
                break
            except (LookupError, UnicodeDecodeError):
                continue
        if not html:
            html = raw.decode("utf-8", errors="replace")
    match = re.search(r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
    if not match:
        return ""
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", match.group(1))).strip()


def _titles_match(expected: str, actual: str) -> bool:
    left = "".join(character.casefold() for character in expected if character.isalnum())
    right = "".join(character.casefold() for character in actual if character.isalnum())
    return bool(left and right and (left in right or right in left))


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit cached narrative evidence links.")
    parser.add_argument("--analysis", default="data/analysis/latest.json")
    parser.add_argument("--output", default="data/cache/evidence_link_audit.json")
    parser.add_argument("--timeout", type=float, default=15.0)
    parser.add_argument("--workers", type=int, default=6)
    args = parser.parse_args()
    result = audit_analysis_file(
        args.analysis,
        args.output,
        timeout_seconds=args.timeout,
        max_workers=args.workers,
    )
    for view, item in result["views"].items():
        records = item["evidence"].values()
        verified = sum(record.get("status") == VERIFIED for record in records)
        print(f"{view}: {verified}/{len(item['evidence'])} links verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
