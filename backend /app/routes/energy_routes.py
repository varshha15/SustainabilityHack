from fastapi import APIRouter, Query, HTTPException
from typing import Optional
from database.models import EnergyData, PaginatedResponse
from services.energy_service import store_energy, get_energy_records, get_energy_summary, get_avg_energy, check_energy_alert
from services.alert_service import create_alert, check_anomaly_alert, ml_detect_anomaly

router = APIRouter(prefix="/energy", tags=["Energy"])


@router.get("/", response_model=PaginatedResponse)
async def get_energy_data(
    building_id: Optional[str] = Query(None, description="Filter by building ID"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
):
    """Get paginated energy readings, newest first."""
    docs, total = await get_energy_records(building_id, page, limit)
    return PaginatedResponse(success=True, total=total, page=page, limit=limit, data=docs)


@router.post("/", status_code=201)
async def store_energy_data(data: EnergyData):
    """
    Store a new energy reading.
    Automatically runs anomaly detection and triggers alerts if needed.
    """
    doc = await store_energy(data.model_dump())

    # Non-fatal background checks
    try:
        avg = await get_avg_energy(data.building_id)
        energy_alert = await check_energy_alert(data.building_id, data.energy_usage, avg)
        if energy_alert:
            await create_alert(**energy_alert)

        ml_result = await ml_detect_anomaly(data.building_id, data.energy_usage)
        if ml_result:
            await check_anomaly_alert(data.building_id, ml_result)
    except Exception as e:
        print(f"[energy_routes] Alert/ML check failed (non-fatal): {e}")

    return {"success": True, "message": "Energy data stored", "id": doc["_id"]}


@router.get("/summary")
async def energy_summary(building_id: str = Query(..., description="Building ID")):
    """Return avg / max / min energy stats for a building."""
    summary = await get_energy_summary(building_id)
    if not summary:
        raise HTTPException(status_code=404, detail="No energy data found for this building")
    return {"success": True, "building_id": building_id, "summary": summary}
