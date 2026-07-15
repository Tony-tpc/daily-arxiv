"""Evidence-first forecasting for energy embodied-intelligence research."""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date, datetime
from math import sqrt
from typing import Any, Dict, Iterable, List

import numpy as np
from sklearn.linear_model import TheilSenRegressor


TOPIC_TAXONOMY: Dict[str, Dict[str, Any]] = {
    "energy_perception": {
        "label": "能源设备感知",
        "keywords": [
            "能源设备感知", "状态感知", "状态估计", "故障诊断", "设备感知",
            "condition monitoring", "state estimation", "fault diagnosis",
            "energy equipment perception",
        ],
        "watch": ["实时状态估计误差", "跨设备数据可用性", "异常工况识别率"],
        "action": "构建带物理约束的多模态设备状态数据集，并验证跨工况泛化。",
    },
    "autonomous_control": {
        "label": "自治决策与安全控制",
        "keywords": [
            "自治决策", "自主决策", "安全控制", "自主控制", "能源智能体",
            "energy agent", "autonomous energy", "safe control", "decision control",
        ],
        "watch": ["闭环安全约束违例率", "极端工况恢复时间", "人工接管频率"],
        "action": "在闭环仿真中比较自治策略与传统控制基线，并报告安全边界。",
    },
    "grid_coordination": {
        "label": "源网荷储与虚拟电厂协同",
        "keywords": [
            "源网荷储", "虚拟电厂", "需求响应", "微电网", "分布式能源",
            "virtual power plant", "demand response", "microgrid",
            "source grid load storage", "distributed energy resource",
        ],
        "watch": ["可调资源聚合规模", "需求响应持续时长", "跨主体协同收益"],
        "action": "建立源网荷储多主体协同基准，验证规模扩展与通信延迟影响。",
    },
    "market_game": {
        "label": "电力市场与博弈机制",
        "keywords": [
            "电力市场", "电力交易", "现货市场", "博弈", "机制设计", "电价",
            "electricity market", "energy trading", "game theory", "mechanism design",
            "peer-to-peer energy",
        ],
        "watch": ["新型主体入市规则", "现货价格波动", "策略收益与系统成本差异"],
        "action": "将市场规则显式纳入智能体环境，评估策略稳定性与机制相容性。",
    },
    "multi_agent_rl": {
        "label": "多智能体强化学习",
        "keywords": [
            "多智能体强化学习", "多智能体", "强化学习", "协同学习",
            "multi-agent reinforcement learning", "multi agent reinforcement learning",
            "marl", "cooperative learning",
        ],
        "watch": ["训练样本效率", "多主体非平稳性", "策略可解释与迁移能力"],
        "action": "统一比较集中训练分散执行、博弈基线与安全约束消融。",
    },
    "digital_twin": {
        "label": "数字孪生与工程验证",
        "keywords": [
            "数字孪生", "仿真验证", "硬件在环", "工程验证", "物理信息",
            "digital twin", "hardware-in-the-loop", "simulation validation",
            "physics-informed",
        ],
        "watch": ["仿真—实物偏差", "硬件在环覆盖工况", "模型在线校准频率"],
        "action": "搭建数字孪生到硬件在环的分级验证链，量化仿真—实物差距。",
    },
}


