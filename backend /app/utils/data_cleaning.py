from datetime import datetime
from typing import Optional


def clamp(value: float, min_val: float, max_val: float) -> float:
    """Clamp a float value between min and max."""
    return max(min_val, min(max_val, value))


def clean_energy_reading(energy_usage: float) -> float:
    """
    Validate and clean an energy reading.
    - Must be non-negative
    - Cap at 10,000 kWh (sanity limit for a single building reading)
    """
    if energy_usage < 0:
        raise ValueError(f"Energy usage cannot be negative: {energy_usage}")
    return clamp(energy_usage, 0, 10_000)


def clean_waste_level(waste_level: float) -> float:
    """Waste level must be 0–100%."""
    if waste_level < 0 or waste_level > 100:
        raise ValueError(f"Waste level must be between 0 and 100: {waste_level}")
    return round(waste_level, 2)


def clean_water_usage(water_usage: float) -> float:
    """Water usage must be non-negative (litres)."""
    if water_usage < 0:
        raise ValueError(f"Water usage cannot be negative: {water_usage}")
    return round(water_usage, 2)


def clean_temperature(temp: Optional[float]) -> Optional[float]:
    """Temperature sanity check: -50°C to 60°C."""
    if temp is None:
        return None
    if temp < -50 or temp > 60:
        raise ValueError(f"Temperature out of realistic range: {temp}")
    return round(temp, 1)


def normalize_building_id(building_id: str) -> str:
    """Uppercase and strip building ID for consistency."""
    return building_id.strip().upper()


def validate_timestamp(timestamp: datetime) -> datetime:
    """Reject timestamps far in the future (more than 1 day ahead)."""
    from datetime import timedelta
    now = datetime.utcnow()
    if timestamp > now + timedelta(days=1):
        raise ValueError(f"Timestamp is too far in the future: {timestamp}")
    return timestamp


def clean_energy_record(data: dict) -> dict:
    """Apply all cleaning rules to an energy record dict."""
    data["building_id"] = normalize_building_id(data.get("building_id", ""))
    data["energy_usage"] = clean_energy_reading(data.get("energy_usage", 0))
    data["water_usage"] = clean_water_usage(data.get("water_usage", 0))
    data["waste_level"] = clean_waste_level(data.get("waste_level", 0))
    data["temperature"] = clean_temperature(data.get("temperature"))
    if "timestamp" in data:
        data["timestamp"] = validate_timestamp(data["timestamp"])
    return data
