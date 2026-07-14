"""Backward-compatible paper summarizer built on DocumentSummarizer."""

from __future__ import annotations

from typing import Any, Dict, List

from .document_summarizer import DocumentSummarizer


class PaperSummarizer(DocumentSummarizer):
    """Preserve the historical paper API while sharing document logic."""

    def summarize_paper(self, paper: Dict[str, Any]) -> Dict[str, Any]:
        prepared = dict(paper)
        prepared.setdefault("source_type", "paper")
        prepared.setdefault("source_name", "arXiv")
        return self.summarize_document(prepared)

    def summarize_papers(
        self,
        papers: List[Dict[str, Any]],
        show_progress: bool = True,
    ) -> List[Dict[str, Any]]:
        prepared = []
        for paper in papers:
            record = dict(paper)
            record.setdefault("source_type", "paper")
            record.setdefault("source_name", "arXiv")
            prepared.append(record)
        return self.summarize_documents(prepared, show_progress=show_progress)

    def generate_daily_report(self, papers: List[Dict[str, Any]]) -> str:
        return self.generate_report(papers)
