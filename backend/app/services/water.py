"""水质采样检测台账业务规则。

四类对象都在内存仓库里：
- water_district 片区：持有「现行口径」指针（current_standard_id）；
- water_standard 限值口径：按片区逐个版本留痕，调整口径=新增一版并切换指针，不改旧版；
- water_point   采样点：归属片区，采样点维护与指标录入都从片区现行口径取限值；
- water_sample  采样批次：登记后为「待判定」，结论按现行口径实时计算（口径调整即重算）；
                「出具结论」后把当时那版限值与结论快照锁定留档，此后不再被改写。
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from app.store import store
from app.services.water_rules import (
    DEFAULT_LIMITS,
    METRIC_ORDER,
    evaluate_batch,
    limits_equal,
    limits_summary,
    validate_limits,
)

DISTRICT_TABLE = "water_district"
STANDARD_TABLE = "water_standard"
POINT_TABLE = "water_point"
SAMPLE_TABLE = "water_sample"

PENDING = "待判定"
CONCLUDED = "已判定"
STATUSES = [PENDING, CONCLUDED]
RESULT_LABELS = ["达标", "预警", "超标"]
REASON_MIN_LEN = 5
PAGE_SIZE_MAX = 200


def _now_text() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def _next_id(rows: list[dict[str, Any]]) -> int:
    return max((int(row.get("id", 0)) for row in rows), default=0) + 1


def _to_float(value: Any) -> float | None:
    if isinstance(value, bool) or value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


class WaterService:
    # ------------------------------------------------------------------ 片区
    def list_districts(self) -> list[dict[str, Any]]:
        """片区列表，附带现行口径版本与限值摘要（采样点维护页与录入页共用此口径）。"""
        result: list[dict[str, Any]] = []
        for district in store.rows(DISTRICT_TABLE):
            standard = self._current_standard(district)
            result.append(
                {
                    "id": district["id"],
                    "片区编号": district["片区编号"],
                    "片区名称": district["片区名称"],
                    "现行版本": standard["版本"] if standard else None,
                    "现行口径ID": standard["id"] if standard else None,
                    "生效时间": standard["生效时间"] if standard else None,
                    "限值": standard["限值"] if standard else {},
                    "限值摘要": limits_summary(standard["限值"]) if standard else "未设置",
                }
            )
        return result

    def create_district(self, values: dict[str, Any]) -> tuple[dict[str, Any] | None, str]:
        name = str(values.get("片区名称") or "").strip()
        if not name:
            return None, "片区名称为必填项"
        if any(row["片区名称"] == name for row in store.rows(DISTRICT_TABLE)):
            return None, f"片区「{name}」已存在"
        limits = values.get("限值") or {
            metric: dict(bound) for metric, bound in DEFAULT_LIMITS.items()
        }
        message = validate_limits(limits)
        if message:
            return None, message
        districts = store.rows(DISTRICT_TABLE)
        district_id = _next_id(districts)
        district = {
            "id": district_id,
            "片区编号": f"WQ-D{district_id:02d}",
            "片区名称": name,
            "current_standard_id": None,
        }
        districts.append(district)
        standard = self._insert_standard(district, limits, "建片区初始口径")
        district["current_standard_id"] = standard["id"]
        return self._district_view(district), ""

    # ------------------------------------------------------------------ 口径
    def list_standards(self, district_id: int) -> tuple[list[dict[str, Any]] | None, str]:
        """口径版本链：按片区保留每一版，新的在前，标注是否现行。"""
        district = store.find(DISTRICT_TABLE, district_id)
        if district is None:
            return None, f"片区 {district_id} 不存在"
        standards = [
            row for row in store.rows(STANDARD_TABLE) if row["片区ID"] == district_id
        ]
        standards.sort(key=lambda row: int(row["版本"]), reverse=True)
        current_id = district["current_standard_id"]
        return [
            {
                "id": row["id"],
                "版本": row["版本"],
                "版本号": f"V{row['版本']}",
                "生效时间": row["生效时间"],
                "限值": row["限值"],
                "限值摘要": limits_summary(row["限值"]),
                "备注": row.get("备注", ""),
                "是否现行": row["id"] == current_id,
            }
            for row in standards
        ], ""

    def adjust_standard(
        self, district_id: int, limits: dict[str, Any], note: str
    ) -> tuple[dict[str, Any] | None, str]:
        """调整口径：新增一版并切指针。

        旧版原样保留——已出结论的批次按当时那版留档；待判定批次读取时自然按新版实时重算。
        """
        district = store.find(DISTRICT_TABLE, district_id)
        if district is None:
            return None, f"片区 {district_id} 不存在"
        message = validate_limits(limits)
        if message:
            return None, message
        current = self._current_standard(district)
        if current is not None and limits_equal(current["限值"], limits):
            return None, "新口径与现行口径完全一致，无需新增版本"
        standard = self._insert_standard(
            district, limits, note.strip() or "口径调整"
        )
        district["current_standard_id"] = standard["id"]
        pending = [
            row
            for row in store.rows(SAMPLE_TABLE)
            if row["片区ID"] == district_id and row["状态"] == PENDING
        ]
        return {
            "片区": district["片区名称"],
            "新版本": f"V{standard['版本']}",
            "待重算批次数": len(pending),
            "限值摘要": limits_summary(standard["限值"]),
        }, ""

    def _insert_standard(
        self, district: dict[str, Any], limits: dict[str, Any], note: str
    ) -> dict[str, Any]:
        rows = store.rows(STANDARD_TABLE)
        version = (
            max(
                (int(row["版本"]) for row in rows if row["片区ID"] == district["id"]),
                default=0,
            )
            + 1
        )
        standard = {
            "id": _next_id(rows),
            "片区ID": district["id"],
            "版本": version,
            "生效时间": _now_text(),
            "限值": limits,
            "备注": note,
        }
        rows.append(standard)
        return standard

    def _current_standard(self, district: dict[str, Any]) -> dict[str, Any] | None:
        standard_id = district.get("current_standard_id")
        if standard_id is None:
            return None
        return store.find(STANDARD_TABLE, int(standard_id))

    def _district_view(self, district: dict[str, Any]) -> dict[str, Any]:
        standard = self._current_standard(district)
        return {
            "id": district["id"],
            "片区编号": district["片区编号"],
            "片区名称": district["片区名称"],
            "现行版本": standard["版本"] if standard else None,
            "现行口径ID": standard["id"] if standard else None,
            "生效时间": standard["生效时间"] if standard else None,
            "限值": standard["限值"] if standard else {},
            "限值摘要": limits_summary(standard["限值"]) if standard else "未设置",
        }

    # ------------------------------------------------------------------ 采样点
    def list_points(
        self, *, district_id: int | None = None, keyword: str | None = None
    ) -> list[dict[str, Any]]:
        """采样点列表（按片区维护），带上所属片区的现行口径，体现两处共用同一份口径。"""
        points = store.rows(POINT_TABLE)
        if district_id is not None:
            points = [row for row in points if row["片区ID"] == district_id]
        if keyword:
            points = [
                row
                for row in points
                if keyword in str(row["采样点编号"])
                or keyword in str(row["采样点名称"])
                or keyword in str(row.get("位置", ""))
            ]
        result = []
        for point in sorted(points, key=lambda row: row["采样点编号"]):
            district = store.find(DISTRICT_TABLE, point["片区ID"])
            standard = self._current_standard(district) if district else None
            result.append(
                {
                    "id": point["id"],
                    "采样点编号": point["采样点编号"],
                    "采样点名称": point["采样点名称"],
                    "片区ID": point["片区ID"],
                    "片区": district["片区名称"] if district else "片区已删除",
                    "位置": point.get("位置", ""),
                    "启用": point.get("启用", True),
                    "采样点状态": "启用" if point.get("启用", True) else "停用",
                    "现行版本": f"V{standard['版本']}" if standard else "—",
                    "现行口径": limits_summary(standard["限值"]) if standard else "未设置",
                }
            )
        return result

    def create_point(self, values: dict[str, Any]) -> tuple[dict[str, Any] | None, str]:
        code = str(values.get("采样点编号") or "").strip()
        name = str(values.get("采样点名称") or "").strip()
        district_id = _to_float(values.get("片区ID"))
        if not code or not name:
            return None, "采样点编号与采样点名称为必填项"
        if district_id is None:
            return None, "请选择采样点所属片区"
        district = store.find(DISTRICT_TABLE, int(district_id))
        if district is None:
            return None, f"片区 {int(district_id)} 不存在"
        points = store.rows(POINT_TABLE)
        if any(row["采样点编号"] == code for row in points):
            return None, f"采样点编号「{code}」已存在"
        point = {
            "id": _next_id(points),
            "采样点编号": code,
            "采样点名称": name,
            "片区ID": int(district_id),
            "位置": str(values.get("位置") or "").strip(),
            "启用": True,
        }
        points.append(point)
        return self.list_points(keyword=code)[0], ""

    def set_point_status(
        self, point_id: int, active: bool
    ) -> tuple[dict[str, Any] | None, str]:
        point = store.find(POINT_TABLE, point_id)
        if point is None:
            return None, f"采样点 {point_id} 不存在"
        point["启用"] = active
        return self.list_points(keyword=point["采样点编号"])[0], ""

    # ------------------------------------------------------------------ 采样批次
    def query_samples(
        self,
        *,
        keyword: str | None = None,
        district_id: int | None = None,
        point_id: int | None = None,
        result: str | None = None,
        status: str | None = None,
        latest_only: bool = False,
    ) -> list[dict[str, Any]]:
        """列表与统计共用的同一套筛选口径，保证统计卡片条数与列表一致。"""
        rows = store.rows(SAMPLE_TABLE)
        if district_id is not None:
            rows = [row for row in rows if row["片区ID"] == district_id]
        if point_id is not None:
            rows = [row for row in rows if row["采样点ID"] == point_id]
        if status:
            rows = [row for row in rows if row["状态"] == status]
        if keyword:
            rows = [
                row
                for row in rows
                if keyword in str(row["编号"])
                or keyword in str(row["采样点编号"])
                or keyword in str(row["采样点名称"])
            ]
        items = [self._sample_view(row) for row in rows]
        if result:
            items = [item for item in items if item["结论"] == result]
        if latest_only:
            latest_ids = {
                max(group, key=lambda item: (item["采样时间"], item["id"]))["id"]
                for group in self._group_by_point(items).values()
            }
            items = [item for item in items if item["id"] in latest_ids]
        # 同一采样点按时间前后排列；点位之间按采样点编号排
        items.sort(key=lambda item: (item["采样点编号"], item["采样时间"], item["id"]))
        return items

    @staticmethod
    def _group_by_point(items: list[dict[str, Any]]) -> dict[int, list[dict[str, Any]]]:
        groups: dict[int, list[dict[str, Any]]] = {}
        for item in items:
            groups.setdefault(item["采样点ID"], []).append(item)
        return groups

    def _sample_view(self, row: dict[str, Any]) -> dict[str, Any]:
        """把存储行拍平成列表行：已判定走留档快照，待判定按现行口径实时算结论。"""
        locked = row.get("locked")
        readings = row["readings"]
        if row["状态"] == CONCLUDED and locked:
            version_label = f"V{locked['版本']}（已留档）"
            standard_id = locked["标准ID"]
            conclusion = locked["conclusion"]
            metrics = locked["metrics"]
            basis = "出具结论时那一版"
        else:
            standard = self._current_standard(
                store.find(DISTRICT_TABLE, row["片区ID"])
            )
            judged = evaluate_batch(standard["限值"], readings)
            version_label = f"V{standard['版本']}（现行口径实时判定）"
            standard_id = standard["id"]
            conclusion = judged["conclusion"]
            metrics = judged["metrics"]
            basis = "现行口径"
        metric_text = {
            f"{item['指标']}": (
                f"{item['数值']:g}{(' ' + item['单位']) if item['单位'] else ''}"
            )
            for item in metrics
        }
        metric_results = {item["指标"]: item["结果"] for item in metrics}
        return {
            "id": row["id"],
            "编号": row["编号"],
            "采样点ID": row["采样点ID"],
            "采样点编号": row["采样点编号"],
            "采样点名称": row["采样点名称"],
            "片区ID": row["片区ID"],
            "片区": row["片区名称"],
            "采样时间": row["采样时间"],
            "采样人员": row["采样人员"],
            "余氯": metric_text["余氯"],
            "浊度": metric_text["浊度"],
            "pH": metric_text["pH"],
            "指标结果": metric_results,
            "结论": conclusion,
            "判定状态": row["状态"],
            "判定依据版本": version_label,
            "判定依据口径ID": standard_id,
            "口径说明": basis,
            "超标原因": locked.get("超标原因", "") if locked else row.get("超标原因", ""),
            "需补原因": (
                row["状态"] == PENDING
                and conclusion == "超标"
                and not self._reason_ok(row.get("超标原因"))
            ),
            "最近一次": "",
            "readings": readings,
            "pending": row["状态"] == PENDING,
            "abnormal": conclusion == "超标",
        }

    def list_samples(
        self, *, page: int = 1, size: int = 20, **filters: Any
    ) -> tuple[list[dict[str, Any]], int]:
        items = self.query_samples(**filters)
        total = len(items)
        start = max(page - 1, 0) * size
        page_items = items[start:start + size]
        self._mark_latest(page_items, all_items=items)
        return page_items, total

    def _mark_latest(
        self, page_items: list[dict[str, Any]], *, all_items: list[dict[str, Any]]
    ) -> None:
        """在「同一采样点」范围内标出时间最近的一条；分页页内也要标出全量意义上的最近一次。"""
        latest_ids = {
            max(group, key=lambda item: (item["采样时间"], item["id"]))["id"]
            for group in self._group_by_point(all_items).values()
        }
        for item in page_items:
            item["最近一次"] = "最近一次" if item["id"] in latest_ids else ""

    def _collect_readings(
        self, values: dict[str, Any]
    ) -> tuple[dict[str, float] | None, str]:
        readings: dict[str, float] = {}
        for metric in METRIC_ORDER:
            number = _to_float(values.get(metric))
            if number is None or number < 0:
                return None, f"指标「{metric}」必须填写不小于 0 的数值"
            readings[metric] = number
        return readings, ""

    @staticmethod
    def _reason_ok(reason: Any) -> bool:
        return len(str(reason or "").strip()) >= REASON_MIN_LEN

    def create_sample(self, values: dict[str, Any]) -> tuple[dict[str, Any] | None, str]:
        """登记一批采样：采样时间、点位、指标缺一不可；判定超标必须写清原因才能保存。"""
        point_id = _to_float(values.get("采样点ID"))
        sampled_at = str(values.get("采样时间") or "").strip().replace("T", " ")
        personnel = str(values.get("采样人员") or "").strip()
        if point_id is None:
            return None, "请选择采样点"
        point = store.find(POINT_TABLE, int(point_id))
        if point is None:
            return None, f"采样点 {int(point_id)} 不存在"
        if not point.get("启用", True):
            return None, f"采样点「{point['采样点名称']}」已停用，不能登记采样"
        if not sampled_at:
            return None, "采样时间为必填项"
        if not personnel:
            return None, "采样人员为必填项"
        readings, message = self._collect_readings(values)
        if readings is None:
            return None, message
        district = store.find(DISTRICT_TABLE, point["片区ID"])
        standard = self._current_standard(district)
        judged = evaluate_batch(standard["限值"], readings)
        reason = str(values.get("超标原因") or "").strip()
        if judged["conclusion"] == "超标" and not self._reason_ok(reason):
            return None, f"该批采样按现行 V{standard['版本']} 判定为超标，必须写清不少于 {REASON_MIN_LEN} 个字的原因才能保存"
        rows = store.rows(SAMPLE_TABLE)
        sample_id = _next_id(rows)
        row = {
            "id": sample_id,
            "编号": f"WS-{sample_id:04d}",
            "采样点ID": point["id"],
            "采样点编号": point["采样点编号"],
            "采样点名称": point["采样点名称"],
            "片区ID": district["id"],
            "片区名称": district["片区名称"],
            "采样时间": sampled_at,
            "采样人员": personnel,
            "readings": readings,
            "状态": PENDING,
            "超标原因": reason,
        }
        rows.append(row)
        view = self._sample_view(row)
        self._mark_latest([view], all_items=self.query_samples())
        return view, ""

    def update_sample(
        self, sample_id: int, values: dict[str, Any]
    ) -> tuple[dict[str, Any] | None, str]:
        """改录指标：仅待判定批次可改，改完仍按现行口径实时重算结论。"""
        row = store.find(SAMPLE_TABLE, sample_id)
        if row is None:
            return None, f"采样批次 {sample_id} 不存在"
        if row["状态"] != PENDING:
            return None, "已出具结论的批次按当时口径留档，不能改录指标"
        if values.get("采样人员") is not None:
            personnel = str(values.get("采样人员") or "").strip()
            if not personnel:
                return None, "采样人员不能为空"
            row["采样人员"] = personnel
        if values.get("采样时间"):
            row["采样时间"] = str(values["采样时间"]).strip().replace("T", " ")
        readings_input = {metric: values.get(metric) for metric in METRIC_ORDER if metric in values}
        if readings_input:
            merged = dict(row["readings"])
            merged.update({k: v for k, v in readings_input.items() if v not in (None, "")})
            readings, message = self._collect_readings(merged)
            if readings is None:
                return None, message
            row["readings"] = readings
        district = store.find(DISTRICT_TABLE, row["片区ID"])
        standard = self._current_standard(district)
        judged = evaluate_batch(standard["限值"], row["readings"])
        reason = str(values.get("超标原因", row.get("超标原因", "")) or "").strip()
        if judged["conclusion"] == "超标" and not self._reason_ok(reason):
            return None, f"改录后按现行 V{standard['版本']} 判定为超标，必须补写不少于 {REASON_MIN_LEN} 个字的原因才能保存"
        row["超标原因"] = reason
        view = self._sample_view(row)
        self._mark_latest([view], all_items=self.query_samples())
        return view, ""

    def conclude_sample(
        self, sample_id: int, reason: str
    ) -> tuple[dict[str, Any] | None, str]:
        """出具结论：把现行口径版本、各指标判定与批次结论快照锁定；超标须写清原因。"""
        row = store.find(SAMPLE_TABLE, sample_id)
        if row is None:
            return None, f"采样批次 {sample_id} 不存在"
        if row["状态"] != PENDING:
            return None, "该批次已出具结论，结论按当时口径留档，不能重复出具"
        district = store.find(DISTRICT_TABLE, row["片区ID"])
        standard = self._current_standard(district)
        judged = evaluate_batch(standard["限值"], row["readings"])
        reason = (reason or row.get("超标原因", "") or "").strip()
        if judged["conclusion"] == "超标" and not self._reason_ok(reason):
            return None, f"判定为超标，必须写清不少于 {REASON_MIN_LEN} 个字的原因才能出具结论"
        row["状态"] = CONCLUDED
        row["超标原因"] = reason if judged["conclusion"] == "超标" else ""
        row["locked"] = {
            "标准ID": standard["id"],
            "版本": standard["版本"],
            "conclusion": judged["conclusion"],
            "metrics": judged["metrics"],
            "超标原因": row["超标原因"],
            "出具时间": _now_text(),
        }
        view = self._sample_view(row)
        self._mark_latest([view], all_items=self.query_samples())
        return view, ""

    # ------------------------------------------------------------------ 统计
    def stats(self, **filters: Any) -> dict[str, Any]:
        """统计页卡片：直接数同条件列表行，超标批次卡片条数与采样列表天然一致。"""
        items = self.query_samples(**filters)
        counts = {label: sum(1 for item in items if item["结论"] == label) for label in RESULT_LABELS}
        cards = [
            {"label": "采样批次", "value": len(items)},
            {"label": "达标批次", "value": counts["达标"]},
            {"label": "预警批次", "value": counts["预警"]},
            {"label": "超标批次", "value": counts["超标"]},
            {"label": "待判定批次", "value": sum(1 for item in items if item["判定状态"] == PENDING)},
        ]
        abnormal_items = [item for item in items if item["结论"] == "超标"]
        return {
            "cards": cards,
            "超标列表": abnormal_items,
            "超标批次数": counts["超标"],
            "列表总条数": len(items),
        }


water_service = WaterService()
