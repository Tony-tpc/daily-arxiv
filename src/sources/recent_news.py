"""Bounded, resumable archive catch-up and missing-body recovery for news jobs."""
from datetime import date as calendar_date, timedelta
from urllib.parse import urlsplit

from bs4 import BeautifulSoup

from src.hotspots.domain import LOCAL_TZ, timestamp
from src.history.backfill import _HTMLArchiveCollector, _archive_page_urls
from src.utils import save_json


def refresh_recent(adapter, documents: list[dict]) -> list[dict]:
    settings = adapter.source_config.get('recent_backfill', {})
    if not settings.get('enabled', False):
        return []
    now = timestamp(adapter._now())
    cutoff = now - timedelta(days=int(adapter.source_config.get('max_age_days', 30)))
    pending = adapter.state.setdefault('pending_details', {})
    archive_state = adapter.state.setdefault('recent_archives', {})
    feeds = {f['url']: f for f in [*adapter.source_config.get('backfill_feeds', []), *adapter._configured_feeds()]}
    # Existing short descriptions survive feed rotation and are retried independently.
    for doc in documents:
        date = timestamp(doc.get('published_at'))
        provenance = doc.get('provenance', {})
        feed = feeds.get(provenance.get('fetch_url'))
        if (doc.get('source_type') != 'news' or not date or not cutoff < date <= now
                or not feed or not feed.get('fetch_detail')
                or (provenance.get('metadata', {}).get('detail_fetched')
                    and (not feed.get('detail_source_selector')
                         or provenance.get('metadata', {}).get('original_source_credit')
                         or provenance.get('metadata', {}).get('attribution_verified') is False))):
            continue
        record = adapter._raw_entry({'title': doc['title'], 'link': doc['url'],
                                     'published': doc['published_at'], 'summary': doc.get('raw_text', '')},
                                    feed, feed['url'], '', adapter._now())
        pending.setdefault(record['dedup_key'], record)
    collector = _HTMLArchiveCollector(adapter.config, 'rss', adapter)
    collector.client.close()  # Reuse the adapter's transport; no second network session.
    for feed in adapter.source_config.get('backfill_feeds', []):
        if not feed.get('enabled', True):
            continue
        feeds.setdefault(feed['url'], feed)
        state = archive_state.setdefault(feed['url'], {})
        today = now.astimezone(LOCAL_TZ).date().isoformat()
        if not state.get('cycle_date') or (state.get('complete') and state.get('cycle_date') != today):
            state.update(cycle_date=today, cursor=0, complete=False, error='')
        if state.get('complete'):
            continue
        if feed.get('date_url_template'):
            anchor = calendar_date.fromisoformat(state['cycle_date'])
            urls = [(anchor - timedelta(days=i)).strftime(feed['date_url_template'])
                    for i in range(int(adapter.source_config.get('max_age_days', 30)) + 1)]
        else:
            urls = list(_archive_page_urls(feed))
        cursor = int(state.get('cursor', 0))
        for page_index in range(cursor, min(len(urls), cursor + int(settings.get('pages_per_feed', 2)))):
            try:
                response = adapter.client.get(urls[page_index]); response.raise_for_status()
                soup = BeautifulSoup(response.content, 'html.parser')
                items = soup.select(feed.get('item_selector', 'li'))
                if not items:
                    raise ValueError('Archive selector matched no items')
                dates = []
                for item in items:
                    record = collector._item_to_record(item, urls[page_index], {**feed, 'backfill_fetch_detail': False})
                    if not record:
                        continue
                    paths = feed.get('article_path_prefixes', [])
                    if paths and not any(urlsplit(record['url']).path.startswith(prefix) for prefix in paths):
                        continue
                    published = timestamp(record['published_at'])
                    if published:
                        dates.append(published)
                    if (published and cutoff < published <= now
                            and adapter._matches_content_filters(record, feed)
                            and record['dedup_key'] not in adapter.state['seen']):
                        pending.setdefault(record['dedup_key'], record)
                if not dates:
                    raise ValueError('Archive contains no usable publication dates')
                state.update(cursor=page_index + 1, error='', last_success_at=adapter._now())
                if max(dates) <= cutoff or page_index + 1 == len(urls):
                    state['complete'] = True
                    break
            except Exception as exc:
                state['error'] = str(exc)
                break  # Keep the cursor for the next run.
    # Persist discovered URLs and cursors before article requests can be interrupted.
    save_json(adapter.state, adapter.state_path)
    records = []
    attempts = 0
    for key, record in list(pending.items()):
        published = timestamp(record.get('published_at'))
        if not published or not cutoff < published <= now:
            del pending[key]
            continue
        if attempts >= int(settings.get('details_per_run', 20)):
            break
        feed = feeds.get(record.get('feed_url'), {})
        if not feed.get('detail_content_selector'):
            continue
        attempts += 1
        try:
            content = adapter._fetch_detail_text(record['url'], feed)
            if len(content) < 100:
                raise ValueError('Article body missing or too short')
            record.update(content=content, summary=content[:1000], detail_fetched=True)
            record.update(adapter.detail_metadata.get(record['url'], {}))
            # A pure statistical dispatch credits its explicit original institution.
            record['origin_owner_id'] = adapter._original_owner(record)
            records.append(record)
        except Exception as exc:
            record['detail_error'] = str(exc)
            # Rotate failures behind other pending documents to avoid starvation.
            pending[key] = pending.pop(key)
    if records:
        adapter.save_raw_snapshot(records)
        for record in records:
            adapter.state['seen'][record['dedup_key']] = adapter._now()
            pending.pop(record['dedup_key'], None)
    save_json(adapter.state, adapter.state_path)
    return records
