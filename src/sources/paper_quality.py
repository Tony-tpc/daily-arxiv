"""Auditable journal-quality admission rules for paper records.

OpenAlex exposes publication venue metadata, but it does not provide a
verified CAS partition feed.  This module deliberately keeps
the institution-reviewed venue list in ``paper_quality`` configuration instead
of guessing a journal's rank from citation counts or publisher names.
"""

from __future__ import annotations

import re
import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Mapping


QUALITY_CONFIG_KEY = "paper_quality"
_DEFAULT_ACCEPTED_TYPES = {"article", "journal-article"}


def enrich_openalex_venue_metadata(
    record: Mapping[str, Any], work: Mapping[str, Any]
) -> Dict[str, Any]:
    """Copy the formal-publication metadata needed by the quality gate.

    The OpenAlex ``primary_location.source`` object is the canonical venue
    source.  Older cached records sometimes omit it, so the result is still a
    valid record but will fail a strict whitelist instead of being guessed.
    """
    enriched = dict(record)
    location = work.get("primary_location")
    if not isinstance(location, Mapping):
        location = {}
    source = location.get("source")
    if not isinstance(source, Mapping):
        source = work.get("host_venue")
    if not isinstance(source, Mapping):
        source = {}

    venue = _text(source.get("display_name") or source.get("name"))
    issn_l = _text(source.get("issn_l"))
    issns = _text_list(source.get("issn"))
    publisher = _text(
        source.get("host_organization_name")
        or source.get("publisher")
        or location.get("publisher")
    )
    publication_type = _text(work.get("type") or record.get("publication_type"))

    if publication_type:
        enriched["publication_type"] = publication_type
    if venue:
        enriched["journal_name"] = venue
        enriched["venue"] = venue
    if issn_l:
        enriched["journal_issn_l"] = issn_l
    if issns:
        enriched["journal_issn"] = issns
    if publisher:
        enriched["journal_publisher"] = publisher
    return enriched


@lru_cache(maxsize=8)
def _load_evidence(path: str, modified: int, inline: str) -> tuple[list[dict], dict, dict]:
    venues = json.loads(inline)
    if path:
        venues += json.loads(Path(path).read_text(encoding="utf-8")).get("venues", [])
    editions = [v.get("edition_year") for v in venues if valid_venue_evidence(v)]
    latest = max(editions, default=0)
    verified = [v for v in venues if valid_venue_evidence(v) and v["edition_year"] == latest]
    names, issns = {}, {}
    for venue in verified:
        for name in [venue.get("name"), *_text_list(venue.get("aliases"))]:
            names[_normalize(name)] = venue
        for issn in [venue.get("issn_l"), *_text_list(venue.get("issn"))]:
            if issn:
                issns[_normalize_issn(issn)] = venue
    return verified, names, issns


def _evidence(config):
    settings = _settings(config)
    path = Path(settings.get("venue_evidence_path") or "__missing_cas_evidence__")
    return _load_evidence(str(path) if path.is_file() else "", path.stat().st_mtime_ns if path.is_file() else 0,
                          json.dumps(settings.get("approved_venues", []), sort_keys=True))


def venue_evidence(config: Mapping[str, Any]) -> list[dict]:
    return _evidence(config)[0]


def valid_venue_evidence(venue: Mapping[str, Any]) -> bool:
    from datetime import date, datetime
    try:
        checked = datetime.fromisoformat(str(venue.get("verified_at", "")).replace("Z", "+00:00"))
        return bool(venue.get("classification_system") == "cas"
                    and venue.get("category_level") == "major"
                    and isinstance(venue.get("edition_year"), int)
                    and 2004 <= venue["edition_year"] <= date.today().year
                    and venue.get("partition") in (1, 2, 3, 4)
                    and venue.get("major_category") and (venue.get("issn_l") or venue.get("issn"))
                    and (str(venue.get("evidence_url", "")).startswith("https://") or
                         (re.fullmatch(r"[0-9a-f]{64}", str(venue.get("evidence_sha256", "")))
                          and venue.get("evidence_file") and venue.get("evidence_page")))
                    and checked.date() <= date.today())
    except (ValueError, TypeError):
        return False


