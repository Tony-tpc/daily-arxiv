"""Validate and import a locally authorized CAS evidence registry (JSON)."""
import argparse
import json
from pathlib import Path
from src.utils import load_config
from src.sources.academic import atomic_json
from src.sources.paper_quality import valid_venue_evidence


def import_evidence(source: str, destination: str) -> int:
    payload = json.loads(Path(source).read_text(encoding='utf-8'))
    venues = payload.get('venues', [])
    if not venues or any(not valid_venue_evidence(v) or not v.get('name') for v in venues):
        raise ValueError('Every venue requires CAS major-category evidence, edition, partition, identity and provenance')
    atomic_json(destination, payload)
    return len(venues)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('file')
    args = parser.parse_args()
    config = load_config()
    print(import_evidence(args.file, config['paper_quality']['venue_evidence_path']))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
