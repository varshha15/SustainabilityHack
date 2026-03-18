from fastapi import APIRouter, Query, HTTPException
from datetime import datetime
from typing import Optional
from database.db import get_collection
from database.models import PredictionResult, PaginatedResponse
from services.alert_service import ml_predict_energy, ml_predict_waste, ml_sustainability_score
from utils.helpers import serialize_list

router = APIRouter(prefix="/predictions", tags=["Predictions"])


@router.get("/", response_model=PaginatedResponse)
async def get_predictions(
    building_id: Optional[str] = Query(None),
    prediction_type: Optional[str] = Query(None, description="energy | waste | anomaly | score"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
):
    """Get stored ML prediction records."""
    collection = get_collection("predictions")
    query = {}
    if building_id:
        query["building_id"] = building_id
    if prediction_type:
        query["prediction_type"] = prediction_type
    skip = (page - 1) * limit
    total = await collection.count_documents(query)
    cursor = collection.find(query).sort("timestamp", -1).skip(skip).limit(limit)
    docs = await cursor.to_list(length=limit)
    return PaginatedResponse(success=True, total=total, page=page, limit=limit, data=serialize_list(docs))


@router.get("/energy/{building_id}")
async def predict_energy(
    building_id: str,
    hours: int = Query(24, ge=1, le=168, description="Prediction horizon in hours"),
):
    """Fetch energy prediction from ML service and store it."""
    result = await ml_predict_energy(building_id, hours)
    if not result:
        raise HTTPException(status_code=503, detail="ML service unavailable for energy prediction")

    collection = get_collection("predictions")
    prediction = PredictionResult(
        building_id=building_id,
        timestamp=datetime.utcnow(),
        prediction_type="energy",
        predicted_value=result.get("predicted_value"),
        confidence=result.get("confidence"),
        recommendations=result.get("recommendations", []),
    )
    await collection.insert_one(prediction.model_dump())
    return {"success": True, "building_id": building_id, "prediction": result}


@router.get("/waste/{building_id}")
async def predict_waste(building_id: str):
    """Fetch waste prediction from ML service and store it."""
    result = await ml_predict_waste(building_id)
    if not result:
        raise HTTPException(status_code=503, detail="ML service unavailable for waste prediction")

    collection = get_collection("predictions")
    prediction = PredictionResult(
        building_id=building_id,
        timestamp=datetime.utcnow(),
        prediction_type="waste",
        predicted_value=result.get("hours_until_full"),
        confidence=result.get("confidence"),
    )
    await collection.insert_one(prediction.model_dump())
    return {"success": True, "building_id": building_id, "prediction": result}


@router.get("/recommendations/{building_id}")
async def get_recommendations(building_id: str):
    """Get latest AI recommendations for a building from stored predictions."""
    collection = get_collection("predictions")
    doc = await collection.find_one(
        {"building_id": building_id, "recommendations": {"$exists": True, "$ne": []}},
        sort=[("timestamp", -1)]
    )
    if not doc:
        return {"success": True, "building_id": building_id, "recommendations": []}
    return {
        "success": True,
        "building_id": building_id,
        "recommendations": doc.get("recommendations", []),
        "generated_at": doc.get("timestamp"),
    }