def evaluate_paper_quality(record: Mapping[str, Any], config: Mapping[str, Any]) -> Dict[str, Any]:
    """Admit original journal articles with verified current CAS major partitions."""
    settings = _settings(config)
    if not settings.get("enabled", False):
        return {"allowed": True, "reason": "quality_gate_disabled"}
    title = _text(record.get("title")).casefold()
    abstract = _text(record.get('abstract') or record.get('raw_text')).casefold()
    types = [_text(record.get("publication_type")).casefold(),
             *[t.casefold() for t in _text_list(record.get("publication_types"))]]
    if record.get("is_retracted"):
        return _decision(False, "retracted")
    excluded = {"review", "editorial", "erratum", "correction", "retraction", "survey", "tutorial"}
    if excluded.intersection(types) or re.search(r"\b(review|survey|editorial|erratum|corrigendum|retraction|bibliometric|meta-analysis)\b|综述|述评|撤稿|勘误", title):
        return _decision(False, "not_original_research")
    if re.search(r'\bthis (?:survey|review|tutorial)\b|\bthis (?:paper|article) (?:presents|provides|offers) (?:a|an) (?:comprehensive |systematic |critical )?(?:survey|review|tutorial)\b', abstract):
        return _decision(False, 'not_original_research')
    if types[0] not in _DEFAULT_ACCEPTED_TYPES:
        return _decision(False, "not_a_formal_journal_article")
    journal = _text(record.get("journal_name") or record.get("venue"))
    issns = _record_issns(record)
    for venue in settings.get('excluded_venues', []):
        if (_normalize_issn(venue.get('issn_l')) in {_normalize_issn(i) for i in issns}
                or _normalize(journal) == _normalize(venue.get('name'))):
            return _decision(False, 'not_original_research', evidence_url=venue.get('evidence_url'))
    if not journal and not issns:
        return _decision(False, "missing_journal_venue")
    _, by_name, by_issn = _evidence(config)
    matches = [by_issn[_normalize_issn(i)] for i in issns if _normalize_issn(i) in by_issn]
    matched = matches[0] if matches else by_name.get(_normalize(journal)) if not issns else None
    if matched is None:
        return _decision(False, "cas_partition_unverified", journal_name=journal, issns=issns)
    evidence = {key: matched[key] for key in ("classification_system", "category_level", "edition_year",
                "major_category", "partition", "evidence_url", "verified_at", "evidence_file",
                "evidence_sha256", "evidence_page") if key in matched}
    if matched["partition"] > 2:
        return _decision(False, "venue_below_partition_threshold", **evidence)
    return _decision(True, "verified_cas_major_1_2", journal_name=journal,
                     venue_id=matched.get("id") or matched.get("name"), **evidence)


def is_high_impact_paper(record: Mapping[str, Any], config: Mapping[str, Any]) -> bool:
    return bool(evaluate_paper_quality(record, config).get("allowed"))


def approved_venue_issns(config: Mapping[str, Any]) -> list[str]:
    return sorted({_text(v.get("issn_l") or _text_list(v.get("issn"))[0])
                   for v in venue_evidence(config) if v["partition"] <= 2})


def _settings(config: Mapping[str, Any]) -> Mapping[str, Any]:
    settings = config.get(QUALITY_CONFIG_KEY, {}) if isinstance(config, Mapping) else {}
    return settings if isinstance(settings, Mapping) else {}


def _record_issns(record: Mapping[str, Any]) -> list[str]:
    return [
        *_text_list(record.get("journal_issn_l")),
        *_text_list(record.get("journal_issn")),
    ]


def _decision(allowed: bool, reason: str, **metadata: Any) -> Dict[str, Any]:
    return {
        "allowed": allowed,
        "reason": reason,
        **{key: value for key, value in metadata.items() if value not in (None, "", [], {})},
    }


def _normalize(value: Any) -> str:
    text = _text(value).casefold().replace("&", " and ")
    return re.sub(r"[^a-z0-9]+", "", text)


def _normalize_issn(value: Any) -> str:
    return re.sub(r"[^0-9xX]", "", _text(value)).upper()


def _text(value: Any) -> str:
    return str(value or "").strip()


def _text_list(value: Any) -> list[str]:
    if isinstance(value, (list, tuple, set)):
        return [_text(item) for item in value if _text(item)]
    return [_text(value)] if _text(value) else []