class ForecastAnalyzer:
    """Produce normalized trends, robust forecasts, and falsifiable scenarios."""

    def __init__(self, config: Dict[str, Any] | None = None):
        settings = (config or {}).get("analysis", {}).get("forecast", {})
        self.history_months = max(1, int(settings.get("history_months", 24)))
        self.min_quant_months = max(2, int(settings.get("min_quant_months", 12)))
        self.min_nonzero_months = max(2, int(settings.get("min_nonzero_months", 6)))
        self.min_topic_documents = max(2, int(settings.get("min_topic_documents", 12)))
        self.strategic_min_months = max(
            self.min_quant_months, int(settings.get("strategic_min_months", 18))
        )
        self.strategic_min_documents = max(
            self.min_topic_documents, int(settings.get("strategic_min_documents", 24))
        )
        self.random_state = int(settings.get("random_state", 42))

    def analyze(
        self,
        observations: List[Dict[str, Any]],
        *,
        coverage: Dict[str, Any] | None = None,
        as_of: str | date | None = None,
    ) -> Dict[str, Any]:
        resolved_as_of = _as_date(as_of) if as_of else date.today()
        if resolved_as_of is None:
            raise ValueError(f"Invalid as_of date: {as_of}")
        months = _month_keys(resolved_as_of, self.history_months)
        normalized = _normalize_documents(observations, months)
        coverage_index = _coverage_index(coverage or {})
        available_months = _available_months(months, normalized, coverage_index)
        source_totals = _source_totals(normalized)
        topic_documents = _topic_documents(normalized)

        topic_series: Dict[str, List[Dict[str, Any]]] = {}
        forecasts: List[Dict[str, Any]] = []
        scenarios: List[Dict[str, Any]] = []
        lead_lag: List[Dict[str, Any]] = []
        for topic_id, definition in TOPIC_TAXONOMY.items():
            evidence = topic_documents.get(topic_id, [])
            series = _build_topic_series(
                months, evidence, source_totals, available_months
            )
            topic_series[topic_id] = series
            metrics = _topic_metrics(series, evidence)
            forecast = self._forecast_topic(
                topic_id, definition, series, evidence, metrics
            )
            forecasts.append(forecast)
            scenarios.append(_scenario(topic_id, definition, forecast, metrics))
            lead_lag.append(_lead_lag(topic_id, definition, evidence))

        source_counts = Counter(
            str(item["document"].get("source_type") or "unknown")
            for item in normalized
        )
        coverage_statuses = Counter(
            str(entry.get("status") or "unknown")
            for entry in coverage_index.values()
        )
        dated_months = sorted({item["month"] for item in normalized})
        quality_gaps = []
        if len(available_months) < self.min_quant_months:
            quality_gaps.append(
                f"仅有 {len(available_months)} 个可用月份，定量预测至少需要 {self.min_quant_months} 个"
            )
        if coverage_statuses.get("partial") or coverage_statuses.get("unavailable"):
            quality_gaps.append("部分来源月份覆盖不完整，缺口未按零值处理")
        if len(source_counts) < 2:
            quality_gaps.append("来源类型少于两个，无法确认跨来源传导")

        return {
            "schema_version": "2.0",
            "generation_mode": "deterministic_metrics",
            "as_of": resolved_as_of.isoformat(),
            "horizons": {
                "near_term": {"months": [1, 3], "label": "近期 1–3 个月"},
                "strategic": {"months": [6, 12], "label": "战略 6–12 个月"},
            },
            "taxonomy": [
                {"id": topic_id, "label": value["label"]}
                for topic_id, value in TOPIC_TAXONOMY.items()
            ],
            "data_quality": {
                "period_start": f"{months[0]}-01",
                "period_end": resolved_as_of.isoformat(),
                "document_count": len(normalized),
                "dated_months": dated_months,
                "available_months": available_months,
                "history_month_count": len(available_months),
                "source_counts": dict(source_counts),
                "coverage_status_counts": dict(coverage_statuses),
                "gaps": quality_gaps,
            },
            "topic_series": topic_series,
            "forecasts": forecasts,
            "scenarios": scenarios,
            "lead_lag": lead_lag,
            "evidence_ids": list(dict.fromkeys(
                evidence_id
                for item in forecasts for evidence_id in item["evidence_ids"]
            )),
            "counter_signals": list(dict.fromkeys(
                signal for item in forecasts for signal in item["counter_signals"]
            )),
            "watch_indicators": list(dict.fromkeys(
                indicator for item in forecasts for indicator in item["watch_indicators"]
            )),
        }

    def _forecast_topic(
        self,
        topic_id: str,
        definition: Dict[str, Any],
        series: List[Dict[str, Any]],
        evidence: List[Dict[str, Any]],
        metrics: Dict[str, Any],
    ) -> Dict[str, Any]:
        usable = [point for point in series if point["available"]]
        gaps = []
        if len(usable) < self.min_quant_months:
            gaps.append(f"可用月份 {len(usable)}/{self.min_quant_months}")
        if metrics["nonzero_months"] < self.min_nonzero_months:
            gaps.append(
                f"非零月份 {metrics['nonzero_months']}/{self.min_nonzero_months}"
            )
        if len(evidence) < self.min_topic_documents:
            gaps.append(f"主题材料 {len(evidence)}/{self.min_topic_documents}")

        projections: List[Dict[str, Any]] = []
        mode = "scenario_only"
        trajectory = _trajectory(metrics["velocity"])
        if not gaps:
            values = np.array([float(point["share"]) for point in usable])
            x = np.arange(len(values), dtype=float).reshape(-1, 1)
            model = TheilSenRegressor(random_state=self.random_state)
            model.fit(x, values)
            fitted = model.predict(x)
            residuals = values - fitted
            low_residual, high_residual = np.quantile(residuals, [0.1, 0.9])
            for horizon in (1, 3):
                predicted = float(model.predict([[len(values) - 1 + horizon]])[0])
                scale = sqrt(horizon)
                projections.append({
                    "months_ahead": horizon,
                    "share": round(_clip(predicted), 4),
                    "lower": round(_clip(predicted + float(low_residual) * scale), 4),
                    "upper": round(_clip(predicted + float(high_residual) * scale), 4),
                })
            slope = float(model.coef_[0])
            trajectory = _trajectory(slope)
            mode = "quantitative"

        source_types = sorted({
            str(item["document"].get("source_type") or "unknown")
            for item in evidence
        })
        strategic_ready = (
            len(usable) >= self.strategic_min_months
            and len(evidence) >= self.strategic_min_documents
            and len(source_types) >= 2
        )
        confidence = "low"
        if mode == "quantitative":
            confidence = "high" if strategic_ready else "medium"
        counter_signals = _counter_signals(metrics, source_types, gaps)
        evidence_ids = [
            str(item["document"].get("id") or "")
            for item in sorted(
                evidence, key=lambda item: item["event_date"], reverse=True
            )[:6]
            if item["document"].get("id")
        ]
        drivers = _drivers(metrics, source_types)
        return {
            "topic_id": topic_id,
            "topic": definition["label"],
            "mode": mode,
            "trajectory": trajectory,
            "confidence": confidence,
            "strategic_ready": strategic_ready,
            "metrics": metrics,
            "projections": projections,
            "drivers": drivers,
            "data_gaps": gaps,
            "evidence_ids": evidence_ids,
            "counter_signals": counter_signals,
            "watch_indicators": list(definition["watch"]),
            "research_action": definition["action"],
        }


