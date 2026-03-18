from database.db import get_collection
from database.models import AlertSeverity
from utils.helpers import serialize_list, build_pagination_query
from utils.data_cleaning import clean_waste_level, normalize_building_id


WASTE_ALERT_THRESHOLD = 90.0    # % — trigger alert above this
WASTE_CRITICAL_THRESHOLD = 95.0


async def store_waste(data: dict) -> dict:
    """Validate and store a waste reading."""
    data["building_id"] = normalize_building_id(data.get("building_id", ""))
    data["waste_level"] = clean_waste_level(data.get("waste_level", 0))
    collection = get_collection("waste_data")
    result = await collection.insert_one(data)
    data["_id"] = str(result.inserted_id)
    return data


async def get_waste_records(building_id: str | None, page: int, limit: int) -> tuple[list, int]:
    """Return paginated waste records."""
    collection = get_collection("waste_data")
    query = {"building_id": building_id} if building_id else {}
    skip, limit = build_pagination_query(page, limit)
    total = await collection.count_documents(query)
    cursor = collection.find(query).sort("timestamp", -1).skip(skip).limit(limit)
    docs = await cursor.to_list(length=limit)
    return serialize_list(docs), total


async def check_waste_alert(building_id: str, waste_level: float) -> dict | None:
    """Return alert dict if waste bin is nearly/completely full."""
    if waste_level >= WASTE_ALERT_THRESHOLD:
        severity = (
            AlertSeverity.CRITICAL if waste_level >= WASTE_CRITICAL_THRESHOLD
            else AlertSeverity.HIGH
        )
        return {
            "building_id": building_id,
            "alert_type": "waste_full",
            "severity": severity,
            "message": f"Waste bin at {waste_level:.1f}% capacity — collection required.",
        }
    return None


async def get_waste_summary(building_id: str) -> dict:
    """Latest waste level and average over last 24 readings."""
    collection = get_collection("waste_data")
    cursor = collection.find({"building_id": building_id}).sort("timestamp", -1).limit(24)
    docs = await cursor.to_list(length=24)
    if not docs:
        return {}
    levels = [d["waste_level"] for d in docs]
    return {
        "current_waste_level": levels[0],
        "avg_waste_level": round(sum(levels) / len(levels), 2),
        "max_waste_level": round(max(levels), 2),
        "collection_due": levels[0] >= WASTE_ALERT_THRESHOLD,
        "readings_count": len(docs),
    }
