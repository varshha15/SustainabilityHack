from datetime import datetime
from bson import ObjectId


def serialize_doc(doc: dict) -> dict:
    """Convert MongoDB _id ObjectId to string."""
    if doc and "_id" in doc:
        doc["_id"] = str(doc["_id"])
    return doc


def serialize_list(docs: list) -> list:
    """Serialize a list of MongoDB documents."""
    return [serialize_doc(doc) for doc in docs]


def parse_object_id(id_str: str) -> ObjectId:
    """Parse string to ObjectId, raises ValueError on failure."""
    try:
        return ObjectId(id_str)
    except Exception:
        raise ValueError(f"Invalid ObjectId: {id_str}")


def utcnow() -> datetime:
    return datetime.utcnow()


def calculate_carbon(electricity_kwh: float, emission_factor: float = 0.233) -> float:
    """carbon_emission (kg CO2) = electricity_used (kWh) × emission_factor"""
    return round(electricity_kwh * emission_factor, 4)


def build_pagination_query(page: int, limit: int) -> tuple[int, int]:
    """Return (skip, limit) for MongoDB pagination."""
    skip = (page - 1) * limit
    return skip, limit
