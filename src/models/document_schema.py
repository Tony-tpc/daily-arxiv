"""Unified document schema for multi-source research intelligence."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


SCHEMA_VERSION = "1.0"


class SourceType(str, Enum):
    """Supported source types for normalized documents."""

    PAPER = "paper"
    POLICY = "policy"
    NEWS = "news"
    INDUSTRY_REPORT = "industry_report"


@dataclass
class ReadingSuggestion:
    """Structured reading recommendation."""

    why_relevant: str = ""
    read_priority: str = "medium"
    recommended_action: str = "review"
    related_topics: List[str] = field(default_factory=list)


@dataclass
class Provenance:
    """Document provenance metadata."""

    collected_via: str = ""
    source_record_id: str = ""
    fetch_url: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DocumentSchema:
    """Canonical document schema spanning papers, policies, news, and reports."""

    id: str
    source_type: str
    source_name: str
    title: str
    summary: str = ""
    core_viewpoints: List[str] = field(default_factory=list)
    research_relevance: str = ""
    worth_reading: Optional[bool] = None
    follow_up_suggestions: List[str] = field(default_factory=list)
    authors_or_orgs: List[str] = field(default_factory=list)
    published_at: str = ""
    collected_at: str = ""
    url: str = ""
    raw_text: str = ""
    keywords: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    entities: List[str] = field(default_factory=list)
    themes: List[str] = field(default_factory=list)
    tag_facets: Dict[str, List[str]] = field(default_factory=dict)
    research_direction: List[str] = field(default_factory=list)
    importance_score: Optional[float] = None
    ranking_score_breakdown: Dict[str, float] = field(default_factory=dict)
    ranking_factors: List[str] = field(default_factory=list)
    ranking_penalties: Dict[str, float] = field(default_factory=dict)
    reading_suggestion: ReadingSuggestion = field(default_factory=ReadingSuggestion)
    provenance: Provenance = field(default_factory=Provenance)
    canonical_url: str = ""
    duplicate_document_ids: List[str] = field(default_factory=list)
    duplicate_sources: List[str] = field(default_factory=list)
    duplicate_count: int = 0
    related_documents: List[Dict[str, Any]] = field(default_factory=list)
    schema_version: str = SCHEMA_VERSION

    # Paper-specific fields
    doi: Optional[str] = None
    arxiv_id: Optional[str] = None
    categories: List[str] = field(default_factory=list)

    # Policy-specific fields
    issuing_body: Optional[str] = None
    policy_level: Optional[str] = None
    region: Optional[str] = None
    effective_date: Optional[str] = None
    document_type: Optional[str] = None
    impact_areas: List[str] = field(default_factory=list)
    policy_strength: Optional[str] = None
    core_policy_direction: Optional[str] = None
    technology_directions: List[str] = field(default_factory=list)
    potential_impact: Optional[str] = None

    # News-specific fields
    media_name: Optional[str] = None
    event_type: Optional[str] = None

    # Industry report-specific fields
    institution: Optional[str] = None
    report_type: Optional[str] = None
    topic_directions: List[str] = field(default_factory=list)
    industry_progress: Optional[str] = None
    trend_assessment: Optional[str] = None

    def __post_init__(self) -> None:
        if isinstance(self.reading_suggestion, dict):
            self.reading_suggestion = ReadingSuggestion(**self.reading_suggestion)
        if isinstance(self.provenance, dict):
            self.provenance = Provenance(**self.provenance)

    def validate(self) -> None:
        """Validate common and source-specific requirements."""
        if not self.id.strip():
            raise ValueError("Document id is required")
        if not self.title.strip():
            raise ValueError("Document title is required")
        if not self.source_name.strip():
            raise ValueError("Document source_name is required")

        try:
            source_type = SourceType(self.source_type)
        except ValueError as exc:
            raise ValueError(f"Unsupported source_type: {self.source_type}") from exc

        if source_type == SourceType.PAPER and not (self.arxiv_id or self.doi or self.categories):
            raise ValueError("Paper documents require arxiv_id, doi, or categories")
        if source_type == SourceType.POLICY and not self.issuing_body:
            raise ValueError("Policy documents require issuing_body")
        if source_type == SourceType.NEWS and not self.media_name:
            raise ValueError("News documents require media_name")
        if source_type == SourceType.INDUSTRY_REPORT and not self.institution:
            raise ValueError("Industry report documents require institution")

    def to_dict(self) -> Dict[str, Any]:
        """Serialize document into a JSON-friendly dict."""
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "DocumentSchema":
        """Create a schema instance from a dictionary payload."""
        normalized = dict(payload)

        reading_suggestion = normalized.get("reading_suggestion", {}) or {}
        provenance = normalized.get("provenance", {}) or {}

        normalized["reading_suggestion"] = (
            reading_suggestion
            if isinstance(reading_suggestion, ReadingSuggestion)
            else ReadingSuggestion(**reading_suggestion)
        )
        normalized["provenance"] = (
            provenance if isinstance(provenance, Provenance) else Provenance(**provenance)
        )

        document = cls(**normalized)
        document.validate()
        return document


def create_document(source_type: SourceType | str, **kwargs: Any) -> DocumentSchema:
    """Convenience factory for creating validated document schema instances."""
    normalized_source_type = source_type.value if isinstance(source_type, SourceType) else str(source_type)
    document = DocumentSchema(source_type=normalized_source_type, **kwargs)
    document.validate()
    return document
