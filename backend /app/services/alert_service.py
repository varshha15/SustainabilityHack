from datetime import datetime
import httpx
from database.db import get_collection, settings
from database.models import Alert, AlertSeverity
from utils.helpers import serialize_doc, serialize_list, build_pagination_query

SCORE_DROP_THRESHOLD = 40.0
ML_TIMEOUT = 10.0


# ── Core alert store ──────────────────────────────

async def create_alert(building_id: str, alert_type: str, severity: str, message: str) -> dict:
    """Persist an alert to MongoDB and return it."""
    collection = get_collection("alerts")
    alert = Alert(
        building_id=building_id,
        alert_type=alert_type,
        severity=severity,
        message=message,
        timestamp=datetime.utcnow(),
    )
    doc = alert.model_dump()
    result = await collection.insert_one(doc)
    doc["_id"] = str(result.inserted_id)
    print(f"[Alert] {severity.upper()} | {building_id} | {message}")
    return doc


async def resolve_alert(alert_id: str) -> bool:
    """Mark an alert resolved. Returns True if found."""
    from utils.helpers import parse_object_id
    collection = get_collection("alerts")
    oid = parse_object_id(alert_id)
    result = await collection.update_one(
        {"_id": oid},
        {"$set": {"resolved": True, "resolved_at": datetime.utcnow()}}
    )
    return result.matched_count > 0


async def get_alerts(building_id, resolved, severity, page, limit) -> tuple[list, int]:
    """Paginated alert fetch with optional filters."""
    collection = get_collection("alerts")
    query = {}
    if building_id:
        query["building_id"] = building_id
    if resolved is not None:
        query["resolved"] = resolved
    if severity:
        query["severity"] = severity
    skip, limit = build_pagination_query(page, limit)
    total = await collection.count_documents(query)
    cursor = collection.find(query).sort("timestamp", -1).skip(skip).limit(limit)
    docs = await cursor.to_list(length=limit)
    return serialize_list(docs), total


async def get_unresolved_count(building_id: str | None) -> int:
    collection = get_collection("alerts")
    query = {"resolved": False}
    if building_id:
        query["building_id"] = building_id
    return await collection.count_documents(query)


# ── ML-triggered alert checks ─────────────────────

async def check_anomaly_alert(building_id: str, ml_result: dict):
    if ml_result and ml_result.get("anomaly_detected"):
        confidence = ml_result.get("confidence", 0)
        await create_alert(
            building_id=building_id,
            alert_type="anomaly",
            severity=AlertSeverity.MEDIUM,
            message=f"ML anomaly detected in building {building_id}. Confidence: {confidence:.0%}.",
        )


async def check_score_alert(building_id: str, score: float):
    if score < SCORE_DROP_THRESHOLD:
        await create_alert(
            building_id=building_id,
            alert_type="score_drop",
            severity=AlertSeverity.CRITICAL,
            message=f"Sustainability score critically low: {score:.0f}/100 for building {building_id}.",
        )


# ── ML service client ─────────────────────────────

async def call_ml(endpoint: str, params: dict = None, body: dict = None) -> dict | None:
    """Generic ML service caller with timeout + error handling."""
    url = f"{settings.ML_SERVICE_URL}{endpoint}"
    try:
        async with httpx.AsyncClient(timeout=ML_TIMEOUT) as client:
            if body:
                r = await client.post(url, json=body)
            else:
                r = await client.get(url, params=params or {})
            r.raise_for_status()
            return r.json()
    except httpx.HTTPError as e:
        print(f"[ML] {endpoint} error: {e}")
        return None


async def ml_detect_anomaly(building_id: str, energy_value: float) -> dict | None:
    return await call_ml("/detect-anomaly", body={"building_id": building_id, "energy_value": energy_value})


async def ml_predict_energy(building_id: str, hours: int = 24) -> dict | None:
    return await call_ml("/predict-energy", params={"building_id": building_id, "hours": hours})


async def ml_predict_waste(building_id: str) -> dict | None:
    return await call_ml("/predict-waste", params={"building_id": building_id})


async def ml_sustainability_score(building_id: str) -> dict | None:
    return await call_ml("/sustainability-score", params={"building_id": building_id})
