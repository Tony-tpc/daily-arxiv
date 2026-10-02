"""Shared public HTML/JSON list parsing for incremental and archive collection."""
from __future__ import annotations

import re
from typing import Any
from urllib.parse import urljoin, urlsplit

from bs4 import BeautifulSoup


def listing_item(item: Any, page_url: str, settings: dict) -> dict | None:
    """Extract a list item's original title, link and date without fetching detail."""
    link = item.select_one(str(settings.get('link_selector', 'a[href]')))
    if link is None and getattr(item, 'name', None) == 'a':
        link = item
    if link is None or not link.get('href'):
        return None
    url = urljoin(page_url, str(link['href']))
    if urlsplit(url).scheme not in {'http', 'https'}:
        return None
    title = ' '.join(str(link.get('title') or link.get_text(' ', strip=True)).split())
    node = item.select_one(settings['date_selector']) if settings.get('date_selector') else item
    text = node.get_text(' ', strip=True) if node is not None else ''
    match = re.search(r'(20\d{2})[年/.-](\d{1,2})[月/.-](\d{1,2})', text)
    published = '-'.join((match[1], match[2].zfill(2), match[3].zfill(2))) if match else ''
    return {'title': title, 'link': url, 'published': published} if title else None


def _field(value: Any, path: str) -> Any:
    for key in path.split('.') if path else []:
        if not isinstance(value, dict) or key not in value:
            raise ValueError(f'Missing JSON listing field: {path}')
        value = value[key]
    return value


def parse_listing(response: Any, settings: dict) -> list[dict]:
    """Read configured HTML or JSON fields; malformed payloads are not healthy empties."""
    if settings.get('format') == 'json':
        rows = _field(response.json(), str(settings.get('items_path', '')))
        if not isinstance(rows, list):
            raise ValueError('JSON items_path must identify an array')
        fields = settings.get('fields', {'title': 'title', 'link': 'url', 'published': 'published_at'})
        records = []
        for row in rows:
            record = {key: _field(row, path) for key, path in fields.items()}
            if not isinstance(record.get('title'), str) or not isinstance(record.get('link'), str):
                raise ValueError('JSON listing requires string title and link')
            record['link'] = urljoin(settings['url'], record['link'])
            if urlsplit(record['link']).scheme not in {'http', 'https'}:
                raise ValueError('JSON listing requires HTTP(S) links')
            records.append(record)
        return records
    soup = BeautifulSoup(response.content, 'html.parser')
    items = soup.select(settings.get('item_selector', 'li'))
    if not items:
        raise ValueError('HTML listing selector matched no items')
    return [record for item in items if (record := listing_item(item, settings['url'], settings))]
