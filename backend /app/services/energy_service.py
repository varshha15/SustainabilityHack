from datetime import datetime
from database.db import get_collection
from database.models import AlertSeverity
from utils.data_cleaning import clean_energy_record
from utils.helpers import serialize_doc, serialize_list, build_pagination_query


# ── Alert thresholds ──────────────────────────────
ENERGY_SPIKE_MULTIPLIER = 1.5   # 50% above average = spike


async def store_energy(data: dict) -> dict:
    """Clean, validate, and store an energy reading."""
    data = clean_energy_record(data)
    collection = get_collection("energy_data")
    result = await collection.insert_one(data)
    data["_id"] = str(result.inserted_id)
    return data


async def get_energy_records(building_id: str | None, page: int, limit: int) -> tuple[list, int]:
    """Return paginated energy records and total count."""
    collection = get_collection("energy_data")
    query = {"building_id": building_id} if building_id else {}
    skip, limit = build_pagination_query(page, limit)
    total = await collection.count_documents(query)
    cursor = collection.find(query).sort("timestamp", -1).skip(skip).limit(limit)
    docs = await cursor.to_list(length=limit)
    return serialize_list(docs), total


async def get_energy_summary(building_id: str) -> dict:
    """Compute avg / max / min energy for a building."""
    collection = get_collection("energy_data")
    cursor = collection.find({"building_id": building_id}).sort("timestamp", -1).limit(48)
    docs = await cursor.to_list(length=48)
    if not docs:
        return {}
    usages = [d["energy_usage"] for d in docs]
    return {
        "avg_energy_kwh": round(sum(usages) / len(usages), 2),
        "max_energy_kwh": round(max(usages), 2),
        "min_energy_kwh": round(min(usages), 2),
        "readings_count": len(docs),
        "latest_timestamp": docs[0]["timestamp"],
    }


async def get_avg_energy(building_id: str, limit: int = 24) -> float:
    """Compute rolling average energy for alert comparison."""
    collection = get_collection("energy_data")
    cursor = collection.find(
        {"building_id": building_id}, {"energy_usage": 1}
    ).sort("timestamp", -1).limit(limit)
    readings = await cursor.to_list(length=limit)
    if not readings:
        return 0.0
    return sum(r["energy_usage"] for r in readings) / len(readings)


async def check_energy_alert(building_id: str, energy_value: float, avg_energy: float) -> dict | None:
    """Return alert dict if energy spike detected, else None."""
    if avg_energy > 0 and energy_value >= avg_energy * ENERGY_SPIKE_MULTIPLIER:
        pct = ((energy_value / avg_energy) - 1) * 100
        return {
            "building_id": building_id,
            "alert_type": "energy_spike",
            "severity": AlertSeverity.HIGH,
            "message": (
                f"Energy spike detected: {energy_value:.1f} kWh "
                f"(avg: {avg_energy:.1f} kWh, {pct:.0f}% above normal)."
            ),
        }
    return None
