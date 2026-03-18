from fastapi import APIRouter, Query, HTTPException
from typing import Optional
from database.db import get_collection
from database.models import CarbonData, Building, PaginatedResponse
from services.carbon_service import store_carbon, get_carbon_records, get_carbon_summary
from services.alert_service import create_alert, check_score_alert, ml_sustainability_score
from utils.helpers import serialize_doc, serialize_list

router = APIRouter(tags=["Sustainability"])


# ── Carbon ───────────────────────────────────────

@router.get("/carbon", response_model=PaginatedResponse)
async def get_carbon_data(
    building_id: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
):
    """Get paginated carbon emission records."""
    docs, total = await get_carbon_records(building_id, page, limit)
    return PaginatedResponse(success=True, total=total, page=page, limit=limit, data=docs)


@router.post("/carbon", status_code=201)
async def store_carbon_data(data: CarbonData):
    """Calculate and store carbon emission from electricity used."""
    doc = await store_carbon(data.model_dump())
    return {
        "success": True,
        "building_id": data.building_id,
        "carbon_emission_kg": doc["carbon_emission"],
        "id": doc["_id"],
    }


@router.get("/carbon/summary/{building_id}")
async def carbon_summary(building_id: str):
    """Total carbon emissions for a building."""
    summary = await get_carbon_summary(building_id)
    return {"success": True, "building_id": building_id, "summary": summary}


# ── Buildings ─────────────────────────────────────

@router.get("/buildings")
async def list_buildings():
    """List all active buildings."""
    collection = get_collection("buildings")
    cursor = collection.find({"active": True})
    docs = await cursor.to_list(length=100)
    return {"success": True, "data": serialize_list(docs)}


@router.post("/buildings", status_code=201)
async def register_building(data: Building):
    """Register a new building."""
    collection = get_collection("buildings")
    existing = await collection.find_one({"building_id": data.building_id})
    if existing:
        raise HTTPException(status_code=409, detail="Building ID already registered")
    doc = data.model_dump()
    result = await collection.insert_one(doc)
    doc["_id"] = str(result.inserted_id)
    return {"success": True, "message": "Building registered", "building": doc}


@router.get("/buildings/{building_id}")
async def get_building(building_id: str):
    """Get a single building's info."""
    collection = get_collection("buildings")
    doc = await collection.find_one({"building_id": building_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Building not found")
    return {"success": True, "data": serialize_doc(doc)}


# ── Score ─────────────────────────────────────────

@router.get("/score/{building_id}")
async def sustainability_score(building_id: str):
    """
    Fetch sustainability score from ML service.
    Stores it and triggers a critical alert if score < 40.
    """
    result = await ml_sustainability_score(building_id)
    if not result:
        raise HTTPException(status_code=503, detail="ML service unavailable")

    score = result.get("score", 0)

    # Store the score prediction
    from datetime import datetime
    from database.models import PredictionResult
    pred_col = get_collection("predictions")
    prediction = PredictionResult(
        building_id=building_id,
        timestamp=datetime.utcnow(),
        prediction_type="score",
        sustainability_score=score,
        recommendations=result.get("recommendations", []),
    )
    await pred_col.insert_one(prediction.model_dump())

    try:
        await check_score_alert(building_id, score)
    except Exception as e:
        print(f"[sustainability_routes] Score alert failed (non-fatal): {e}")

    return {"success": True, "building_id": building_id, "score": score, "details": result}


# ── Dashboard (aggregated) ────────────────────────

@router.get("/dashboard/{building_id}")
async def building_dashboard(building_id: str):
    """
    Single endpoint for frontend dashboard.
    Returns: latest energy, waste, carbon, score, alert count.
    """
    energy_col = get_collection("energy_data")
    waste_col = get_collection("waste_data")
    carbon_col = get_collection("carbon_data")
    alert_col = get_collection("alerts")
    pred_col = get_collection("predictions")

    latest_energy = await energy_col.find_one({"building_id": building_id}, sort=[("timestamp", -1)])
    latest_waste = await waste_col.find_one({"building_id": building_id}, sort=[("timestamp", -1)])
    latest_carbon = await carbon_col.find_one({"building_id": building_id}, sort=[("timestamp", -1)])
    latest_score = await pred_col.find_one(
        {"building_id": building_id, "prediction_type": "score"}, sort=[("timestamp", -1)]
    )
    unresolved_alerts = await alert_col.count_documents({"building_id": building_id, "resolved": False})

    return {
        "success": True,
        "building_id": building_id,
        "dashboard": {
            "latest_energy": serialize_doc(latest_energy),
            "latest_waste": serialize_doc(latest_waste),
            "latest_carbon": serialize_doc(latest_carbon),
            "sustainability_score": latest_score.get("sustainability_score") if latest_score else None,
            "recommendations": latest_score.get("recommendations", []) if latest_score else [],
            "unresolved_alerts": unresolved_alerts,
        },
    }
