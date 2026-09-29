"""Import authorized bibliographic exports into the same audited paper library."""
import argparse
import json
from src.utils import load_config
from src.sources.institution_import import read_export
from src.academic_library import PaperLibrary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('files', nargs='+')
    parser.add_argument('--database', required=True)
    parser.add_argument('--no-enrich', action='store_true')
    args = parser.parse_args()
    records = [r for path in args.files for r in read_export(path, args.database)]
    report = PaperLibrary(load_config()).ingest(records, enrich=not args.no_enrich)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
