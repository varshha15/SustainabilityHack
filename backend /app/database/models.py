from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


# ──────────────────────────────────────────────────
# Energy
# ──────────────────────────────────────────────────

class EnergyData(BaseModel):
    building_id: str
    timestamp: datetime
    energy_usage: float          # kWh
    water_usage: float           # litres
    waste_level: float           # % 0-100
    temperature: Optional[float] = None  # °C

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


# ──────────────────────────────────────────────────
# Waste
# ──────────────────────────────────────────────────

class WasteData(BaseModel):
    building_id: str
    timestamp: datetime
    waste_level: float           # % 0-100
    waste_type: Optional[str] = "general"
    collection_due: Optional[bool] = False


# ──────────────────────────────────────────────────
# Carbon
# ──────────────────────────────────────────────────

class CarbonData(BaseModel):
    building_id: str
    timestamp: datetime
    electricity_used: float      # kWh
    carbon_emission: float       # kg CO2
    emission_factor: float = 0.233


# ──────────────────────────────────────────────────
# Predictions
# ──────────────────────────────────────────────────

class PredictionResult(BaseModel):
    building_id: str
    timestamp: datetime
    prediction_type: str         # "energy" | "waste" | "anomaly" | "score"
    predicted_value: Optional[float] = None
    anomaly_detected: Optional[bool] = None
    confidence: Optional[float] = None
    sustainability_score: Optional[float] = None
    recommendations: Optional[List[str]] = []
    source: str = "ml_service"


# ──────────────────────────────────────────────────
# Alerts
# ──────────────────────────────────────────────────

class AlertSeverity:
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Alert(BaseModel):
    building_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    alert_type: str              # "energy_spike" | "waste_full" | "score_drop" | "anomaly"
    severity: str = AlertSeverity.MEDIUM
    message: str
    resolved: bool = False
    resolved_at: Optional[datetime] = None


class AlertCreate(BaseModel):
    building_id: str
    alert_type: str
    severity: str = AlertSeverity.MEDIUM
    message: str


# ──────────────────────────────────────────────────
# Buildings
# ──────────────────────────────────────────────────

class Building(BaseModel):
    building_id: str
    name: str
    location: Optional[str] = None
    floors: Optional[int] = None
    area_sqm: Optional[float] = None
    active: bool = True


# ──────────────────────────────────────────────────
# Generic responses
# ──────────────────────────────────────────────────

class APIResponse(BaseModel):
    success: bool
    message: str
    data: Optional[dict] = None


class PaginatedResponse(BaseModel):
    success: bool
    total: int
    page: int
    limit: int
    data: list
