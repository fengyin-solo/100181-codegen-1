"""水质采样检测业务规则。

片区限值采用“发布新版本”的方式保留历史：采样记录出结论时固化当时版本；
片区发布新口径后，只自动重算尚未出结论且指标完整的记录，已出结论记录不改写。
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from math import isfinite
from typing import Any

from app.store import store

AREA_MODULE = "water_areas"
POINT_MODULE = "water_points"
STANDARD_MODULE = "water_standards"
SAMPLE_MODULE = "water_samples"

RESULT_PENDING = "待判定"
RESULT_QUALIFIED = "达标"
RESULT_WARNING = "预警"
RESULT_EXCEEDED = "超标"
RESULT_ORDER = [RESULT_QUALIFIED, RESULT_WARNING, RESULT_EXCEEDED]

DEFAULT_INDICATORS = [
    {
        "code": "residual_chlorine",
        "name": "余氯",
        "unit": "mg/L",
        "warning_low": 0.30,
        "warning_high": 1.20,
        "limit_low": 0.10,
        "limit_high": 2.00,
    },
    {
        "code": "turbidity",
        "name": "浊度",
        "unit": "NTU",
        "warning_low": 0.00,
        "warning_high": 1.00,
        "limit_low": 0.00,
        "limit_high": 3.00,
    },
    {
        "code": "ph",
        "name": "pH",
        "unit": "",
        "warning_low": 7.00,
        "warning_high": 8.00,
        "limit_low": 6.50,
        "limit_high": 8.50,
    },
]


def _number(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if isfinite(number) else None


def _next_id(rows: list[dict[str, Any]]) -> int:
    return max((int(row.get("id", 0)) for row in rows), default=0) + 1


def _clean(value: Any) -> str:
    return str(value or "").strip()


class WaterQualityService:
    def __init__(self) -> None:
        self.ensure_seed()

    def ensure_seed(self) -> None:
        """补齐内存表和演示数据，避免新增模块依赖手工改一大段种子文件。"""
        if store.rows(AREA_MODULE):
            return

        now = "2026-09-30 09:00"
        store.rows(AREA_MODULE).extend([
            {"id": 1, "name": "城东片区", "manager": "王敏", "remark": "市政末梢与二次供水", "created_at": "2026-09-01 09:00"},
            {"id": 2, "name": "城西片区", "manager": "陈立", "remark": "老城区取水点", "created_at": "2026-09-01 09:00"},
        ])
        store.rows(POINT_MODULE).extend([
            {"id": 1, "code": "WQ001", "name": "城东管网末梢点", "area_id": 1, "address": "河东大街 18 号", "contact": "王敏", "created_at": "2026-09-01 09:00"},
            {"id": 2, "code": "WQ002", "name": "城东小区二次供水点", "area_id": 1, "address": "梧桐小区泵房", "contact": "周倩", "created_at": "2026-09-01 09:00"},
            {"id": 3, "code": "WQ003", "name": "城西市政取水点", "area_id": 2, "address": "河西桥西 200 米", "contact": "陈立", "created_at": "2026-09-01 09:00"},
        ])
        standards = [
            {
                "id": 1,
                "area_id": 1,
                "version": "V1",
                "is_current": True,
                "note": "城东初始限值",
                "created_at": "2026-09-01 09:00",
                "indicators": deepcopy(DEFAULT_INDICATORS),
            },
            {
                "id": 2,
                "area_id": 2,
                "version": "V1",
                "is_current": False,
                "note": "城西初始限值",
                "created_at": "2026-09-01 09:00",
                "indicators": deepcopy(DEFAULT_INDICATORS),
            },
            {
                "id": 3,
                "area_id": 2,
                "version": "V2",
                "is_current": True,
                "note": "城西浊度收紧",
                "created_at": "2026-09-20 09:00",
                "indicators": [
                    {
                        "code": "residual_chlorine",
                        "name": "余氯",
                        "unit": "mg/L",
                        "warning_low": 0.35,
                        "warning_high": 1.10,
                        "limit_low": 0.10,
                        "limit_high": 2.00,
                    },
                    {
                        "code": "turbidity",
                        "name": "浊度",
                        "unit": "NTU",
                        "warning_low": 0.00,
                        "warning_high": 0.80,
                        "limit_low": 0.00,
                        "limit_high": 2.00,
                    },
                    {
                        "code": "ph",
                        "name": "pH",
                        "unit": "",
                        "warning_low": 7.00,
                        "warning_high": 8.00,
                        "limit_low": 6.50,
                        "limit_high": 8.50,
                    },
                ],
            },
        ]
        store.rows(STANDARD_MODULE).extend(standards)

        samples = [
            {
                "id": 1,
                "batch_no": "WQ-20260920-0001",
                "point_id": 1,
                "area_id": 1,
                "sampled_at": "2026-09-20T09:00",
                "sampler": "王敏",
                "values": {"residual_chlorine": 0.42, "turbidity": 0.42, "ph": 7.20},
                "reason": "",
                "finalized": True,
                "result": RESULT_QUALIFIED,
                "standard_id": 1,
                "finalized_at": "2026-09-20T10:00",
            },
            {
                "id": 2,
                "batch_no": "WQ-20260925-0002",
                "point_id": 2,
                "area_id": 1,
                "sampled_at": "2026-09-25T10:00",
                "sampler": "周倩",
                "values": {"residual_chlorine": 0.45, "turbidity": 0.62, "ph": 7.30},
                "reason": "",
                "finalized": True,
                "result": RESULT_QUALIFIED,
                "standard_id": 1,
                "finalized_at": "2026-09-25T11:00",
            },
            {
                "id": 3,
                "batch_no": "WQ-20260928-0003",
                "point_id": 1,
                "area_id": 1,
                "sampled_at": "2026-09-28T09:00",
                "sampler": "王敏",
                "values": {"residual_chlorine": 0.08, "turbidity": 2.20, "ph": 6.90},
                "reason": "暴雨后管网冲刷导致末梢余氯下降，已安排放水冲洗并复测。",
                "finalized": True,
                "result": RESULT_EXCEEDED,
                "standard_id": 1,
                "finalized_at": "2026-09-28T10:30",
            },
            {
                "id": 4,
                "batch_no": "WQ-20260918-0004",
                "point_id": 3,
                "area_id": 2,
                "sampled_at": "2026-09-18T09:00",
                "sampler": "陈立",
                "values": {"residual_chlorine": 0.40, "turbidity": 0.95, "ph": 7.20},
                "reason": "",
                "finalized": True,
                "result": RESULT_QUALIFIED,
                "standard_id": 2,
                "finalized_at": "2026-09-18T10:00",
            },
            {
                "id": 5,
                "batch_no": "WQ-20260929-0005",
                "point_id": 3,
                "area_id": 2,
                "sampled_at": "2026-09-29T09:00",
                "sampler": "陈立",
                "values": {"residual_chlorine": 0.40, "turbidity": 0.95, "ph": 7.20},
                "reason": "",
                "finalized": False,
                "result": RESULT_PENDING,
                "standard_id": None,
                "finalized_at": None,
            },
        ]
        for sample in samples:
            standard = next(item for item in standards if item["id"] == sample["standard_id"]) if sample["standard_id"] else None
            if standard:
                evaluation, _ = self.evaluate(sample["values"], standard)
                sample["metric_results"] = evaluation
            else:
                sample["metric_results"] = []
            sample["status"] = sample["result"]
            sample["pending"] = not sample["finalized"]
            sample["abnormal"] = sample["result"] == RESULT_EXCEEDED
            sample["created_at"] = now
        store.rows(SAMPLE_MODULE).extend(samples)

    def _areas_by_id(self) -> dict[int, dict[str, Any]]:
        return {int(row["id"]): row for row in store.rows(AREA_MODULE)}

    def _points_by_id(self) -> dict[int, dict[str, Any]]:
        return {int(row["id"]): row for row in store.rows(POINT_MODULE)}

    def _standards_by_id(self) -> dict[int, dict[str, Any]]:
        return {int(row["id"]): row for row in store.rows(STANDARD_MODULE)}

    def current_standard(self, area_id: int) -> dict[str, Any] | None:
        for standard in store.rows(STANDARD_MODULE):
            if int(standard.get("area_id", 0)) == area_id and standard.get("is_current"):
                return standard
        return None

    def serialize_area(self, row: dict[str, Any]) -> dict[str, Any]:
        item = dict(row)
        standard = self.current_standard(int(row["id"]))
        item["current_version"] = standard.get("version") if standard else None
        item["current_standard_id"] = standard.get("id") if standard else None
        item["indicator_count"] = len(standard.get("indicators", [])) if standard else 0
        return item

    def list_areas(self) -> list[dict[str, Any]]:
        return [self.serialize_area(row) for row in sorted(store.rows(AREA_MODULE), key=lambda item: int(item["id"]))]

    def create_area(self, values: dict[str, Any]) -> tuple[dict[str, Any] | None, str]:
        name = _clean(values.get("name"))
        if not name:
            return None, "片区名称不能为空"
        if any(_clean(row.get("name")) == name for row in store.rows(AREA_MODULE)):
            return None, "片区名称已存在"
        row = {
            "id": _next_id(store.rows(AREA_MODULE)),
            "name": name,
            "manager": _clean(values.get("manager")),
            "remark": _clean(values.get("remark")),
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        }
        store.rows(AREA_MODULE).append(row)
        return self.serialize_area(row), ""

    def update_area(self, area_id: int, values: dict[str, Any]) -> tuple[dict[str, Any] | None, str]:
        row = self._areas_by_id().get(area_id)
        if row is None:
            return None, f"片区 {area_id} 不存在"
        name = _clean(values.get("name"))
        if not name:
            return None, "片区名称不能为空"
        if any(_clean(item.get("name")) == name and int(item["id"]) != area_id for item in store.rows(AREA_MODULE)):
            return None, "片区名称已存在"
        row["name"] = name
        row["manager"] = _clean(values.get("manager"))
        row["remark"] = _clean(values.get("remark"))
        return self.serialize_area(row), ""

    def serialize_point(self, row: dict[str, Any]) -> dict[str, Any]:
        item = dict(row)
        area = self._areas_by_id().get(int(row.get("area_id", 0)))
        item["area_name"] = area.get("name", "未知片区") if area else "未知片区"
        standard = self.current_standard(int(row.get("area_id", 0))) if area else None
        item["current_version"] = standard.get("version") if standard else None
        return item

    def list_points(self, *, area_id: int | None = None, keyword: str | None = None) -> list[dict[str, Any]]:
        rows = store.rows(POINT_MODULE)
        if area_id is not None:
            rows = [row for row in rows if int(row.get("area_id", 0)) == area_id]
        if keyword:
            rows = [
                row for row in rows
                if keyword in _clean(row.get("code")) or keyword in _clean(row.get("name")) or keyword in _clean(row.get("address"))
            ]
        return [self.serialize_point(row) for row in sorted(rows, key=lambda item: int(item["id"]))]

    def _save_point_values(self, row: dict[str, Any] | None, values: dict[str, Any]) -> tuple[dict[str, Any] | None, str]:
        code = _clean(values.get("code"))
        name = _clean(values.get("name"))
        area_value = _number(values.get("area_id"))
        if not code or not name:
            return None, "采样点编号和名称不能为空"
        area_id = int(area_value) if area_value is not None else 0
        if area_id not in self._areas_by_id():
            return None, "请选择有效片区"
        current_id = int(row["id"]) if row else None
        if any(_clean(item.get("code")) == code and int(item["id"]) != current_id for item in store.rows(POINT_MODULE)):
            return None, "采样点编号已存在"
        payload = {
            "code": code,
            "name": name,
            "area_id": area_id,
            "address": _clean(values.get("address")),
            "contact": _clean(values.get("contact")),
        }
        if row is None:
            payload["id"] = _next_id(store.rows(POINT_MODULE))
            payload["created_at"] = datetime.now().strftime("%Y-%m-%d %H:%M")
            store.rows(POINT_MODULE).append(payload)
            return payload, ""
        row.update(payload)
        return row, ""

    def create_point(self, values: dict[str, Any]) -> tuple[dict[str, Any] | None, str]:
        row, message = self._save_point_values(None, values)
        return (self.serialize_point(row), "") if row else (None, message)

    def update_point(self, point_id: int, values: dict[str, Any]) -> tuple[dict[str, Any] | None, str]:
        row = self._points_by_id().get(point_id)
        if row is None:
            return None, f"采样点 {point_id} 不存在"
        saved, message = self._save_point_values(row, values)
        return (self.serialize_point(saved), "") if saved else (None, message)

    def serialize_standard(self, row: dict[str, Any]) -> dict[str, Any]:
        item = dict(row)
        item["indicators"] = deepcopy(row.get("indicators", []))
        area = self._areas_by_id().get(int(row.get("area_id", 0)))
        item["area_name"] = area.get("name", "未知片区") if area else "未知片区"
        return item

    def list_standards(self, *, area_id: int | None = None) -> list[dict[str, Any]]:
        rows = store.rows(STANDARD_MODULE)
        if area_id is not None:
            rows = [row for row in rows if int(row.get("area_id", 0)) == area_id]
        rows = sorted(rows, key=lambda item: (int(item.get("area_id", 0)), -int(item.get("id", 0))))
        return [self.serialize_standard(row) for row in rows]

    def _parse_indicators(self, values: dict[str, Any]) -> tuple[list[dict[str, Any]] | None, str]:
        raw_indicators = values.get("indicators") if isinstance(values.get("indicators"), list) else None
        if not raw_indicators:
            return None, "至少维护一个检测指标"
        indicators: list[dict[str, Any]] = []
        codes: set[str] = set()
        for index, raw in enumerate(raw_indicators, start=1):
            if not isinstance(raw, dict):
                return None, f"第 {index} 个指标格式不正确"
            name = _clean(raw.get("name"))
            if not name:
                return None, f"第 {index} 个指标名称不能为空"
            numbers = {
                key: _number(raw.get(key))
                for key in ["warning_low", "warning_high", "limit_low", "limit_high"]
            }
            if any(number is None for number in numbers.values()):
                return None, f"指标「{name}」的预警和超标限值必须都是数字"
            warning_low, warning_high, limit_low, limit_high = (
                numbers["warning_low"], numbers["warning_high"], numbers["limit_low"], numbers["limit_high"]
            )
            assert warning_low is not None and warning_high is not None and limit_low is not None and limit_high is not None
            if not (limit_low <= warning_low <= warning_high <= limit_high):
                return None, f"指标「{name}」的限值需满足：下限 ≤ 预警下限 ≤ 预警上限 ≤ 上限"
            code = _clean(raw.get("code")) or f"m{index}"
            if code in codes:
                code = f"{code}_{index}"
            codes.add(code)
            indicators.append({
                "code": code,
                "name": name,
                "unit": _clean(raw.get("unit")),
                "warning_low": warning_low,
                "warning_high": warning_high,
                "limit_low": limit_low,
                "limit_high": limit_high,
            })
        return indicators, ""

    def create_standard(self, values: dict[str, Any]) -> tuple[dict[str, Any] | None, str, dict[str, int]]:
        area_id = int(_number(values.get("area_id")) or 0)
        if area_id not in self._areas_by_id():
            return None, "请选择有效片区", {}
        indicators, message = self._parse_indicators(values)
        if indicators is None:
            return None, message, {}

        area_standards = [row for row in store.rows(STANDARD_MODULE) if int(row.get("area_id", 0)) == area_id]
        version_number = len(area_standards) + 1
        for row in area_standards:
            row["is_current"] = False
        standard = {
            "id": _next_id(store.rows(STANDARD_MODULE)),
            "area_id": area_id,
            "version": f"V{version_number}",
            "is_current": True,
            "note": _clean(values.get("note")) or f"第 {version_number} 版限值",
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "indicators": indicators,
        }
        store.rows(STANDARD_MODULE).append(standard)
        recalculated, waiting_reason = self.recalculate_open_samples(area_id)
        return self.serialize_standard(standard), "", {"recalculated": recalculated, "waiting_reason": waiting_reason}

    def evaluate(
        self,
        values: dict[str, Any],
        standard: dict[str, Any],
    ) -> tuple[list[dict[str, Any]], str]:
        details: list[dict[str, Any]] = []
        overall = RESULT_QUALIFIED
        for indicator in standard.get("indicators", []):
            value = _number(values.get(indicator["code"]))
            if value is None:
                return [], RESULT_PENDING
            level = RESULT_QUALIFIED
            message = "处于正常区间"
            if value < float(indicator["limit_low"]) or value > float(indicator["limit_high"]):
                level = RESULT_EXCEEDED
                message = f"超出限值 {indicator['limit_low']}～{indicator['limit_high']}"
            elif value < float(indicator["warning_low"]) or value > float(indicator["warning_high"]):
                level = RESULT_WARNING
                message = f"进入预警区间 {indicator['warning_low']}～{indicator['warning_high']}"
            if RESULT_ORDER.index(level) > RESULT_ORDER.index(overall):
                overall = level
            details.append({
                "code": indicator["code"],
                "name": indicator["name"],
                "unit": indicator.get("unit", ""),
                "value": value,
                "level": level,
                "message": message,
            })
        return details, overall

    def recalculate_open_samples(self, area_id: int) -> tuple[int, int]:
        """按新口径重算本片区未出结论记录，发布时调用。"""
        standard = self.current_standard(area_id)
        if standard is None:
            return 0, 0
        recalculated = 0
        waiting_reason = 0
        for sample in store.rows(SAMPLE_MODULE):
            if sample.get("finalized") or int(sample.get("area_id", 0)) != area_id:
                continue
            details, result = self.evaluate(sample.get("values", {}), standard)
            if result == RESULT_PENDING:
                continue
            reason = _clean(sample.get("reason"))
            if result == RESULT_EXCEEDED and not reason:
                waiting_reason += 1
                continue
            self._apply_conclusion(sample, standard, result, details, reason)
            recalculated += 1
        return recalculated, waiting_reason

    def _apply_conclusion(
        self,
        sample: dict[str, Any],
        standard: dict[str, Any],
        result: str,
        details: list[dict[str, Any]],
        reason: str,
    ) -> None:
        sample["finalized"] = True
        sample["result"] = result
        sample["metric_results"] = details
        sample["standard_id"] = int(standard["id"])
        sample["reason"] = reason if result == RESULT_EXCEEDED else ""
        sample["finalized_at"] = datetime.now().strftime("%Y-%m-%dT%H:%M")
        sample["status"] = result
        sample["pending"] = False
        sample["abnormal"] = result == RESULT_EXCEEDED

    def serialize_sample(self, row: dict[str, Any], *, latest: bool = False) -> dict[str, Any]:
        item = deepcopy(row)
        point = self._points_by_id().get(int(row.get("point_id", 0)))
        area = self._areas_by_id().get(int(row.get("area_id", 0)))
        item["point_name"] = point.get("name", "未知采样点") if point else "未知采样点"
        item["point_code"] = point.get("code", "") if point else ""
        item["area_name"] = area.get("name", "未知片区") if area else "未知片区"
        standard = self._standards_by_id().get(int(row["standard_id"])) if row.get("standard_id") else None
        item["standard_version"] = standard.get("version") if standard else None
        item["is_latest"] = latest
        if not row.get("finalized"):
            current = self.current_standard(int(row.get("area_id", 0))) if area else None
            if current:
                preview_details, preview_result = self.evaluate(row.get("values", {}), current)
                item["preview_result"] = preview_result
                item["preview_metric_results"] = preview_details
                item["preview_standard_id"] = int(current["id"])
                item["preview_standard_version"] = current.get("version")
        return item

    def _query_samples(
        self,
        *,
        area_id: int | None = None,
        point_id: int | None = None,
        result: str | None = None,
        keyword: str | None = None,
    ) -> list[dict[str, Any]]:
        rows = store.rows(SAMPLE_MODULE)
        if area_id is not None:
            rows = [row for row in rows if int(row.get("area_id", 0)) == area_id]
        if point_id is not None:
            rows = [row for row in rows if int(row.get("point_id", 0)) == point_id]
        if result:
            rows = [row for row in rows if row.get("result") == result]
        if keyword:
            points = self._points_by_id()
            rows = [
                row for row in rows
                if keyword in _clean(row.get("batch_no"))
                or keyword in _clean(points.get(int(row.get("point_id", 0)), {}).get("name"))
                or keyword in _clean(row.get("sampler"))
            ]
        return sorted(rows, key=lambda item: (_clean(item.get("sampled_at")), int(item.get("id", 0))), reverse=True)

    def list_samples(
        self,
        *,
        area_id: int | None = None,
        point_id: int | None = None,
        result: str | None = None,
        keyword: str | None = None,
        page: int = 1,
        size: int = 20,
    ) -> tuple[list[dict[str, Any]], int]:
        rows = self._query_samples(area_id=area_id, point_id=point_id, result=result, keyword=keyword)
        latest_ids = {
            sorted(point_rows, key=lambda item: (_clean(item.get("sampled_at")), int(item.get("id", 0))), reverse=True)[0]["id"]
            for point_rows in (
                [row for row in rows if int(row.get("point_id", 0)) == point_key]
                for point_key in {int(row.get("point_id", 0)) for row in rows}
            )
            if point_rows
        }
        total = len(rows)
        start = max(page - 1, 0) * size
        page_rows = rows[start:start + size]
        return [self.serialize_sample(row, latest=int(row["id"]) in latest_ids) for row in page_rows], total

    def _sample_payload(self, values: dict[str, Any]) -> tuple[int, str, str, dict[str, float], str] | str:
        point_id = int(_number(values.get("point_id")) or 0)
        point = self._points_by_id().get(point_id)
        if point is None:
            return "请选择有效采样点"
        sampled_at = _clean(values.get("sampled_at")).replace(" ", "T")
        if not sampled_at:
            return "采样时间不能为空"
        sampler = _clean(values.get("sampler"))
        if not sampler:
            return "采样人员不能为空"
        raw_values = values.get("values") if isinstance(values.get("values"), dict) else {}
        numeric_values = {key: number for key, number in ((key, _number(value)) for key, value in raw_values.items()) if number is not None}
        reason = _clean(values.get("reason"))
        return point_id, sampled_at, sampler, numeric_values, reason

    def create_sample(self, values: dict[str, Any]) -> tuple[dict[str, Any] | None, str]:
        payload = self._sample_payload(values)
        if isinstance(payload, str):
            return None, payload
        point_id, sampled_at, sampler, numeric_values, reason = payload
        point = self._points_by_id()[point_id]
        rows = store.rows(SAMPLE_MODULE)
        sequence = len(rows) + 1
        sample = {
            "id": _next_id(rows),
            "batch_no": f"WQ-{sampled_at[:10].replace('-', '')}-{sequence:04d}",
            "point_id": point_id,
            "area_id": int(point["area_id"]),
            "sampled_at": sampled_at,
            "sampler": sampler,
            "values": numeric_values,
            "reason": reason,
            "finalized": False,
            "result": RESULT_PENDING,
            "metric_results": [],
            "standard_id": None,
            "finalized_at": None,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "status": RESULT_PENDING,
            "pending": True,
            "abnormal": False,
        }
        rows.append(sample)
        if bool(values.get("finalize")):
            return self.conclude_sample(int(sample["id"]), {"reason": reason})
        return self.serialize_sample(sample), ""

    def update_sample(self, sample_id: int, values: dict[str, Any]) -> tuple[dict[str, Any] | None, str]:
        sample = next((row for row in store.rows(SAMPLE_MODULE) if int(row["id"]) == sample_id), None)
        if sample is None:
            return None, f"采样批次 {sample_id} 不存在"
        if sample.get("finalized"):
            return None, "已出结论的批次按当时口径留档，不能改写"
        payload = self._sample_payload(values)
        if isinstance(payload, str):
            return None, payload
        point_id, sampled_at, sampler, numeric_values, reason = payload
        point = self._points_by_id()[point_id]
        sample.update({
            "point_id": point_id,
            "area_id": int(point["area_id"]),
            "sampled_at": sampled_at,
            "sampler": sampler,
            "values": numeric_values,
            "reason": reason,
            "result": RESULT_PENDING,
            "metric_results": [],
            "standard_id": None,
            "finalized_at": None,
            "status": RESULT_PENDING,
            "pending": True,
            "abnormal": False,
        })
        if bool(values.get("finalize")):
            return self.conclude_sample(sample_id, {"reason": reason})
        return self.serialize_sample(sample), ""

    def conclude_sample(self, sample_id: int, values: dict[str, Any]) -> tuple[dict[str, Any] | None, str]:
        sample = next((row for row in store.rows(SAMPLE_MODULE) if int(row["id"]) == sample_id), None)
        if sample is None:
            return None, f"采样批次 {sample_id} 不存在"
        if sample.get("finalized"):
            return None, "该批次已有结论，历史结论按当时版本留档"
        standard = self.current_standard(int(sample.get("area_id", 0)))
        if standard is None:
            return None, "该片区尚未发布限值口径，不能出结论"
        details, result = self.evaluate(sample.get("values", {}), standard)
        if result == RESULT_PENDING:
            missing = [item["name"] for item in standard.get("indicators", []) if _number(sample.get("values", {}).get(item["code"])) is None]
            return None, f"指标未录完整，缺少：{'、'.join(missing)}"
        reason = _clean(values.get("reason")) or _clean(sample.get("reason"))
        if result == RESULT_EXCEEDED and not reason:
            return None, "超标批次必须写清原因后才能保存结论"
        self._apply_conclusion(sample, standard, result, details, reason)
        return self.serialize_sample(sample), ""

    def stats(
        self,
        *,
        area_id: int | None = None,
        point_id: int | None = None,
        keyword: str | None = None,
    ) -> dict[str, Any]:
        rows = self._query_samples(area_id=area_id, point_id=point_id, keyword=keyword)
        exceeded = [row for row in rows if row.get("result") == RESULT_EXCEEDED]
        latest_points = {
            sorted(point_rows, key=lambda item: (_clean(item.get("sampled_at")), int(item.get("id", 0))), reverse=True)[0]["id"]
            for point_rows in (
                [row for row in rows if int(row.get("point_id", 0)) == point_key]
                for point_key in {int(row.get("point_id", 0)) for row in rows}
            )
            if point_rows
        }
        return {
            "total": len(rows),
            "pending": sum(1 for row in rows if not row.get("finalized")),
            "qualified": sum(1 for row in rows if row.get("result") == RESULT_QUALIFIED),
            "warning": sum(1 for row in rows if row.get("result") == RESULT_WARNING),
            "exceeded": len(exceeded),
            "latest_total": len(latest_points),
            "exceeded_items": [self.serialize_sample(row, latest=int(row["id"]) in latest_points) for row in exceeded],
        }
