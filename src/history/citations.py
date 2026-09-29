"""Checkpointed two-level reference traversal and one-level citing discovery."""
from datetime import date
from src.academic_library import PaperLibrary
from src.sources.academic import PaperQuery, atomic_json, read_json, record_key, unique_records
from src.sources.openalex_search_adapter import OpenAlexSearchAdapter
from src.sources.semantic_scholar_adapter import SemanticScholarAdapter


def trace_citations(config: dict, *, max_requests: int | None = None) -> dict:
    library = PaperLibrary(config)
    settings = config.get('paper_discovery', {}).get('citations', {})
    budget = int(max_requests if max_requests is not None else settings.get('max_requests_per_run', 100))
    semantic = SemanticScholarAdapter(config)
    semantic_ready = semantic.readiness() == 'ready'
    semantic.close()
    semantic_budget = budget // 2 if semantic_ready else 0
    budget -= semantic_budget
    depth_limit = int(settings.get('reference_depth', 2))
    path = library.root / 'citation_progress.json'
    state = read_json(path, {'queue': [], 'done': [], 'records': [], 'errors': {}})
    queue, done = state['queue'], set(state['done'])
    keys = {job['key'] for job in queue} | done

    def enqueue(identifier, depth, root, relation='reference'):
        key = f'{relation}:{identifier}:{depth}'
        if identifier and key not in keys:
            queue.append(dict(key=key, identifier=identifier, depth=depth, root=root, relation=relation))
            keys.add(key)

    for seed in library.load():
        root = record_key(seed)
        identifier = seed.get('openalex_id') or ('doi:' + seed['doi'] if seed.get('doi') else '')
        enqueue(identifier, 0, root)
        if identifier and int(settings.get('citing_depth', 1)):
            enqueue(identifier, 1, root, 'cited_by')
    adapter = OpenAlexSearchAdapter(config)
    adapter.settings['max_pages_per_run'] = 1
    calls, attempted = 0, set()
    try:
        while calls < budget:
            pending = [j for j in queue if j['key'] not in attempted]
            job = min(pending, key=lambda j: (j['relation'] != 'reference' or j['depth'] == 0, -j['depth']), default=None)
            if job is None:
                break
            attempted.add(job['key'])
            calls += 1
            try:
                if job['relation'] == 'reference':
                    identifier = job['identifier'].replace('https://openalex.org/', '')
                    record = adapter.lookup(identifier)
                    record['citation_discovery'] = {'root': job['root'], 'depth': job['depth'], 'relation': 'reference'}
                    state['records'].append(record)
                    if job['depth'] < depth_limit:
                        for ref in record.get('references', []):
                            enqueue(ref, job['depth'] + 1, job['root'])
                    complete = True
                else:
                    identifier = job['identifier'].replace('https://openalex.org/', '')
                    if identifier.startswith('doi:'):
                        record = adapter.lookup(identifier)
                        job['identifier'] = record['id']
                        atomic_json(path, state)
                        continue
                    result = adapter.fetch_range('1800-01-01', date.today().isoformat(), queries=[
                        PaperQuery(job['key'], relation='cited_by', seed=identifier)])
                    for record in result.records:
                        record['citation_discovery'] = {'root': job['root'], 'depth': 1, 'relation': 'cited_by'}
                    state['records'].extend(result.records)
                    complete = result.status == 'complete'
                    if result.errors:
                        state['errors'][job['key']] = result.errors
                if complete:
                    queue.remove(job)
                    done.add(job['key'])
                    state['errors'].pop(job['key'], None)
            except Exception as exc:
                # Avoid persisting URLs containing credentials from provider exceptions.
                state['errors'][job['key']] = type(exc).__name__
            state['done'] = sorted(done)
            state['records'] = unique_records(state['records'])
            atomic_json(path, state)
        report = library.ingest(state['records'], coverage={'citations:openalex_search': {
            'status': 'partial' if queue else 'complete', 'pending': len(queue),
            'completed': len(done), 'errors': state['errors'], 'requests_this_run': calls}})
        if semantic_ready:
            return _trace_semantic(config, semantic_budget)
        return report
    finally:
        adapter.close()


def _trace_semantic(config: dict, budget: int) -> dict:
    library = PaperLibrary(config)
    settings = config.get('paper_discovery', {}).get('citations', {})
    depth_limit = int(settings.get('reference_depth', 2))
    path = library.root / 'semantic_citation_progress.json'
    state = read_json(path, {'queue': [], 'done': [], 'records': []})
    keys = {j['key'] for j in state['queue']} | set(state['done'])

    def enqueue(identifier, depth, root, relation):
        key = f'{relation}:{identifier}:{depth}'
        if identifier and key not in keys:
            state['queue'].append(dict(key=key, identifier=identifier, depth=depth, root=root, relation=relation))
            keys.add(key)

    for paper in library.load():
        identifier = paper.get('semantic_scholar_id') or ('DOI:' + paper['doi'] if paper.get('doi') else '')
        if depth_limit:
            enqueue(identifier, 1, record_key(paper), 'references')
        if int(settings.get('citing_depth', 1)):
            enqueue(identifier, 1, record_key(paper), 'cited_by')
    adapter = SemanticScholarAdapter(config)
    adapter.settings['max_pages_per_run'] = 1
    errors, calls = [], 0
    try:
        for job in list(state['queue'])[:budget]:
            result = adapter.fetch_range('1800-01-01', date.today().isoformat(), queries=[
                PaperQuery(job['key'], relation=job['relation'], seed=job['identifier'])])
            calls += result.metadata.get('requests', 0)
            for record in result.records:
                record['citation_discovery'] = {k: job[k] for k in ('root', 'depth', 'relation')}
                if job['relation'] == 'references' and job['depth'] < depth_limit:
                    enqueue(record.get('semantic_scholar_id'), job['depth'] + 1, job['root'], 'references')
            state['records'] = unique_records(state['records'] + result.records)
            errors.extend(result.errors)
            if result.status == 'complete':
                state['queue'].remove(job)
                state['done'].append(job['key'])
            atomic_json(path, state)
        return library.ingest(state['records'], coverage={'citations:semantic_scholar': {
            'status': 'partial' if state['queue'] else 'complete', 'pending': len(state['queue']),
            'completed': len(state['done']), 'errors': errors, 'requests_this_run': calls}})
    finally:
        adapter.close()
