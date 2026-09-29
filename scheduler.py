"""Source-specific APScheduler orchestration with durable job state."""

from __future__ import annotations

import copy
import json
import logging
import os
import sys
import threading
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List

import pytz
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger


project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.notifier import EmailNotifier
from src.pipeline.context import create_pipeline_context
from src.pipeline.runner import run_pipeline
from src.utils import load_config, load_env, pick_text, setup_logging


PIPELINE_SOURCES = ("arxiv", "openalex_search", "crossref", "openaire", "semantic_scholar", "rss", "policy", "industry_report")
DEFAULT_JOBS: Dict[str, Dict[str, Any]] = {
    "academic_weekly": {
        "enabled": True,
        "sources": ["arxiv", "openalex_search", "crossref", "openaire", "semantic_scholar"],
        "day_of_week": "sun",
        "trigger": "cron",
        "hour": 9,
        "minute": 0,
    },
    "news_8h": {
        "enabled": True,
        "sources": ["rss"],
        "trigger": "interval",
        "hours": 8,
    },
    "policy_daily": {
        "enabled": True,
        "sources": ["policy"],
        "trigger": "cron",
        "hour": 10,
        "minute": 0,
    },
    "industry_weekly": {
        "enabled": True,
        "sources": ["industry_report"],
        "trigger": "cron",
        "day_of_week": "mon",
        "hour": 11,
        "minute": 0,
    },
}

_PIPELINE_LOCK = threading.Lock()
_STATE_LOCK = threading.Lock()


