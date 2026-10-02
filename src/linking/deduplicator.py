"""Deduplicate canonical documents and build explainable cross-source links."""

from __future__ import annotations

import copy
import re
import unicodedata
from difflib import SequenceMatcher
from typing import Any, Dict, Iterable, List, Tuple
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from src.sources.observations import policy_identity


RELATION_TYPES = {
    frozenset(("paper", "policy")): "paper_policy",
    frozenset(("paper", "news")): "paper_news",
    frozenset(("paper", "industry_report")): "paper_industry_report",
    frozenset(("policy", "news")): "policy_news",
    frozenset(("policy", "industry_report")): "policy_industry_report",
}

GENERIC_LINK_TERMS = {
    "cn", "中国", "能源", "能源系统", "政策治理", "产业动态", "新闻事件",
    "paper", "policy", "news", "industry_report", "high", "medium", "low",
    "notice", "regulation", "新闻", "政策", "行业报告",
}

LIST_FIELDS = {
    "authors_or_orgs", "keywords", "tags", "entities", "themes",
    "research_direction", "categories", "impact_areas", "technology_directions",
    "topic_directions", "ranking_factors", "follow_up_suggestions",
}

TRACKING_QUERY_KEYS = {
    "spm", "from", "source", "ref", "referrer", "campaign", "tracking_id",
}


