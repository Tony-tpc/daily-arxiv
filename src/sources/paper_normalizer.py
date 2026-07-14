"""Canonical paper normalization and research-scope filtering."""

from __future__ import annotations

import html
import re
from typing import Any, Dict, Iterable, List, Optional

from src.models.document_schema import SourceType, create_document


PAPER_SOURCE_NAMES = {"arxiv", "openalex_search"}


def normalize_paper_records(
    records: Iterable[Dict[str, Any]],
    source_name: str,
    config: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """Return valid canonical papers, excluding out-of-scope research directions."""
    normalized: List[Dict[str, Any]] = []
    for record in records:
        if not isinstance(record, dict):
            continue
        document = normalize_paper_record(record, source_name, config)
        if document is not None:
            normalized.append(document)
    return normalized


def normalize_paper_record(
    record: Dict[str, Any],
    source_name: str,
    config: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    """Map one legacy arXiv/OpenAlex record to the unified document schema."""
    result = dict(record)
    title = clean_paper_title(result.get("title"))
    record_id = str(
        result.get("id") or result.get("arxiv_id") or result.get("doi")
        or result.get("entry_url") or result.get("url") or ""
    ).strip()
    if not record_id or not title or is_excluded_paper(result, config, title=title):
        return None

    authors = _string_list(result.get("authors_or_orgs") or result.get("authors"))
    categories = _unique(
        _string_list(result.get("categories"))
        + _string_list(result.get("openalex_topics"))[:3]
    )
    topics = _string_list(result.get("openalex_topics"))
    institutions = _string_list(result.get("openalex_institutions"))
    entry_url = str(
        result.get("url") or result.get("entry_url") or result.get("pdf_url") or ""
    ).strip()
    doi = _clean_doi(result.get("doi"))
    arxiv_id = extract_arxiv_id(
        result.get("arxiv_id") or result.get("entry_url") or result.get("pdf_url")
    )
    if not arxiv_id and source_name == "arxiv" and not record_id.upper().startswith("W"):
        arxiv_id = extract_arxiv_id(record_id) or record_id
    if not (arxiv_id or doi or categories):
        return None

    source_label = str(result.get("source_name") or "").strip()
    if not source_label:
        source_label = "arXiv" if source_name == "arxiv" else "OpenAlex"
    summary = str(result.get("summary") or "")
    raw_text = str(result.get("raw_text") or result.get("abstract") or "")
    published_at = str(result.get("published_at") or result.get("published") or "")
    collected_at = str(result.get("collected_at") or result.get("fetched_at") or "")
    keywords = _unique(_string_list(result.get("keywords")) + categories + topics)
    tags = _unique(_string_list(result.get("tags")) + categories + topics)
    entities = _unique(
        _string_list(result.get("entities")) + authors + institutions
    )
    provenance = result.get("provenance")
    if not isinstance(provenance, dict):
        provenance = {}
    provenance = {
        "collected_via": provenance.get("collected_via") or source_name,
        "source_record_id": provenance.get("source_record_id") or record_id,
        "fetch_url": provenance.get("fetch_url") or entry_url,
        "metadata": provenance.get("metadata")
        if isinstance(provenance.get("metadata"), dict) else {},
    }

    canonical = create_document(
        SourceType.PAPER,
        id=record_id,
        source_name=source_label,
        title=title,
        summary=summary,
        core_viewpoints=_string_list(result.get("core_viewpoints")),
        research_relevance=str(result.get("research_relevance") or ""),
        worth_reading=result.get("worth_reading"),
        follow_up_suggestions=_string_list(result.get("follow_up_suggestions")),
        authors_or_orgs=authors,
        published_at=published_at,
        collected_at=collected_at,
        url=entry_url,
        raw_text=raw_text,
        keywords=keywords,
        tags=tags,
        entities=entities,
        themes=_string_list(result.get("themes")),
        tag_facets=result.get("tag_facets")
        if isinstance(result.get("tag_facets"), dict) else {},
        research_direction=_string_list(result.get("research_direction")),
        importance_score=result.get("importance_score"),
        ranking_score_breakdown=result.get("ranking_score_breakdown")
        if isinstance(result.get("ranking_score_breakdown"), dict) else {},
        ranking_factors=_string_list(result.get("ranking_factors")),
        ranking_penalties=result.get("ranking_penalties")
        if isinstance(result.get("ranking_penalties"), dict) else {},
        reading_suggestion=result.get("reading_suggestion")
        if isinstance(result.get("reading_suggestion"), dict) else {},
        provenance=provenance,
        canonical_url=str(result.get("canonical_url") or entry_url),
        duplicate_document_ids=_string_list(result.get("duplicate_document_ids")),
        duplicate_sources=_string_list(result.get("duplicate_sources")),
        duplicate_count=int(result.get("duplicate_count") or 0),
        related_documents=result.get("related_documents")
        if isinstance(result.get("related_documents"), list) else [],
        doi=doi,
        arxiv_id=arxiv_id,
        categories=categories,
    ).to_dict()

    for key, value in canonical.items():
        if key not in result or result[key] in (None, "", [], {}):
            result[key] = value
    result.update({
        "schema_version": canonical["schema_version"],
        "source_type": "paper",
        "source_name": source_label,
        "title": title,
        "authors_or_orgs": authors,
        "published_at": published_at,
        "collected_at": collected_at,
        "url": entry_url,
        "raw_text": raw_text,
        "keywords": keywords,
        "tags": tags,
        "entities": entities,
        "categories": categories,
        "doi": doi,
        "arxiv_id": arxiv_id,
        "provenance": provenance,
        "canonical_url": str(result.get("canonical_url") or entry_url),
    })
    return result


def clean_paper_title(value: Any) -> str:
    """Strip escaped or literal HTML markup from provider titles."""
    text = html.unescape(str(value or ""))
    text = re.sub(r"<[^>]*>", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return re.sub(r"-\s+", "-", text)


def extract_arxiv_id(value: Any) -> Optional[str]:
    """Return a bare arXiv identifier from a URL or identifier string."""
    text = str(value or "").strip()
    if not text:
        return None
    match = re.search(r"arxiv\.org/(?:abs|pdf)/([^/?#]+)", text, flags=re.IGNORECASE)
    if match:
        return re.sub(r"\.pdf$", "", match.group(1), flags=re.IGNORECASE)
    if re.fullmatch(r"(?:[a-z-]+/)?\d{4}\.\d{4,5}(?:v\d+)?", text, flags=re.IGNORECASE):
        return text
    return None


def is_excluded_paper(
    record: Dict[str, Any],
    config: Dict[str, Any],
    *,
    title: str = "",
) -> bool:
    """Return whether a paper belongs to an explicitly excluded research direction."""
    terms = _unique(
        _string_list(config.get("negative_keywords"))
        + _string_list(config.get("research_profile", {}).get("excluded_directions"))
        + _string_list(config.get("sources", {}).get("arxiv", {}).get("exclude_keywords"))
        + _string_list(
            config.get("sources", {}).get("openalex_search", {}).get("exclude_keywords")
        )
    )
    if not terms:
        return False
    searchable = " ".join([
        title or clean_paper_title(record.get("title")),
        str(record.get("abstract") or record.get("raw_text") or ""),
        " ".join(_string_list(record.get("categories"))),
        " ".join(_string_list(record.get("openalex_topics"))),
        " ".join(_string_list(record.get("openalex_concepts"))),
    ]).casefold()
    return any(term.casefold() in searchable for term in terms if term.strip())


def _clean_doi(value: Any) -> Optional[str]:
    text = str(value or "").strip()
    text = re.sub(r"^(?:https?://(?:dx\.)?doi\.org/|doi:\s*)", "", text, flags=re.IGNORECASE)
    return text or None


def _string_list(value: Any) -> List[str]:
    if isinstance(value, (list, tuple, set)):
        return [str(item).strip() for item in value if str(item).strip()]
    cleaned = str(value or "").strip()
    return [cleaned] if cleaned else []


def _unique(values: Iterable[str]) -> List[str]:
    return list(dict.fromkeys(value for value in values if value))