def _normalize_documents(
    observations: Iterable[Dict[str, Any]], months: List[str]
) -> List[Dict[str, Any]]:
    by_id: Dict[str, Dict[str, Any]] = {}
    allowed = set(months)
    for observation in observations:
        document = observation.get("document") or observation
        if not isinstance(document, dict):
            continue
        event_date = _event_date(document)
        document_id = str(
            document.get("id") or document.get("url") or document.get("title") or ""
        )
        if not event_date or event_date.strftime("%Y-%m") not in allowed or not document_id:
            continue
        candidate = {
            "document": document,
            "document_id": document_id,
            "event_date": event_date,
            "month": event_date.strftime("%Y-%m"),
        }
        existing = by_id.get(document_id)
        if existing is None or len(_searchable(document)) > len(_searchable(existing["document"])):
            by_id[document_id] = candidate
    return sorted(by_id.values(), key=lambda item: (item["event_date"], item["document_id"]))


def _topic_documents(
    documents: List[Dict[str, Any]],
) -> Dict[str, List[Dict[str, Any]]]:
    grouped: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for item in documents:
        searchable = _searchable(item["document"])
        for topic_id, definition in TOPIC_TAXONOMY.items():
            if any(keyword.casefold() in searchable for keyword in definition["keywords"]):
                grouped[topic_id].append(item)
    return grouped


