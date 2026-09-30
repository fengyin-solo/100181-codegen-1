"""水质判定纯规则：指标定义、限值校验与达标/预警/超标判定。

这里只放不依赖数据仓库的纯函数，采样登记、口径重算、示例数据冻结快照都走同一份规则，
保证「采样点维护与指标录入共用同一份口径」在后端只有一个判定来源。
"""
from __future__ import annotations

from typing import Any

# 参与判定的指标及其单位、展示顺序
METRIC_ORDER: list[str] = ["余氯", "浊度", "pH"]
METRIC_UNITS: dict[str, str] = {"余氯": "mg/L", "浊度": "NTU", "pH": ""}

# 每个指标的四段边界：min/max 为合格上下限（落在外面即超标），
# warn_min/warn_max 为预警带（合格区间内部、贴近限值的一段）。
# 单侧指标（浊度只有上限）允许 min、warn_min 为 None。
LIMIT_KEYS: list[str] = ["min", "warn_min", "warn_max", "max"]
RESULT_ORDER: dict[str, int] = {"达标": 0, "预警": 1, "超标": 2}

# 新建片区时的初始口径
DEFAULT_LIMITS: dict[str, dict[str, float | None]] = {
    "余氯": {"min": 0.05, "warn_min": 0.10, "warn_max": 0.30, "max": 0.50},
    "浊度": {"min": None, "warn_min": None, "warn_max": 0.50, "max": 1.00},
    "pH": {"min": 6.5, "warn_min": 6.8, "warn_max": 8.0, "max": 8.5},
}


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def validate_limits(limits: dict[str, Any]) -> str:
    """校验一整版限值；返回空串表示通过，否则返回可读的错误说明。"""
    if not isinstance(limits, dict):
        return "限值必须按指标分组提供"
    for metric in METRIC_ORDER:
        limit = limits.get(metric)
        if not isinstance(limit, dict):
            return f"指标「{metric}」缺少限值配置"
        bounds: list[float] = []
        for key in LIMIT_KEYS:
            value = limit.get(key)
            if value is None:
                continue
            if not _is_number(value):
                return f"指标「{metric}」的{key}必须是数字或留空"
            bounds.append(float(value))
        if not bounds:
            return f"指标「{metric}」至少要设置一侧限值"
        if any(left > right for left, right in zip(bounds, bounds[1:])):
            return f"指标「{metric}」的限值需满足 下限≤预警下限≤预警上限≤上限"
        if limit.get("min") is None and limit.get("max") is None:
            return f"指标「{metric}」不能上下限都为空"
    return ""


def evaluate_metric(limit: dict[str, Any], value: float) -> str:
    """单个指标判定：限外超标，限内但进入预警带为预警，其余达标。"""
    low, high = limit.get("min"), limit.get("max")
    warn_low, warn_high = limit.get("warn_min"), limit.get("warn_max")
    if (low is not None and value < float(low)) or (high is not None and value > float(high)):
        return "超标"
    if (warn_low is not None and value < float(warn_low)) or (
        warn_high is not None and value > float(warn_high)
    ):
        return "预警"
    return "达标"


def evaluate_batch(
    limits: dict[str, Any], readings: dict[str, float]
) -> dict[str, Any]:
    """按一版限值判定整批采样：批次结论取所有指标里最严重的一档。"""
    metrics: list[dict[str, Any]] = []
    for metric in METRIC_ORDER:
        value = float(readings[metric])
        result = evaluate_metric(limits[metric], value)
        metrics.append(
            {
                "指标": metric,
                "数值": value,
                "单位": METRIC_UNITS[metric],
                "结果": result,
            }
        )
    conclusion = max(metrics, key=lambda item: RESULT_ORDER[item["结果"]])["结果"]
    return {"conclusion": conclusion, "metrics": metrics}


def limits_equal(left: dict[str, Any], right: dict[str, Any]) -> bool:
    """两版限值是否完全一致（数值按 float 比较，容忍 1/None 与 1.0 之类的差异）。"""
    for metric in METRIC_ORDER:
        a, b = left.get(metric) or {}, right.get(metric) or {}
        for key in LIMIT_KEYS:
            av, bv = a.get(key), b.get(key)
            av_n = None if av is None else float(av)
            bv_n = None if bv is None else float(bv)
            if av_n != bv_n:
                return False
    return True


def limits_summary(limits: dict[str, Any]) -> str:
    """把一版限值压成一行摘要，供采样点维护页展示「当前共用口径」。"""
    parts: list[str] = []
    for metric in METRIC_ORDER:
        limit = limits.get(metric) or {}
        low, high = limit.get("min"), limit.get("max")
        left = "—" if low is None else f"{float(low):g}"
        right = "—" if high is None else f"{float(high):g}"
        unit = METRIC_UNITS[metric]
        parts.append(f"{metric} {left}~{right}{unit}")
    return "；".join(parts)