class Deduplicator:
    """Merge true duplicates, then relate complementary source types."""

    def __init__(self, config: Dict[str, Any] | None = None):
        settings = (config or {}).get("linking", {})
        self.title_similarity_threshold = float(
            settings.get("title_similarity_threshold", 0.92)
        )
        self.relation_threshold = float(settings.get("relation_threshold", 0.35))
        self.max_related = int(settings.get("max_related_per_document", 8))

    def process(self, documents: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Return de-duplicated documents with bidirectional relation references."""
        prepared = [copy.deepcopy(item) for item in documents if isinstance(item, dict)]
        for document in prepared:
            document["canonical_url"] = canonicalize_url(document.get("url"))
            document["related_documents"] = []

        unique_documents, duplicate_groups = self.deduplicate(prepared)
        relation_count = self.link_related(unique_documents)
        return {
            "documents": unique_documents,
            "input_count": len(prepared),
            "output_count": len(unique_documents),
            "duplicates_removed": len(prepared) - len(unique_documents),
            "duplicate_groups": duplicate_groups,
            "relation_count": relation_count,
        }

    def deduplicate(
        self, documents: List[Dict[str, Any]]
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Union records matching DOI, canonical URL, or same-type title similarity."""
        parent = list(range(len(documents)))
        group_dois = [{normalize_doi(d.get("doi") or d.get("url"))} - {""} for d in documents]
        group_policies = [{policy_identity(d)} - {""} for d in documents]

        def find(index: int) -> int:
            while parent[index] != index:
                parent[index] = parent[parent[index]]
                index = parent[index]
            return index

        def union(left: int, right: int) -> None:
            left_root, right_root = find(left), find(right)
            if left_root != right_root:
                if group_dois[left_root] and group_dois[right_root] and group_dois[left_root] != group_dois[right_root]:
                    return
                if group_policies[left_root] and group_policies[right_root] and group_policies[left_root] != group_policies[right_root]:
                    return
                parent[right_root] = left_root
                group_dois[left_root].update(group_dois[right_root])
                group_policies[left_root].update(group_policies[right_root])

        doi_index: Dict[str, int] = {}
        url_index: Dict[str, int] = {}
        for index, document in enumerate(documents):
            doi = normalize_doi(document.get("doi") or document.get("url"))
            canonical_url = canonicalize_url(document.get("url"))
            if doi:
                union(index, doi_index.setdefault(doi, index))
            if canonical_url:
                union(index, url_index.setdefault(canonical_url, index))

        buckets: Dict[tuple, set[int]] = {}
        for index, document in enumerate(documents):
            kind = str(document.get("source_type"))
            if kind == "paper":
                year = str(document.get("published_at") or document.get("published") or "")[:4]
                authors = document.get("authors_or_orgs") or document.get("authors") or []
                keys = [(kind, year, normalize_title(str(a))) for a in authors if year and a]
            else:
                keys = [(kind,)]
            for key in keys:
                buckets.setdefault(key, set()).add(index)
        checked = set()
        for indices in buckets.values():
            for left in sorted(indices):
                for right in sorted(i for i in indices if i > left):
                    if (left, right) in checked or find(left) == find(right):
                        continue
                    checked.add((left, right))
                    left_title = normalize_title(documents[left].get("title"))
                    right_title = normalize_title(documents[right].get("title"))
                    if min(len(left_title), len(right_title)) >= 12 and SequenceMatcher(None, left_title, right_title).ratio() >= self.title_similarity_threshold:
                        union(left, right)

        grouped: Dict[int, List[Dict[str, Any]]] = {}
        for index, document in enumerate(documents):
            grouped.setdefault(find(index), []).append(document)

        unique_documents: List[Dict[str, Any]] = []
        duplicate_groups: List[Dict[str, Any]] = []
        for group in grouped.values():
            merged = self._merge_group(group)
            unique_documents.append(merged)
            if len(group) > 1:
                duplicate_groups.append({
                    "canonical_id": merged.get("id"),
                    "document_ids": [item.get("id") for item in group],
                    "sources": _unique(item.get("source_name") for item in group),
                    "count": len(group),
                })
        return unique_documents, duplicate_groups

    def link_related(self, documents: List[Dict[str, Any]]) -> int:
        """Attach only the five supported cross-source relationship types."""
        relation_count = 0
        for left_index, left in enumerate(documents):
            for right in documents[left_index + 1:]:
                relation_type = RELATION_TYPES.get(frozenset((
                    str(left.get("source_type") or ""),
                    str(right.get("source_type") or ""),
                )))
                if not relation_type:
                    continue
                score, shared_topics, reason = self._relation_evidence(left, right)
                if score < self.relation_threshold:
                    continue
                left["related_documents"].append(
                    self._reference(right, relation_type, score, shared_topics, reason)
                )
                right["related_documents"].append(
                    self._reference(left, relation_type, score, shared_topics, reason)
                )
                relation_count += 1

        for document in documents:
            related = sorted(
                document.get("related_documents", []),
                key=lambda item: (-float(item.get("score") or 0), str(item.get("title") or "")),
            )[: self.max_related]
            document["related_documents"] = related
            web_card = document.get("web_card")
            if isinstance(web_card, dict):
                web_card["related_documents"] = related
                web_card["duplicate_count"] = document.get("duplicate_count", 0)
                web_card["duplicate_sources"] = document.get("duplicate_sources", [])
        return relation_count

    def _merge_group(self, group: List[Dict[str, Any]]) -> Dict[str, Any]:
        # Formal publisher metadata wins over repository/preprint descriptions.
        def authority(item):
            provider = item.get("source_record_provider", "")
            return (item.get("publication_type") in {"article", "journal-article"},
                    provider == "crossref", self._quality(item))
        ordered = sorted(group, key=authority, reverse=True)
        merged = copy.deepcopy(ordered[0])
        for candidate in ordered[1:]:
            for key, value in candidate.items():
                if key in LIST_FIELDS:
                    merged[key] = _unique([*_as_list(merged.get(key)), *_as_list(value)])
                elif merged.get(key) in (None, "", [], {}):
                    merged[key] = copy.deepcopy(value)

        ids = _unique(item.get("id") for item in group)
        sources = _unique(item.get("source_name") for item in group)
        merged["duplicate_document_ids"] = [
            item for item in ids if item != str(merged.get("id") or "")
        ]
        merged["duplicate_sources"] = sources if len(group) > 1 else []
        merged["duplicate_count"] = max(0, len(group) - 1)
        if merged.get('source_type') == 'paper':
            merged['is_retracted'] = any(item.get('is_retracted') for item in group)
            for field in ('references', 'version_links', 'publication_types', 'journal_issn'):
                merged[field] = _unique(v for item in group for v in _as_list(item.get(field)))
            merged['publication_types'] = _unique(merged['publication_types'] + [item.get('publication_type') for item in group])
            merged['discovered_via'] = _unique(p for item in group for p in
                (item.get('discovered_via') or [item.get('source_record_provider') or item.get('source_name')]))
            merged['field_sources'] = {
                field: _unique(source for item in group for source in _as_list(
                    (item.get('field_sources') or {}).get(field) or item.get('source_name'))
                    if item.get('abstract' if field == 'abstract' else 'journal_name' if field == 'journal' else field))
                for field in ('abstract', 'journal', 'publication_type')}
            merged['abstract_status'] = 'available' if merged.get('abstract') or merged.get('raw_text') else 'missing'
        merged["canonical_url"] = canonicalize_url(merged.get("url"))
        merged["related_documents"] = []

        provenance = copy.deepcopy(merged.get("provenance") or {})
        metadata = copy.deepcopy(provenance.get("metadata") or {})
        from src.sources.observations import observations
        observed = {}
        for item in group:
            for observation in observations(item):
                key = (observation.get('source_id'), observation.get('url'), observation.get('published_at'))
                observed[key] = copy.deepcopy(observation)
        if observed:
            metadata['observations'] = list(observed.values())
        if len(group) > 1:
            metadata["merged_documents"] = [
                {
                    "id": item.get("id"),
                    "source_type": item.get("source_type"),
                    "source_name": item.get("source_name"),
                    "url": item.get("url"),
                }
                for item in group
            ]
        provenance["metadata"] = metadata
        merged["provenance"] = provenance
        return merged

    @staticmethod
    def _quality(document: Dict[str, Any]) -> float:
        filled = sum(
            1 for value in document.values() if value not in (None, "", [], {})
        )
        return filled + min(len(str(document.get("raw_text") or "")) / 1000, 5)

    @staticmethod
    def _reference(
        document: Dict[str, Any],
        relation_type: str,
        score: float,
        shared_topics: List[str],
        reason: str,
    ) -> Dict[str, Any]:
        return {
            "id": document.get("id"),
            "source_type": document.get("source_type"),
            "source_name": document.get("source_name"),
            "title": document.get("title"),
            "url": document.get("url"),
            "relationship": relation_type,
            "score": round(score, 3),
            "shared_topics": shared_topics,
            "reason": reason,
        }

    @staticmethod
    def _relation_evidence(
        left: Dict[str, Any], right: Dict[str, Any]
    ) -> Tuple[float, List[str], str]:
        shared_directions = _shared(left, right, "research_direction")
        shared_themes = _shared(left, right, "themes")
        shared_tags = _shared(left, right, "tags")
        shared_entities = _shared(left, right, "entities")
        title_similarity = SequenceMatcher(
            None, normalize_title(left.get("title")), normalize_title(right.get("title"))
        ).ratio()

        score = 0.0
        if shared_directions:
            score += 0.5
        if shared_themes:
            score += 0.3
        if shared_tags:
            score += 0.35
        if shared_entities:
            score += 0.2
        if title_similarity >= 0.55:
            score += 0.35 * title_similarity
        score = min(1.0, score)

        shared_topics = _unique(
            [*shared_directions, *shared_themes, *shared_tags, *shared_entities]
        )[:8]
        reasons = []
        if shared_directions:
            reasons.append("共享研究方向：" + "、".join(shared_directions[:3]))
        if shared_themes:
            reasons.append("共享主题：" + "、".join(shared_themes[:3]))
        if shared_tags:
            reasons.append("共享标签：" + "、".join(shared_tags[:3]))
        if shared_entities:
            reasons.append("共享实体：" + "、".join(shared_entities[:3]))
        if title_similarity >= 0.55:
            reasons.append(f"标题相似度 {title_similarity:.0%}")
        return score, shared_topics, "；".join(reasons)


def normalize_doi(value: Any) -> str:
    """Normalize DOI literals and doi.org URLs."""
    text = str(value or "").strip().casefold()
    match = re.search(r"10\.\d{4,9}/[^\s?#]+", text)
    return match.group(0).rstrip("/.,;)") if match else ""


def canonicalize_url(value: Any) -> str:
    """Normalize URL casing, fragments, default ports, and tracking parameters."""
    raw = str(value or "").strip()
    if not raw:
        return ""
    parts = urlsplit(raw)
    if not parts.scheme or not parts.netloc:
        return raw.rstrip("/")
    hostname = (parts.hostname or "").casefold()
    port = parts.port
    netloc = hostname
    if port and not ((parts.scheme.casefold() == "http" and port == 80) or (parts.scheme.casefold() == "https" and port == 443)):
        netloc = f"{hostname}:{port}"
    query = [
        (key, val)
        for key, val in parse_qsl(parts.query, keep_blank_values=True)
        if not key.casefold().startswith("utm_") and key.casefold() not in TRACKING_QUERY_KEYS
    ]
    return urlunsplit((
        parts.scheme.casefold(), netloc, re.sub(r"/{2,}", "/", parts.path).rstrip("/"),
        urlencode(sorted(query)), "",
    ))


def normalize_title(value: Any) -> str:
    text = unicodedata.normalize("NFKC", str(value or "")).casefold()
    return re.sub(r"[^0-9a-z\u4e00-\u9fff]+", "", text)


def _shared(left: Dict[str, Any], right: Dict[str, Any], field: str) -> List[str]:
    left_values = {_term_key(value): str(value).strip() for value in _as_list(left.get(field))}
    right_values = {_term_key(value): str(value).strip() for value in _as_list(right.get(field))}
    keys = [key for key in left_values.keys() & right_values.keys() if key not in GENERIC_LINK_TERMS]
    return [left_values[key] for key in sorted(keys)]


def _term_key(value: Any) -> str:
    return unicodedata.normalize("NFKC", str(value or "")).strip().casefold()


def _as_list(value: Any) -> List[Any]:
    if isinstance(value, (list, tuple, set)):
        return list(value)
    return [value] if value not in (None, "") else []


def _unique(values: Iterable[Any]) -> List[str]:
    result: List[str] = []
    seen = set()
    for value in values:
        text = str(value or "").strip()
        key = _term_key(text)
        if text and key not in seen:
            seen.add(key)
            result.append(text)
    return result
