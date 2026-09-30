"""水质采样检测台账接口：片区与限值版本维护、采样点维护、采样登记/判定/统计。

路由层只做参数收发，所有业务判断（超标原因拦截、口径版本切换、待判定重算）都在 services/water。
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.schemas import ActionResult, EntryPayload, PageResult
from app.services.water import PAGE_SIZE_MAX, STATUSES, water_service

router = APIRouter(prefix="/api/water", tags=["水质采样"])


class StandardAdjustPayload(BaseModel):
    """调整片区口径：提交一整版指标限值。"""

    values: dict[str, Any] = Field(default_factory=dict)
    remark: str | None = None


def _int_or_none(value: int | None) -> int | None:
    return value


# --------------------------------------------------------------------- 片区口径
@router.get("/districts")
def list_districts() -> dict[str, Any]:
    """片区清单，附各片区现行口径版本与限值摘要。"""
    return {"items": water_service.list_districts()}


@router.post("/districts", response_model=ActionResult)
def create_district(payload: EntryPayload) -> ActionResult:
    """新建片区，可随片区带上第一版限值；不填则用平台初始口径。"""
    district, message = water_service.create_district(payload.values)
    if district is None:
        return ActionResult(ok=False, message=message)
    return ActionResult(ok=True, message=f"片区「{district['片区名称']}」已建立，口径 V{district['现行版本']} 生效", entry=district)


@router.get("/districts/{district_id}/standards")
def list_standards(district_id: int) -> dict[str, Any]:
    """按片区读取口径版本链，每版留档并标注是否现行。"""
    items, message = water_service.list_standards(district_id)
    if items is None:
        raise HTTPException(status_code=404, detail=message)
    return {"items": items}


@router.post("/districts/{district_id}/standards", response_model=ActionResult)
def adjust_standard(district_id: int, payload: StandardAdjustPayload) -> ActionResult:
    """调整口径：新增一版并切到新版；待判定批次随后按新版重算，已出结论批次不动。"""
    result, message = water_service.adjust_standard(
        district_id, payload.values.get("限值") or payload.values, payload.remark or ""
    )
    if result is None:
        return ActionResult(ok=False, message=message)
    return ActionResult(
        ok=True,
        message=f"口径已更新为 {result['新版本']}，{result['待重算批次数']} 条待判定批次按新版重算（已出结论批次保持留档）",
        entry=result,
    )


# --------------------------------------------------------------------- 采样点
@router.get("/points")
def list_points(
    district_id: int | None = Query(default=None, description="按片区筛选采样点"),
    keyword: str | None = Query(default=None, description="按采样点编号/名称/位置检索"),
) -> dict[str, Any]:
    """采样点列表：带上所属片区现行口径，和指标录入读的是同一份。"""
    return {"items": water_service.list_points(district_id=district_id, keyword=keyword)}


@router.post("/points", response_model=ActionResult)
def create_point(payload: EntryPayload) -> ActionResult:
    """在片区下登记采样点。"""
    point, message = water_service.create_point(payload.values)
    if point is None:
        return ActionResult(ok=False, message=message)
    return ActionResult(ok=True, message=f"采样点「{point['采样点编号']}」已登记", entry=point)


@router.post("/points/{point_id}/status", response_model=ActionResult)
def set_point_status(point_id: int, payload: EntryPayload) -> ActionResult:
    """启用/停用采样点；停用后不允许登记新批次。"""
    active = bool(payload.values.get("启用", True))
    point, message = water_service.set_point_status(point_id, active)
    if point is None:
        return ActionResult(ok=False, message=message)
    return ActionResult(ok=True, message=f"采样点已{point['采样点状态']}", entry=point)


# --------------------------------------------------------------------- 采样批次
@router.get("/samples", response_model=PageResult[dict])
def list_samples(
    keyword: str | None = Query(default=None, description="按批次编号或采样点检索"),
    district_id: int | None = Query(default=None, description="片区筛选"),
    point_id: int | None = Query(default=None, description="采样点筛选"),
    result: str | None = Query(default=None, description="达标、预警、超标"),
    status: str | None = Query(default=None, description="待判定、已判定"),
    latest_only: bool = Query(default=False, description="只看每个采样点最近一次"),
    page: int = 1,
    size: int = 20,
) -> PageResult[dict]:
    """采样台账：同一点位按采样时间先后排列，并标记最近一次。"""
    if size > PAGE_SIZE_MAX:
        raise HTTPException(status_code=400, detail=f"每页最多 {PAGE_SIZE_MAX} 条，请缩小分页范围")
    if result and result not in ("达标", "预警", "超标"):
        raise HTTPException(status_code=400, detail="结论只支持 达标、预警、超标")
    if status and status not in STATUSES:
        raise HTTPException(status_code=400, detail="判定状态只支持 待判定、已判定")
    items, total = water_service.list_samples(
        keyword=keyword,
        district_id=_int_or_none(district_id),
        point_id=_int_or_none(point_id),
        result=result,
        status=status,
        latest_only=latest_only,
        page=page,
        size=size,
    )
    return PageResult(items=items, total=total, page=page, size=size)


@router.post("/samples", response_model=ActionResult)
def create_sample(payload: EntryPayload) -> ActionResult:
    """登记一批采样（采样时间、余氯、浊度、pH 等）；超标必须写清原因才能保存。"""
    sample, message = water_service.create_sample(payload.values)
    if sample is None:
        return ActionResult(ok=False, message=message)
    return ActionResult(ok=True, message=f"批次 {sample['编号']} 已登记，当前判定：{sample['结论']}", entry=sample)


@router.patch("/samples/{sample_id}", response_model=ActionResult)
def update_sample(sample_id: int, payload: EntryPayload) -> ActionResult:
    """改录待判定批次的指标/人员/时间；改完按现行口径重算，超标须补写原因。"""
    sample, message = water_service.update_sample(sample_id, payload.values)
    if sample is None:
        return ActionResult(ok=False, message=message)
    return ActionResult(ok=True, message=f"批次 {sample['编号']} 已改录，当前判定：{sample['结论']}", entry=sample)


@router.post("/samples/{sample_id}/conclude", response_model=ActionResult)
def conclude_sample(sample_id: int, payload: EntryPayload) -> ActionResult:
    """出具结论：按现行口径锁定快照留档；超标必须写清原因。"""
    reason = str(payload.values.get("超标原因") or "").strip()
    sample, message = water_service.conclude_sample(sample_id, reason)
    if sample is None:
        return ActionResult(ok=False, message=message)
    return ActionResult(ok=True, message=f"批次 {sample['编号']} 结论已出具并按 {sample['判定依据版本'].split('（')[0]} 留档", entry=sample)


# --------------------------------------------------------------------- 统计
@router.get("/stats")
def stats(
    keyword: str | None = None,
    district_id: int | None = None,
    point_id: int | None = None,
    result: str | None = None,
    status: str | None = None,
    latest_only: bool = False,
) -> dict[str, Any]:
    """统计页：超标批次卡片由与采样列表同一查询口径直接计数，条数保持一致。"""
    return water_service.stats(
        keyword=keyword,
        district_id=district_id,
        point_id=point_id,
        result=result,
        status=status,
        latest_only=latest_only,
    )
