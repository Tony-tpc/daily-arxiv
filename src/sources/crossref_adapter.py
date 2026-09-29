"""Independent DOI and journal discovery through Crossref."""
from __future__ import annotations
from urllib.parse import quote
from .academic import PagedPaperAdapter, PaperPage, PaperQuery, clean_doi
from .paper_normalizer import clean_paper_title


def first(value):
    return str(value[0]) if isinstance(value, list) and value else str(value or "")


def publication_date(work: dict) -> str:
    for field in ("published", "published-online", "published-print", "issued"):
        parts = (work.get(field) or {}).get("date-parts", [[]])[0]
        if parts:
            return "-".join(f"{int(p):04d}" if i == 0 else f"{int(p):02d}" for i, p in enumerate(parts[:3]))
    return ""


class CrossrefAdapter(PagedPaperAdapter):
    source_name = "crossref"
    base_url = "https://api.crossref.org"

    def fetch_page(self, query: PaperQuery, date_from: str, date_to: str, cursor: str) -> PaperPage:
        path = f"/journals/{query.issn}/works" if query.issn else "/works"
        params = {"filter": f"type:journal-article,from-pub-date:{date_from},until-pub-date:{date_to}",
                  "rows": self.page_size, "cursor": cursor}
        if query.term:
            params["query.bibliographic"] = query.term
        if self.settings.get("mailto"):
            params["mailto"] = self.settings["mailto"]
        payload = self.get_json(self.base_url + path, params, {"User-Agent": "daily-arxiv/2.0"})["message"]
        works = payload["items"]
        return PaperPage([self.work_to_record(w) for w in works],
                         payload.get("next-cursor") if len(works) >= self.page_size else None,
                         payload.get("total-results"))

    def lookup(self, doi: str) -> dict:
        return self.work_to_record(self.get_json(f"{self.base_url}/works/{quote(clean_doi(doi), safe='')}")["message"])

    @staticmethod
    def work_to_record(work: dict) -> dict:
        doi = clean_doi(work.get("DOI"))
        return {
            "id": f"crossref:{doi}", "doi": doi, "title": clean_paper_title(first(work.get("title"))),
            "abstract": clean_paper_title(work.get("abstract", "")),
            "authors": [" ".join(filter(None, [a.get("given"), a.get("family")])) or a.get("name", "") for a in work.get("author", [])],
            "published": publication_date(work), "entry_url": f"https://doi.org/{doi}", "pdf_url": "",
            "publication_type": work.get("type", ""), "journal_name": first(work.get("container-title")),
            "journal_issn": work.get("ISSN", []), "journal_publisher": work.get("publisher", ""),
            "citation_count": work.get("is-referenced-by-count", 0),
            "references": [f"doi:{clean_doi(r['DOI'])}" for r in work.get("reference", []) if r.get("DOI")],
            "is_retracted": any("retract" in str(u.get("type", "")).lower() for u in work.get("update-to", [])),
            "source_name": "Crossref", "source_record_provider": "crossref",
            "field_sources": {"journal": "crossref", "publication_type": "crossref", "abstract": "crossref"},
        }
