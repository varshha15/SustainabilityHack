from database.db import get_collection
from utils.helpers import serialize_list, build_pagination_query, calculate_carbon


async def store_carbon(data: dict) -> dict:
    """Calculate and store carbon emission from electricity used."""
    data["carbon_emission"] = calculate_carbon(
        data.get("electricity_used", 0),
        data.get("emission_factor", 0.233),
    )
    collection = get_collection("carbon_data")
    result = await collection.insert_one(data)
    data["_id"] = str(result.inserted_id)
    return data


async def get_carbon_records(building_id: str | None, page: int, limit: int) -> tuple[list, int]:
    """Return paginated carbon records."""
    collection = get_collection("carbon_data")
    query = {"building_id": building_id} if building_id else {}
    skip, limit = build_pagination_query(page, limit)
    total = await collection.count_documents(query)
    cursor = collection.find(query).sort("timestamp", -1).skip(skip).limit(limit)
    docs = await cursor.to_list(length=limit)
    return serialize_list(docs), total


async def get_carbon_summary(building_id: str) -> dict:
    """Total carbon emissions and stats for a building."""
    collection = get_collection("carbon_data")
    cursor = collection.find(
        {"building_id": building_id}, {"carbon_emission": 1, "electricity_used": 1}
    )
    docs = await cursor.to_list(length=10_000)
    if not docs:
        return {"total_emission_kg": 0, "total_electricity_kwh": 0, "readings_count": 0}
    total_emission = sum(d.get("carbon_emission", 0) for d in docs)
    total_electricity = sum(d.get("electricity_used", 0) for d in docs)
    return {
        "total_emission_kg": round(total_emission, 2),
        "total_electricity_kwh": round(total_electricity, 2),
        "readings_count": len(docs),
        "avg_emission_per_reading": round(total_emission / len(docs), 4),
    }
