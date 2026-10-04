"""Run bounded source catch-up and analysis: python -m src.hotspots.refresh_industry."""
from types import SimpleNamespace

from src.utils import load_config, load_env, setup_logging
from src.storage.base import build_storage
from src.sources.rss_adapter import RSSSourceAdapter
from src.sources.recent_news import refresh_recent
from src.sources.observations import attach_observations
from src.linking.deduplicator import Deduplicator
from src.hotspots.editorial import EditorialEngine
from src.hotspots.store import HotspotStore
from src.hotspots.topics import TopicEngine
from src.hotspots.ranking import record_source_health
from src.pipeline import hotspot_stage


def run(config: dict) -> dict:
    logger = setup_logging(config)
    storage = build_storage(config)
    documents = storage.load_latest().get('documents', [])
    adapter = RSSSourceAdapter(config)
    try:
        records = adapter.fetch()
        records += refresh_recent(adapter, documents)
        documents = Deduplicator(config).process(
            [attach_observations(d, config) for d in documents + adapter.normalize(records)])['documents']
        storage.save_snapshot(documents, metadata={'reason': 'recent industry catch-up'})
    finally:
        adapter.client.close()
    store = HotspotStore(config)
    editorial = EditorialEngine(config)
    client = editorial.client
    engine = TopicEngine(config, client)
    record_source_health(store, config, engine.now)
    engine.process(documents)
    editorial.process(documents)
    hotspot_stage.run(SimpleNamespace(config=config))
    result = store.latest()
    logger.info('行业补采重建：新建或补全 %s 份，模型调用 %s；榜单 %s；进度 %s',
                len(records), client.calls, {k: len(v) for k, v in result['boards'].items()}, result['processing'])
    return result


if __name__ == '__main__':
    load_env()
    run(load_config())
