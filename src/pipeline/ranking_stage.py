"""Ranking stage: sort enriched records by citation impact."""

from __future__ import annotations

from .context import PipelineContext


IMPACT_BRACKETS = [
    (100, "hot"),       # >= 100 citations → hot paper
    (25, "high"),       # >= 25  → high impact
    (5, "notable"),    # >= 5   → notable
]


def run(context: PipelineContext) -> PipelineContext:
    """Re-rank normalized (enriched) records by citation impact."""
    if context.stop_requested:
        return context

    arxiv_config = context.config.get("sources", {}).get("arxiv", {}) if isinstance(context.config, dict) else {}
    ranking = arxiv_config.get("ranking", {}) if isinstance(arxiv_config, dict) else {}
    if isinstance(ranking, dict) and not ranking.get("enabled", True):
        return context

    primary = ranking.get("primary", "citation_count") if isinstance(ranking, dict) else "citation_count"
    secondary = ranking.get("secondary", "openalex_referenced_works_count") if isinstance(ranking, dict) else "openalex_referenced_works_count"

    records = list(context.normalized_records or context.papers)

    def score(record: dict) -> tuple:
        p = int(record.get(primary, 0) or 0)
        s = int(record.get(secondary, 0) or 0)
        return (p, s)

    records.sort(key=score, reverse=True)

    for record in records:
        cites = int(record.get("citation_count", 0) or 0)
        for threshold, label in IMPACT_BRACKETS:
            if cites >= threshold:
                record["impact_bracket"] = label
                break
        else:
            record["impact_bracket"] = ""

    context.normalized_records = records
    context.logger.info(
        context.text(
            f"\U0001f4ca 按引用影响排序完成: {len(records)} 条记录",
            f"\U0001f4ca Records ranked by citation impact: {len(records)}",
        )
    )
    return context