def _searchable(document: Dict[str, Any]) -> str:
    values: List[str] = []
    for field in (
        "title", "summary", "research_relevance", "raw_text", "keywords",
        "tags", "themes", "research_direction", "topic_directions",
        "technology_directions", "impact_areas",
    ):
        raw = document.get(field)
        if isinstance(raw, (list, tuple, set)):
            values.extend(str(value) for value in raw)
        elif raw:
            values.append(str(raw))
    return " ".join(values).casefold()


def _source_totals(documents: List[Dict[str, Any]]) -> Dict[str, Counter]:
    totals: Dict[str, Counter] = defaultdict(Counter)
    for item in documents:
        source = str(item["document"].get("source_type") or "unknown")
        totals[item["month"]][source] += 1
    return totals


def _build_topic_series(
    months: List[str],
    evidence: List[Dict[str, Any]],
    source_totals: Dict[str, Counter],
    available_months: List[str],
) -> List[Dict[str, Any]]:
    topic_counts: Dict[str, Counter] = defaultdict(Counter)
    for item in evidence:
        source = str(item["document"].get("source_type") or "unknown")
        topic_counts[item["month"]][source] += 1
    available = set(available_months)
    series = []
    for month in months:
        counts = topic_counts.get(month, Counter())
        totals = source_totals.get(month, Counter())
        normalized_parts = [
            counts[source] / total
            for source, total in totals.items() if total > 0
        ]
        share = sum(normalized_parts) / len(normalized_parts) if normalized_parts else 0.0
        series.append({
            "month": month,
            "available": month in available,
            "document_count": int(sum(counts.values())),
            "source_counts": dict(counts),
            "share": round(float(share), 4),
        })
    return series


def _topic_metrics(
    series: List[Dict[str, Any]], evidence: List[Dict[str, Any]]
) -> Dict[str, Any]:
    usable = [point for point in series if point["available"]]
    shares = [float(point["share"]) for point in usable]
    recent = _mean(shares[-3:])
    previous = _mean(shares[-6:-3])
    older = _mean(shares[-9:-6])
    velocity = recent - previous
    acceleration = velocity - (previous - older)
    source_types = {
        str(item["document"].get("source_type") or "unknown")
        for item in evidence
    }
    return {
        "document_count": len(evidence),
        "available_months": len(usable),
        "nonzero_months": sum(point["document_count"] > 0 for point in usable),
        "velocity": round(velocity, 4),
        "acceleration": round(acceleration, 4),
        "persistence": round(
            sum(point["document_count"] > 0 for point in usable[-6:])
            / max(1, len(usable[-6:])),
            3,
        ),
        "source_diversity": len(source_types),
    }


def _lead_lag(
    topic_id: str, definition: Dict[str, Any], evidence: List[Dict[str, Any]]
) -> Dict[str, Any]:
    grouped: Dict[str, List[date]] = defaultdict(list)
    for item in evidence:
        source = str(item["document"].get("source_type") or "unknown")
        grouped[source].append(item["event_date"])
    supported = {source: dates for source, dates in grouped.items() if len(dates) >= 2}
    sequence = sorted(
        (
            {"source_type": source, "onset": min(dates).isoformat(), "count": len(dates)}
            for source, dates in supported.items()
        ),
        key=lambda item: item["onset"],
    )
    lag_months = None
    if len(sequence) >= 2:
        start = _as_date(sequence[0]["onset"])
        end = _as_date(sequence[-1]["onset"])
        if start and end:
            lag_months = (end.year - start.year) * 12 + end.month - start.month
    return {
        "topic_id": topic_id,
        "topic": definition["label"],
        "status": "supported" if len(sequence) >= 2 else "insufficient",
        "sequence": sequence,
        "lag_months": lag_months,
        "limitation": "每类来源至少需要2条材料" if len(sequence) < 2 else "时间顺序不等同于因果关系",
    }


