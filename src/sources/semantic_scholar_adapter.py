"""Semantic Scholar bulk discovery and paginated citation neighborhoods."""
import os
from .academic import PagedPaperAdapter, PaperPage, PaperQuery, clean_doi


class SemanticScholarAdapter(PagedPaperAdapter):
    source_name = 'semantic_scholar'
    base_url = 'https://api.semanticscholar.org/graph/v1'
    fields = 'title,abstract,authors,year,publicationDate,publicationTypes,journal,externalIds,citationCount,openAccessPdf,url'

    @property
    def api_key(self):
        return self.settings.get('api_key') or os.getenv('SEMANTIC_SCHOLAR_API_KEY', '')

    def readiness(self):
        return 'ready' if self.api_key else 'missing_api_key:SEMANTIC_SCHOLAR_API_KEY'

    def queries(self):
        return [q for q in super().queries() if not q.issn]

    def fetch_page(self, query: PaperQuery, date_from: str, date_to: str, cursor: str) -> PaperPage:
        headers = {'x-api-key': self.api_key}
        if query.relation:
            relation = 'citations' if query.relation == 'cited_by' else 'references'
            payload = self.get_json(f'{self.base_url}/paper/{query.seed}/{relation}',
                                   {'fields': self.fields, 'offset': 0 if cursor == '*' else cursor,
                                    'limit': self.page_size}, headers)
            field = 'citingPaper' if relation == 'citations' else 'citedPaper'
            works = [r[field] for r in payload['data'] if r.get(field)]
            next_cursor = str(payload['next']) if payload.get('next') is not None else None
        else:
            params = {'query': query.term.replace('-', ' '), 'fields': self.fields,
                      'publicationDateOrYear': f'{date_from}:{date_to}'}
            if cursor != '*':
                params['token'] = cursor
            payload = self.get_json(f'{self.base_url}/paper/search/bulk', params, headers)
            works, next_cursor = payload['data'], payload.get('token')
        return PaperPage([self.work_to_record(w) for w in works], next_cursor, payload.get('total'))

    @staticmethod
    def work_to_record(work: dict) -> dict:
        ids = work.get('externalIds') or {}
        doi = clean_doi(ids.get('DOI'))
        journal = work.get('journal') or {}
        types = work.get('publicationTypes') or []
        return {'id': f"s2:{work['paperId']}", 'semantic_scholar_id': work['paperId'], 'doi': doi,
                'title': work.get('title', ''), 'abstract': work.get('abstract') or '',
                'authors': [a.get('name', '') for a in work.get('authors') or []],
                'published': work.get('publicationDate') or str(work.get('year') or ''),
                'publication_type': 'review' if 'Review' in types else 'journal-article' if 'JournalArticle' in types else '',
                'publication_types': types, 'journal_name': journal.get('name') or '',
                'entry_url': f'https://doi.org/{doi}' if doi else work.get('url', ''),
                'pdf_url': (work.get('openAccessPdf') or {}).get('url') or '',
                'citation_count': work.get('citationCount', 0), 'source_name': 'Semantic Scholar',
                'source_record_provider': 'semantic_scholar',
                'field_sources': {'abstract': 'semantic_scholar', 'journal': 'semantic_scholar', 'publication_type': 'semantic_scholar'}}
