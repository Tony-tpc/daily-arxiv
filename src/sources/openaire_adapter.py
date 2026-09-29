"""OpenAIRE Graph v3 discovery; repository instances remain version evidence."""
from .academic import PagedPaperAdapter, PaperPage, PaperQuery, clean_doi
from .paper_normalizer import clean_paper_title


class OpenAIREAdapter(PagedPaperAdapter):
    source_name = "openaire"

    def queries(self):
        return [q for q in super().queries() if not q.issn]

    def fetch_page(self, query: PaperQuery, date_from: str, date_to: str, cursor: str) -> PaperPage:
        payload = self.get_json('https://api.openaire.eu/graph/v3/research-products', {
            'search': query.term, 'type': 'publication', 'fromPublicationDate': date_from,
            'toPublicationDate': date_to, 'pageSize': self.page_size, 'cursor': cursor})
        works = payload['results']
        return PaperPage([self.work_to_record(w) for w in works],
                         payload.get('header', {}).get('nextCursor') if works else None,
                         payload.get('header', {}).get('numFound'))

    @staticmethod
    def work_to_record(work: dict) -> dict:
        pids = work.get('pids') or []
        doi = next((clean_doi(p.get('value')) for p in pids if str(p.get('scheme', '')).lower() == 'doi'), '')
        container = work.get('container') or {}
        instances = work.get('instances') or []
        types = {str(i.get('type') or '').lower() for i in instances}
        pub_type = 'review' if 'review' in types else 'journal-article' if 'article' in types else ''
        urls = list(dict.fromkeys(u for i in instances for u in i.get('urls', [])))
        topics = [s.get('subject', {}).get('value', '') for s in work.get('subjects') or []]
        issns = [container.get(k) for k in ('issnPrinted', 'issnOnline', 'issn') if container.get(k)]
        return {'id': f"openaire:{work['id']}", 'doi': doi, 'title': work.get('mainTitle', ''),
                'abstract': clean_paper_title('\n'.join(work.get('descriptions') or [])),
                'authors': [a.get('fullName', '') for a in work.get('authors') or []],
                'published': work.get('publicationDate') or '',
                'entry_url': f'https://doi.org/{doi}' if doi else (urls[0] if urls else ''),
                'pdf_url': '', 'journal_name': container.get('name') or '', 'journal_issn': issns,
                'publication_type': pub_type, 'publication_types': sorted(types),
                'categories': topics, 'version_links': urls,
                'source_name': 'OpenAIRE', 'source_record_provider': 'openaire',
                'field_sources': {'abstract': 'openaire', 'journal': 'openaire', 'publication_type': 'openaire'}}