def _scenario(
    topic_id: str,
    definition: Dict[str, Any],
    forecast: Dict[str, Any],
    metrics: Dict[str, Any],
) -> Dict[str, Any]:
    trajectory = forecast["trajectory"]
    label = definition["label"]
    base = {
        "rising": f"{label}在未来6–12个月保持扩张，但工程验证将成为主要约束。",
        "declining": f"{label}短期关注可能回落，研究价值取决于新的验证证据。",
        "stable": f"{label}预计保持稳定推进，增量来自方法整合而非单点热度。",
    }[trajectory]
    return {
        "topic_id": topic_id,
        "topic": label,
        "confidence": forecast["confidence"],
        "base_case": base,
        "upside": f"若政策、论文与工程报告连续两个季度同向增加，{label}可能进入加速阶段。",
        "downside": f"若持续性低于50%或关键验证指标无改善，{label}可能停留在概念验证阶段。",
        "triggers": list(definition["watch"]),
        "assumptions": forecast["data_gaps"] or ["历史主题占比具有延续性"],
        "evidence_ids": list(forecast["evidence_ids"]),
        "counter_signals": list(forecast["counter_signals"]),
        "research_action": definition["action"],
        "persistence": metrics["persistence"],
    }


def _drivers(metrics: Dict[str, Any], source_types: List[str]) -> List[str]:
    drivers = [
        f"近三个月归一化速度 {metrics['velocity']:+.3f}",
        f"最近六个月持续性 {metrics['persistence']:.0%}",
        f"覆盖 {len(source_types)} 类来源",
    ]
    return drivers


def _counter_signals(
    metrics: Dict[str, Any], source_types: List[str], gaps: List[str]
) -> List[str]:
    signals = list(gaps)
    if metrics["velocity"] <= 0:
        signals.append("近期归一化主题占比未增长")
    if metrics["persistence"] < 0.5:
        signals.append("最近六个月信号持续性低于50%")
    if len(source_types) < 2:
        signals.append("尚无跨来源相互印证")
    return signals or ["尚未观察到明确反向信号；需继续监测预测区间外变化"]


def _coverage_index(coverage: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    entries = coverage.get("entries", {}) if isinstance(coverage, dict) else {}
    return entries if isinstance(entries, dict) else {}


def _available_months(
    months: List[str],
    documents: List[Dict[str, Any]],
    coverage: Dict[str, Dict[str, Any]],
) -> List[str]:
    observed = {item["month"] for item in documents}
    covered = {
        str(entry.get("period") or "")
        for entry in coverage.values()
        if entry.get("status") == "complete"
    }
    return [month for month in months if month in observed or month in covered]


def _month_keys(as_of: date, count: int) -> List[str]:
    keys = []
    current = as_of.year * 12 + as_of.month - 1
    for offset in reversed(range(count)):
        year, zero_month = divmod(current - offset, 12)
        keys.append(f"{year:04d}-{zero_month + 1:02d}")
    return keys


def _event_date(document: Dict[str, Any]) -> date | None:
    for field in (
        "published_at", "published", "publication_date", "issued_at",
        "release_date", "date",
    ):
        value = _as_date(document.get(field))
        if value:
            return value
    return None


def _as_date(value: Any) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value or "").strip()
    try:
        return date.fromisoformat(text[:10]) if text else None
    except ValueError:
        return None


def _mean(values: List[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _clip(value: float) -> float:
    return max(0.0, min(1.0, value))


def _trajectory(value: float) -> str:
    if value > 0.01:
        return "rising"
    if value < -0.01:
        return "declining"
    return "stable"
