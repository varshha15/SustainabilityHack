from fastapi import APIRouter, Query, HTTPException
from typing import Optional
from database.models import WasteData, PaginatedResponse
from services.waste_service import store_waste, get_waste_records, get_waste_summary, check_waste_alert
from services.alert_service import create_alert, ml_predict_waste

router = APIRouter(prefix="/waste", tags=["Waste"])


@router.get("/", response_model=PaginatedResponse)
async def get_waste_data(
    building_id: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
):
    """Get paginated waste readings."""
    docs, total = await get_waste_records(building_id, page, limit)
    return PaginatedResponse(success=True, total=total, page=page, limit=limit, data=docs)


@router.post("/", status_code=201)
async def store_waste_data(data: WasteData):
    """Store waste reading. Triggers alert if bin is ≥ 90% full."""
    doc = await store_waste(data.model_dump())
    try:
        alert = await check_waste_alert(data.building_id, data.waste_level)
        if alert:
            await create_alert(**alert)
    except Exception as e:
        print(f"[waste_routes] Alert check failed (non-fatal): {e}")
    return {"success": True, "message": "Waste data stored", "id": doc["_id"]}


@router.get("/summary")
async def waste_summary(building_id: str = Query(...)):
    """Current waste level + average for a building."""
    summary = await get_waste_summary(building_id)
    if not summary:
        raise HTTPException(status_code=404, detail="No waste data found for this building")
    return {"success": True, "building_id": building_id, "summary": summary}


@router.get("/predict/{building_id}")
async def waste_prediction(building_id: str):
    """Get ML prediction for waste bin fill time."""
    result = await ml_predict_waste(building_id)
    if not result:
        raise HTTPException(status_code=503, detail="ML service unavailable")
    return {"success": True, "building_id": building_id, "prediction": result}
