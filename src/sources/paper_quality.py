"""Auditable journal-quality admission rules for paper records.

OpenAlex exposes publication venue metadata, but it does not provide a
licensed JCR impact-factor or quartile feed.  This module deliberately keeps
the institution-reviewed venue list in ``paper_quality`` configuration instead
of guessing a journal's rank from citation counts or publisher names.
"""

from __future__ import annotations

import re
from typing import Any, Dict, Iterable, Mapping


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


def evaluate_paper_quality(
    record: Mapping[str, Any], config: Mapping[str, Any]
) -> Dict[str, Any]:
    """Return an explainable whitelist decision for one formal paper record."""
    settings = _settings(config)
    if not settings.get("enabled", False):
        return {"allowed": True, "reason": "quality_gate_disabled"}

    journal_name = _text(record.get("journal_name") or record.get("venue"))
    issns = _record_issns(record)
    publication_type = _text(record.get("publication_type")).casefold()
    accepted_types = {
        _text(value).casefold()
        for value in settings.get("accepted_publication_types", _DEFAULT_ACCEPTED_TYPES)
        if _text(value)
    }
    if settings.get("require_formal_journal_article", True):
        if publication_type not in accepted_types:
            return _decision(
                False,
                "not_a_formal_journal_article",
                journal_name=journal_name,
                publication_type=publication_type,
            )
        if not journal_name and not issns:
            return _decision(
                False,
                "missing_journal_venue",
                publication_type=publication_type,
            )

    matched = _match_venue(journal_name, issns, settings.get("approved_venues", []))
    if matched is None:
        return _decision(
            False,
            "venue_not_whitelisted",
            journal_name=journal_name,
            issns=issns,
            publication_type=publication_type,
        )

    quartile = _text(matched.get("quartile")).upper()
    maximum_quartile = _quartile_number(settings.get("maximum_allowed_quartile", "Q2"))
    venue_quartile = _quartile_number(quartile)
    if venue_quartile is None:
        return _decision(
            False,
            "venue_quartile_unverified",
            journal_name=journal_name,
            venue_id=_text(matched.get("id") or matched.get("name")),
        )
    if maximum_quartile is not None and venue_quartile > maximum_quartile:
        return _decision(
            False,
            "venue_below_quartile_threshold",
            journal_name=journal_name,
            quartile=quartile,
            maximum_allowed_quartile=f"Q{maximum_quartile}",
            venue_id=_text(matched.get("id") or matched.get("name")),
        )

    return _decision(
        True,
        "whitelisted_q1_q2_journal",
        journal_name=journal_name,
        journal_issn_l=_text(record.get("journal_issn_l")),
        journal_publisher=_text(record.get("journal_publisher")),
        quartile=quartile,
        venue_id=_text(matched.get("id") or matched.get("name")),
        publication_type=publication_type,
    )


def is_high_impact_paper(record: Mapping[str, Any], config: Mapping[str, Any]) -> bool:
    """Return whether a paper passes the configured high-impact whitelist."""
    return bool(evaluate_paper_quality(record, config).get("allowed"))


def approved_venue_issns(config: Mapping[str, Any]) -> list[str]:
    return sorted({_text(v.get('issn_l')) for v in _settings(config).get('approved_venues', [])
                   if v.get('issn_l')})


def _settings(config: Mapping[str, Any]) -> Mapping[str, Any]:
    settings = config.get(QUALITY_CONFIG_KEY, {}) if isinstance(config, Mapping) else {}
    return settings if isinstance(settings, Mapping) else {}


def _match_venue(
    journal_name: str,
    issns: Iterable[str],
    approved_venues: Any,
) -> Mapping[str, Any] | None:
    normalized_name = _normalize(journal_name)
    normalized_issns = {_normalize_issn(value) for value in issns if _normalize_issn(value)}
    for candidate in approved_venues if isinstance(approved_venues, list) else []:
        if not isinstance(candidate, Mapping):
            continue
        candidate_issns = {
            _normalize_issn(value)
            for value in _text_list(candidate.get("issn_l"))
            + _text_list(candidate.get("issn"))
            if _normalize_issn(value)
        }
        # When the provider supplied an ISSN, it is the strongest available
        # identity signal.  Do not let a matching display name mask a
        # conflicting ISSN from an incorrectly mapped source record.
        if normalized_issns:
            if normalized_issns.intersection(candidate_issns):
                return candidate
            continue
        candidate_names = [candidate.get("name"), *(_text_list(candidate.get("aliases")))]
        if normalized_name and any(_normalize(name) == normalized_name for name in candidate_names):
            return candidate
    return None


def _record_issns(record: Mapping[str, Any]) -> list[str]:
    return [
        *_text_list(record.get("journal_issn_l")),
        *_text_list(record.get("journal_issn")),
    ]


def _quartile_number(value: Any) -> int | None:
    match = re.fullmatch(r"Q([1-4])", _text(value).upper())
    return int(match.group(1)) if match else None


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
