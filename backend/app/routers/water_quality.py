"""水质采样检测接口：片区、采样点、限值版本和采样批次台账。"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query

from app.schemas import ActionResult, EntryPayload, PageResult
from app.services.water_quality import WaterQualityService

router = APIRouter(prefix="/api/water-quality", tags=["水质采样检测"])
service = WaterQualityService()


def _area_id(value: int | None) -> int | None:
    return value if value is not None and value > 0 else None


@router.get("/areas")
def list_areas() -> dict[str, Any]:
    items = service.list_areas()
    return {"items": items, "total": len(items)}


@router.post("/areas", response_model=ActionResult)
def create_area(payload: EntryPayload) -> ActionResult:
    entry, message = service.create_area(payload.values)
    if entry is None:
        return ActionResult(ok=False, message=message)
    return ActionResult(ok=True, message="片区已新增", entry=entry)


@router.put("/areas/{area_id}", response_model=ActionResult)
def update_area(area_id: int, payload: EntryPayload) -> ActionResult:
    entry, message = service.update_area(area_id, payload.values)
    if entry is None:
        return ActionResult(ok=False, message=message)
    return ActionResult(ok=True, message="片区已更新", entry=entry)


@router.get("/points")
def list_points(
    area_id: int | None = Query(default=None),
    keyword: str | None = Query(default=None),
) -> dict[str, Any]:
    items = service.list_points(area_id=_area_id(area_id), keyword=keyword)
    return {"items": items, "total": len(items)}


@router.post("/points", response_model=ActionResult)
def create_point(payload: EntryPayload) -> ActionResult:
    entry, message = service.create_point(payload.values)
    if entry is None:
        return ActionResult(ok=False, message=message)
    return ActionResult(ok=True, message="采样点已新增", entry=entry)


@router.put("/points/{point_id}", response_model=ActionResult)
def update_point(point_id: int, payload: EntryPayload) -> ActionResult:
    entry, message = service.update_point(point_id, payload.values)
    if entry is None:
        return ActionResult(ok=False, message=message)
    return ActionResult(ok=True, message="采样点已更新", entry=entry)


@router.get("/standards")
def list_standards(area_id: int | None = Query(default=None)) -> dict[str, Any]:
    items = service.list_standards(area_id=_area_id(area_id))
    return {"items": items, "total": len(items)}


@router.post("/standards", response_model=ActionResult)
def create_standard(payload: EntryPayload) -> ActionResult:
    entry, message, counts = service.create_standard(payload.values)
    if entry is None:
        return ActionResult(ok=False, message=message)
    text = f"限值新版本 {entry.get('version')} 已发布"
    if counts.get("recalculated"):
        text += f"，已按新口径重算 {counts['recalculated']} 批"
    if counts.get("waiting_reason"):
        text += f"，{counts['waiting_reason']} 批超标记录需补充原因后出结论"
    return ActionResult(ok=True, message=text, entry=entry)


@router.get("/samples", response_model=PageResult[dict])
def list_samples(
    area_id: int | None = Query(default=None),
    point_id: int | None = Query(default=None),
    result: str | None = Query(default=None, description="达标、预警、超标、待判定"),
    keyword: str | None = Query(default=None),
    page: int = 1,
    size: int = 20,
) -> PageResult[dict]:
    if size > 200:
        raise HTTPException(status_code=400, detail="每页最多 200 条，请缩小分页范围")
    items, total = service.list_samples(
        area_id=_area_id(area_id),
        point_id=_area_id(point_id),
        result=result,
        keyword=keyword,
        page=page,
        size=size,
    )
    return PageResult(items=items, total=total, page=page, size=size)


@router.get("/samples/stats")
def sample_stats(
    area_id: int | None = Query(default=None),
    point_id: int | None = Query(default=None),
    keyword: str | None = Query(default=None),
) -> dict[str, Any]:
    return service.stats(area_id=_area_id(area_id), point_id=_area_id(point_id), keyword=keyword)


@router.post("/samples", response_model=ActionResult)
def create_sample(payload: EntryPayload) -> ActionResult:
    entry, message = service.create_sample(payload.values)
    if entry is None:
        return ActionResult(ok=False, message=message)
    return ActionResult(ok=True, message="采样批次已保存", entry=entry)


@router.put("/samples/{sample_id}", response_model=ActionResult)
def update_sample(sample_id: int, payload: EntryPayload) -> ActionResult:
    entry, message = service.update_sample(sample_id, payload.values)
    if entry is None:
        return ActionResult(ok=False, message=message)
    return ActionResult(ok=True, message="采样批次已更新", entry=entry)


@router.post("/samples/{sample_id}/conclusion", response_model=ActionResult)
def conclude_sample(sample_id: int, payload: EntryPayload) -> ActionResult:
    entry, message = service.conclude_sample(sample_id, payload.values)
    if entry is None:
        return ActionResult(ok=False, message=message)
    return ActionResult(ok=True, message=f"结论已保存：{entry.get('result')}", entry=entry)