def build_job_specs(config: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Return validated, enabled source job definitions in configuration order."""
    scheduler_config = config.get("scheduler", {})
    configured = scheduler_config.get("jobs")
    jobs = configured if isinstance(configured, dict) and configured else DEFAULT_JOBS
    specs: List[Dict[str, Any]] = []
    for job_id, raw in jobs.items():
        if not isinstance(raw, dict) or not raw.get("enabled", True):
            continue
        sources = [str(item) for item in raw.get("sources", []) if str(item) in PIPELINE_SOURCES]
        if not sources:
            raise ValueError(f"Scheduler job {job_id!r} has no supported sources")
        trigger = str(raw.get("trigger", "cron")).lower()
        if trigger not in {"cron", "interval"}:
            raise ValueError(f"Scheduler job {job_id!r} has unsupported trigger {trigger!r}")
        spec = {"id": str(job_id), **copy.deepcopy(raw), "sources": sources, "trigger": trigger}
        if trigger == "interval":
            hours = float(spec.get("hours", 0))
            if hours <= 0:
                raise ValueError(f"Scheduler job {job_id!r} requires hours > 0")
            if sources == ["rss"] and not 6 <= hours <= 12:
                raise ValueError("The domestic news interval must be between 6 and 12 hours")
        specs.append(spec)
    return specs


def build_source_config(config: Dict[str, Any], source_names: Iterable[str]) -> Dict[str, Any]:
    """Create an isolated incremental config without mutating the shared config."""
    isolated = copy.deepcopy(config)
    selected = {str(name) for name in source_names}
    sources = isolated.setdefault("sources", {})
    for name in PIPELINE_SOURCES:
        source_config = sources.setdefault(name, {})
        if isinstance(source_config, dict):
            source_config["enabled"] = name in selected
    runtime = isolated.setdefault("runtime", {})
    runtime["merge_with_latest"] = True
    runtime["scheduler_sources"] = sorted(selected)
    isolated.setdefault("summarization", {}).setdefault("reuse_existing", True)
    return isolated


def run_source_job(
    job_id: str,
    source_names: Iterable[str],
    *,
    config: Dict[str, Any] | None = None,
    logger: logging.Logger | None = None,
    notifier: Any = None,
    pipeline_runner: Callable[[Any], Any] = run_pipeline,
    sleep_func: Callable[[float], None] = time.sleep,
) -> Dict[str, Any]:
    """Run one isolated source group with bounded retry and durable status."""
    base_config = copy.deepcopy(config or load_config())
    logger = logger or setup_logging(base_config)
    text = lambda zh, en: pick_text(base_config, zh, en)
    scheduler_config = base_config.get("scheduler", {})
    retry = scheduler_config.get("retry", {})
    max_attempts = max(1, int(retry.get("max_attempts", 3)))
    base_delay = max(0.0, float(retry.get("base_delay_seconds", 30)))
    max_delay = max(base_delay, float(retry.get("max_delay_seconds", 300)))
    sources = [str(name) for name in source_names]
    job_config = build_source_config(base_config, sources)
    started_at = _utc_now()
    started_clock = time.monotonic()

    for attempt in range(1, max_attempts + 1):
        attempt_started = _utc_now()
        _update_job_status(base_config, job_id, {
            "status": "running",
            "sources": sources,
            "last_started_at": started_at,
            "attempt_started_at": attempt_started,
            "attempts": attempt,
            "error": "",
        })
        _append_job_event(base_config, {
            "event": "started",
            "job_id": job_id,
            "sources": sources,
            "attempt": attempt,
            "timestamp": attempt_started,
        })
        try:
            with _PIPELINE_LOCK:
                if job_config.get('paper_discovery', {}).get('enabled', False) and 'openalex_search' in sources:
                    from src.history.paper_backfill import PaperBackfillService
                    from src.history.citations import trace_citations
                    from src.sources.academic import INDEX_SOURCES
                    today = datetime.now().date()
                    start = today.replace(year=today.year - int(job_config['paper_discovery'].get('history_years', 10)), day=1)
                    PaperBackfillService(job_config).run(start.isoformat(), today.isoformat(),
                        sources=[s for s in sources if s in INDEX_SOURCES],
                        max_requests=int(job_config['paper_discovery'].get('history_requests_per_run', 120)))
                    trace_citations(job_config)
                context = create_pipeline_context(job_config, logger, text)
                context = pipeline_runner(context) or context

            record_count = sum(
                len(records) for records in getattr(context, "source_records", {}).values()
            )
            source_errors = dict(getattr(context, "source_errors", {}) or {})
            if source_errors and record_count == 0:
                details = "; ".join(f"{name}: {error}" for name, error in source_errors.items())
                raise RuntimeError(f"All scheduled sources failed: {details}")
            if record_count and not getattr(context, "normalized_records", []) and getattr(
                context, "stop_requested", False
            ):
                raise RuntimeError("Fetched records could not be normalized into documents")

            status = "partial" if source_errors else ("empty" if record_count == 0 else "succeeded")
            finished_at = _utc_now()
            duration = round(time.monotonic() - started_clock, 3)
            result = {
                "success": True,
                "job_id": job_id,
                "status": status,
                "sources": sources,
                "record_count": record_count,
                "document_count": len(getattr(context, "normalized_records", []) or []),
                "source_errors": source_errors,
                "attempts": attempt,
                "started_at": started_at,
                "finished_at": finished_at,
                "duration_seconds": duration,
                "artifacts": dict(getattr(context, "artifacts", {}) or {}),
            }
            _update_job_status(base_config, job_id, {
                **result,
                "last_finished_at": finished_at,
                "last_success_at": finished_at,
                "error": "",
            })
            _append_job_event(base_config, {"event": status, "timestamp": finished_at, **result})
            logger.info(text(
                f"调度任务 {job_id} 完成：{status}，新增 {record_count} 条，尝试 {attempt} 次",
                f"Scheduled job {job_id} finished: {status}, {record_count} new records, {attempt} attempt(s)",
            ))
            _notify(notifier, True, duration=duration, stats={"papers_count": record_count})
            return result
        except Exception as exc:
            error = str(exc)
            logger.error(text(
                f"调度任务 {job_id} 第 {attempt}/{max_attempts} 次失败: {error}",
                f"Scheduled job {job_id} failed on attempt {attempt}/{max_attempts}: {error}",
            ), exc_info=True)
            if attempt < max_attempts:
                delay = min(max_delay, base_delay * (2 ** (attempt - 1)))
                _append_job_event(base_config, {
                    "event": "retry_scheduled",
                    "job_id": job_id,
                    "sources": sources,
                    "attempt": attempt,
                    "delay_seconds": delay,
                    "error": error,
                    "timestamp": _utc_now(),
                })
                sleep_func(delay)
                continue

            finished_at = _utc_now()
            duration = round(time.monotonic() - started_clock, 3)
            result = {
                "success": False,
                "job_id": job_id,
                "status": "failed",
                "sources": sources,
                "record_count": 0,
                "document_count": 0,
                "source_errors": {},
                "attempts": attempt,
                "started_at": started_at,
                "finished_at": finished_at,
                "duration_seconds": duration,
                "artifacts": {},
                "error": error,
            }
            _update_job_status(base_config, job_id, {
                **result,
                "last_finished_at": finished_at,
            })
            _append_job_event(base_config, {"event": "failed", "timestamp": finished_at, **result})
            _notify(notifier, False, duration=duration, error_msg=f"{error}\n\n{traceback.format_exc()}")
            return result

    raise AssertionError("unreachable")


def register_source_jobs(
    scheduler: Any,
    config: Dict[str, Any],
    logger: logging.Logger,
    notifier: Any = None,
) -> List[Dict[str, Any]]:
    """Register configured jobs and return their normalized specs."""
    timezone_name = config.get("scheduler", {}).get("timezone", "Asia/Shanghai")
    tz = pytz.timezone(timezone_name)
    specs = build_job_specs(config)
    for spec in specs:
        if spec["trigger"] == "interval":
            trigger = IntervalTrigger(hours=float(spec["hours"]), timezone=tz)
        else:
            trigger = CronTrigger(
                day_of_week=spec.get("day_of_week"),
                hour=int(spec.get("hour", 0)),
                minute=int(spec.get("minute", 0)),
                timezone=tz,
            )
        scheduler.add_job(
            run_source_job,
            trigger=trigger,
            kwargs={
                "job_id": spec["id"],
                "source_names": spec["sources"],
                "config": config,
                "logger": logger,
                "notifier": notifier,
            },
            id=spec["id"],
            name=str(spec.get("name") or spec["id"]),
            max_instances=1,
            coalesce=True,
            misfire_grace_time=int(spec.get("misfire_grace_time", 3600)),
            replace_existing=True,
        )
    return specs


def scheduled_task(logger=None, notifier=None, language="zh") -> bool:
    """Backward-compatible entry point for one run of all enabled sources."""
    config = load_config()
    enabled = [
        name for name in PIPELINE_SOURCES
        if config.get("sources", {}).get(name, {}).get("enabled", False)
    ]
    result = run_source_job(
        "daily_arxiv_task",
        enabled or ["arxiv"],
        config=config,
        logger=logger,
        notifier=notifier,
    )
    return bool(result["success"])


def _status_path(config: Dict[str, Any]) -> Path:
    return Path(config.get("scheduler", {}).get("status_path", "data/state/scheduler_status.json"))


def _task_log_path(config: Dict[str, Any]) -> Path:
    return Path(config.get("scheduler", {}).get("task_log_path", "logs/scheduler_jobs.jsonl"))


def _update_job_status(config: Dict[str, Any], job_id: str, values: Dict[str, Any]) -> None:
    path = _status_path(config)
    with _STATE_LOCK:
        payload: Dict[str, Any] = {}
        if path.exists():
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                payload = {}
        jobs = payload.get("jobs") if isinstance(payload.get("jobs"), dict) else {}
        previous = jobs.get(job_id) if isinstance(jobs.get(job_id), dict) else {}
        jobs[job_id] = {**previous, **values}
        payload = {
            "schema_version": "1.0",
            "updated_at": _utc_now(),
            "jobs": jobs,
        }
        path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = path.with_name(f".{path.name}.{os.getpid()}.{threading.get_ident()}.tmp")
        temp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(temp_path, path)


def _append_job_event(config: Dict[str, Any], event: Dict[str, Any]) -> None:
    path = _task_log_path(config)
    with _STATE_LOCK:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, ensure_ascii=False, default=str) + "\n")
            handle.flush()
            os.fsync(handle.fileno())


def _notify(notifier: Any, success: bool, **kwargs: Any) -> None:
    if notifier is None:
        return
    try:
        notifier.send_notification(success=success, **kwargs)
    except Exception:
        logging.getLogger("daily_arxiv").warning("Scheduler notification failed", exc_info=True)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def main() -> None:
    """Start the blocking multi-source scheduler."""
    load_env()
    config = load_config()
    logger = setup_logging(config)
    text = lambda zh, en: pick_text(config, zh, en)
    scheduler_config = config.get("scheduler", {})
    if not scheduler_config.get("enabled", False):
        logger.warning(text(
            "调度器未启用；请设置 scheduler.enabled: true",
            "Scheduler disabled; set scheduler.enabled: true",
        ))
        return

    notifier = None
    notification = scheduler_config.get("notification", {})
    if notification.get("enabled", False):
        email_config = copy.deepcopy(notification.get("email", {}))
        email_config["_language"] = config.get("app", {}).get("language", "zh")
        notifier = EmailNotifier(email_config)

    tz = pytz.timezone(scheduler_config.get("timezone", "Asia/Shanghai"))
    scheduler = BlockingScheduler(timezone=tz)
    specs = register_source_jobs(scheduler, config, logger, notifier)
    logger.info(text(
        f"多源调度器已加载 {len(specs)} 个任务：{', '.join(item['id'] for item in specs)}",
        f"Loaded {len(specs)} source jobs: {', '.join(item['id'] for item in specs)}",
    ))

    if scheduler_config.get("run_on_start", False):
        for spec in specs:
            run_source_job(
                spec["id"],
                spec["sources"],
                config=config,
                logger=logger,
                notifier=notifier,
            )

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info(text("多源调度器已停止", "Source scheduler stopped"))


if __name__ == "__main__":
    main()
