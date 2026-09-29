"""Parse authorized bibliographic exports without automating institutional logins."""
from __future__ import annotations
import csv
import hashlib
import re
from pathlib import Path
from datetime import datetime, timezone
from .academic import clean_doi


def publication_type(value: str) -> str:
    """Preserve restrictive secondary labels such as Article; Proceedings Paper."""
    text = value.casefold()
    if re.search(r'\breview\b|\bsurvey\b', text):
        return 'review'
    if any(term in text for term in ('conference', 'proceedings', 'conf', 'cpaper')):
        return 'proceedings-article'
    if any(term in text for term in ('editorial', 'correction', 'retraction', 'erratum', 'preprint')):
        return next(term for term in ('editorial', 'correction', 'retraction', 'erratum', 'preprint') if term in text)
    return 'journal-article' if any(t.strip() in {'jour', 'article', 'journal article', 'journal-article', 'research article'}
        for t in text.split(';')) else text


def _tagged(text: str, ris: bool) -> list[dict]:
    records, current = [], {}
    previous = ''
    for line in text.splitlines():
        match = re.match(r'^([A-Z0-9]{2})  - ?(.*)$' if ris else r'^([A-Z0-9]{2}) (.*)$', line)
        if line.strip() == 'ER' or (match and match[1] == 'ER'):
            if current:
                records.append(current)
            current, previous = {}, ''
        elif match:
            previous = match[1]
            current.setdefault(previous, []).append(match[2].strip())
        elif line.startswith('   ') and previous:
            if not ris and previous in {'AU', 'AF', 'CR'}:
                current[previous].append(line.strip())
            else:
                current[previous][-1] += ' ' + line.strip()
    if current and ('TI' in current or 'T1' in current):
        records.append(current)
    return records


def read_export(path: str | Path, database: str) -> list[dict]:
    """Read RIS/BibTeX/CSV/WoS tagged text; preserve file hash and database provenance."""
    path = Path(path)
    raw = path.read_bytes()
    try:
        text = raw.decode('utf-8-sig')
    except UnicodeDecodeError:
        text = raw.decode('gb18030')
    batch = hashlib.sha256(raw).hexdigest()
    records = []
    if path.suffix.lower() in {'.bib', '.bibtex'}:
        import bibtexparser
        library = bibtexparser.parse_string(text)
        if library.failed_blocks:
            raise ValueError('BibTeX contains unparsed blocks; fix the export before importing')
        for entry in library.entries:
            fields = {k.lower(): v.value for k, v in entry.fields_dict.items()}
            records.append({'title': fields.get('title'), 'authors': re.split(r'\s+and\s+', fields.get('author', '')),
                'abstract': fields.get('abstract', ''), 'doi': fields.get('doi'),
                'journal_name': fields.get('journal'), 'journal_issn': fields.get('issn', '').split(','),
                'published': fields.get('date') or fields.get('year', ''),
                'publication_type': publication_type(entry.entry_type + ';' + fields.get('type', '')),
                'entry_url': fields.get('url', '')})
    elif path.suffix.lower() == '.csv':
        for row in csv.DictReader(text.splitlines()):
            row = {str(k).strip().casefold(): (v or '').strip() for k, v in row.items() if k}
            def get(*names):
                return next((row[n] for n in names if row.get(n)), '')
            kind = get('document type', 'publication type', 'type')
            records.append({'title': get('title', 'article title', 'document title'),
                'authors': re.split(r';\s*', get('authors', 'author full names')),
                'doi': get('doi'), 'abstract': get('abstract'),
                'journal_name': get('source title', 'publication title', 'journal', 'journal name'),
                'journal_issn': re.split(r'[;,]\s*', get('issn', 'eissn')),
                'published': get('publication date', 'date', 'year', 'publication year'),
                'publication_type': publication_type(kind),
                'entry_url': get('url', 'link', 'document identifier')})
    else:
        ris = path.suffix.lower() == '.ris' or bool(re.search(r'^TY  - ', text, re.M))
        for row in _tagged(text, ris):
            def value(*keys):
                return next((row[k][0] for k in keys if row.get(k)), '')
            kind = value('TY' if ris else 'DT').casefold()
            journal = value('JO', 'JF', 'T2') if ris else value('SO')
            refs = []
            for item in row.get('CR', []):
                match = re.search(r'\bDOI\s+(10\.\S+)', item, re.I)
                if match:
                    refs.append('doi:' + clean_doi(match[1]))
            records.append({'title': value('TI', 'T1'), 'abstract': value('AB', 'N2'),
                'authors': row.get('AU') or row.get('AF') or [], 'doi': value('DO' if ris else 'DI'),
                'journal_name': journal, 'journal_issn': row.get('SN', []) + row.get('EI', []),
                'published': value('PY', 'Y1'), 'entry_url': value('UR'), 'references': refs,
                'publication_type': publication_type(kind + ';' + value('M3')),
                'publication_types': [kind]})
    for index, record in enumerate(records):
        record['doi'] = clean_doi(record.get('doi'))
        record['id'] = f'import:{hashlib.sha256(database.encode()).hexdigest()[:8]}:{batch[:16]}:{index}'
        record['source_name'] = database
        record['source_record_provider'] = 'institution_import'
        record['import_batch'] = batch
        record['import_file'] = path.name
        record['collected_at'] = datetime.now(timezone.utc).isoformat()
        record['field_sources'] = {field: database for field in ('abstract', 'journal', 'publication_type')}
        if record['doi']:
            record['entry_url'] = 'https://doi.org/' + record['doi']
    if not records or any(not r.get('title') for r in records):
        raise ValueError('Export contains no records or a record without a title')
    return records
