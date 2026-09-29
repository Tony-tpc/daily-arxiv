"""Command-line entry point for the 24-month historical corpus backfill."""

from __future__ import annotations

import argparse
import json

from src.history.backfill import BackfillService, SOURCE_TYPES
from src.history.paper_backfill import PaperBackfillService
from src.sources.academic import INDEX_SOURCES
from datetime import date
from src.utils import load_config, load_env, setup_logging


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Backfill event-dated energy research information history."
    )
    parser.add_argument("--months", type=int, default=120)
    parser.add_argument("--as-of", default="")
    parser.add_argument(
        "--sources",
        default=",".join(INDEX_SOURCES),
        help="Comma-separated source adapters.",
    )
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--date-from", default="")
    parser.add_argument("--date-to", default="")
    parser.add_argument("--max-requests", type=int, default=120)
    parser.add_argument("--no-enrich", action="store_true")
    parser.add_argument("--trace-citations", action="store_true")
    args = parser.parse_args()

    if args.months < 1 or args.max_requests < 0:
        parser.error("months must be positive and max-requests must be nonnegative")
    load_env()
    config = load_config()
    setup_logging(config)
    sources = [value.strip() for value in args.sources.split(",") if value.strip()]
    unknown = set(sources) - ((set(SOURCE_TYPES) | set(INDEX_SOURCES)) - {'paper_library'})
    if unknown:
        parser.error('Unsupported sources: ' + ', '.join(sorted(unknown)))
    end = date.fromisoformat(args.date_to or args.as_of) if (args.date_to or args.as_of) else date.today()
    index = end.year * 12 + end.month - args.months
    start = date.fromisoformat(args.date_from) if args.date_from else date(index // 12, index % 12 + 1, 1)
    result = {}
    papers = [s for s in sources if s in INDEX_SOURCES]
    if papers:
        result['papers'] = PaperBackfillService(config).run(start.isoformat(), end.isoformat(),
            sources=papers, max_requests=args.max_requests, force=args.force, enrich=not args.no_enrich)
    others = [s for s in sources if s not in INDEX_SOURCES]
    if others:
        result['other_sources'] = BackfillService(config).run(months=args.months, as_of=end,
            sources=others, force=args.force, date_from=start.isoformat())
    if args.trace_citations:
        from src.history.citations import trace_citations
        result['citations'] = trace_citations(config, max_requests=args.max_requests)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
