"""Resume the bounded editorial queue before the existing summary/export stages."""
from src.hotspots.editorial import EditorialEngine
from src.hotspots.ranking import record_source_health


def run(context):
    if not context.config.get('hotspots', {}).get('enabled', False):
        return context
    engine = EditorialEngine(context.config)
    record_source_health(engine.store, context.config, engine.now)
    from src.hotspots.topics import TopicEngine
    TopicEngine(context.config, engine.client, now=engine.now).process(context.normalized_records)
    context.normalized_records = engine.process(context.normalized_records)
    context.editorial_processed = True
    context.artifacts['hotspot_state'] = str(engine.store.path)
    context.logger.info('精选任务完成：本轮模型调用 %s 次', engine.client.calls)
    return context
