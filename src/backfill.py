"""Command-line entry point for the 24-month historical corpus backfill."""

from __future__ import annotations

import argparse
import json

from src.history.backfill import BackfillService, SOURCE_TYPES
from src.utils import load_config, load_env, setup_logging


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Backfill event-dated energy research information history."
    )
    parser.add_argument("--months", type=int, default=24)
    parser.add_argument("--as-of", default="")
    parser.add_argument(
        "--sources",
        default=",".join(SOURCE_TYPES),
        help="Comma-separated source adapters.",
    )
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    load_env()
    config = load_config()
    setup_logging(config)
    sources = [value.strip() for value in args.sources.split(",") if value.strip()]
    result = BackfillService(config).run(
        months=args.months,
        as_of=args.as_of or None,
        sources=sources,
        force=args.force,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
