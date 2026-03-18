from fastapi import APIRouter, Query, HTTPException
from typing import Optional
from database.models import AlertCreate, PaginatedResponse
from services.alert_service import create_alert, resolve_alert, get_alerts, get_unresolved_count

router = APIRouter(prefix="/alerts", tags=["Alerts"])


@router.get("/", response_model=PaginatedResponse)
async def get_all_alerts(
    building_id: Optional[str] = Query(None),
    resolved: Optional[bool] = Query(None, description="Filter by resolved status"),
    severity: Optional[str] = Query(None, description="low | medium | high | critical"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
):
    """Get paginated alerts with optional filters."""
    docs, total = await get_alerts(building_id, resolved, severity, page, limit)
    return PaginatedResponse(success=True, total=total, page=page, limit=limit, data=docs)


@router.post("/", status_code=201)
async def create_manual_alert(data: AlertCreate):
    """Manually create an alert (e.g. from sensor trigger or data pipeline)."""
    alert = await create_alert(
        building_id=data.building_id,
        alert_type=data.alert_type,
        severity=data.severity,
        message=data.message,
    )
    return {"success": True, "message": "Alert created", "alert": alert}


@router.patch("/{alert_id}/resolve")
async def resolve_alert_by_id(alert_id: str):
    """Mark an alert as resolved."""
    found = await resolve_alert(alert_id)
    if not found:
        raise HTTPException(status_code=404, detail="Alert not found")
    return {"success": True, "message": f"Alert {alert_id} marked as resolved"}


@router.get("/unresolved/count")
async def unresolved_alerts_count(
    building_id: Optional[str] = Query(None, description="Filter by building"),
):
    """Quick count of unresolved alerts — used for dashboard badge."""
    count = await get_unresolved_count(building_id)
    return {"success": True, "unresolved_count": count}
