"""OpenAlex discovery with full pagination and evidence-bearing metadata."""
from __future__ import annotations
from .academic import PagedPaperAdapter, PaperPage, PaperQuery, clean_doi
from .paper_quality import enrich_openalex_venue_metadata


def reconstruct_abstract(index: dict | None) -> str:
    positions = {}
    for word, offsets in (index or {}).items():
        for position in offsets if isinstance(offsets, list) else []:
            if isinstance(position, int) and position >= 0:
                positions[position] = word
    return " ".join(positions[p] for p in sorted(positions))


class OpenAlexSearchAdapter(PagedPaperAdapter):
    source_name = "openalex_search"
    base_url = "https://api.openalex.org"
    select_fields = ["id", "doi", "title", "publication_date", "publication_year", "type",
                     "primary_location", "locations", "authorships", "topics", "primary_topic",
                     "cited_by_count", "referenced_works", "ids", "updated_date",
                     "abstract_inverted_index", "is_retracted"]

    @property
    def headers(self) -> dict:
        key = self.config.get("sources", {}).get("openalex", {}).get("api_key", "")
        return {"Authorization": f"Bearer {key}"} if key else {}

    def fetch_page(self, query: PaperQuery, date_from: str, date_to: str, cursor: str) -> PaperPage:
        filters = [f"from_publication_date:{date_from}", f"to_publication_date:{date_to}"]
        if query.issn:
            filters.append(f"primary_location.source.issn:{query.issn}")
        if query.relation == "cited_by":
            filters.append(f"cites:{query.seed}")
        params = {"filter": ",".join(filters), "per_page": self.page_size, "cursor": cursor,
                  "select": ",".join(self.select_fields), "sort": "publication_date:asc"}
        if query.term:
            params["search"] = query.term
        payload = self.get_json(f"{self.base_url}/works", params, self.headers)
        works = payload["results"]
        return PaperPage([self._work_to_record(w) for w in works],
                         payload.get("meta", {}).get("next_cursor") if works else None,
                         payload.get("meta", {}).get("count"))

    def lookup(self, identifier: str) -> dict:
        return self._work_to_record(self.get_json(f"{self.base_url}/works/{identifier}",
                                    {"select": ",".join(self.select_fields)}, self.headers))

    def _work_to_record(self, work: dict) -> dict:
        doi = clean_doi(work.get("doi"))
        location = work.get("primary_location") or {}
        topics = [t["display_name"] for t in work.get("topics", []) if t.get("display_name")]
        authorships = work.get("authorships") or []
        institutions = list(dict.fromkeys(i["display_name"] for a in authorships for i in a.get("institutions", []) if i.get("display_name")))
        record = {
            "id": str(work.get("id", "")).rsplit("/", 1)[-1], "openalex_id": work.get("id"),
            "doi": doi, "title": work.get("title") or work.get("display_name", ""),
            "authors": [a.get("author", {}).get("display_name", "") for a in authorships],
            "abstract": reconstruct_abstract(work.get("abstract_inverted_index")),
            "published": work.get("publication_date") or str(work.get("publication_year") or ""),
            "entry_url": f"https://doi.org/{doi}" if doi else location.get("landing_page_url") or work.get("id", ""),
            "pdf_url": location.get("pdf_url") or "", "categories": topics[:3],
            "openalex_topics": topics, "openalex_institutions": institutions,
            "openalex_referenced_works": work.get("referenced_works", []),
            "references": work.get("referenced_works", []), "citation_count": work.get("cited_by_count", 0),
            "publication_type": work.get("type", ""), "is_retracted": work.get("is_retracted", False),
            "source_name": "OpenAlex", "source_record_provider": self.source_name,
            "version_links": [l.get("landing_page_url") for l in work.get("locations", []) if l.get("landing_page_url")],
            "field_sources": {"abstract": "openalex", "publication_type": "openalex", "journal": "openalex"},
        }
        return enrich_openalex_venue_metadata(record, work)
