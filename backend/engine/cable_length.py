"""Kabellaengen-Schaetzung aus Geodaten (Luftlinie + Trassenfaktor)."""
from __future__ import annotations

import math
from typing import Literal, TypedDict


class CableLengthEstimate(TypedDict):
    length_km: float
    source: Literal["geo_calculated", "user_input", "estimated"]
    airline_km: float
    routing_factor: float
    confidence: Literal["high", "medium", "low"]
    note: str


ROUTING_FACTORS = {
    "urban": 1.2,
    "suburban": 1.35,
    "rural": 1.5,
}


def haversine_distance(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Luftlinienabstand in km."""
    r_earth_km = 6371.0
    d_lat = math.radians(lat2 - lat1)
    d_lng = math.radians(lng2 - lng1)
    a = (
        math.sin(d_lat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(d_lng / 2) ** 2
    )
    return r_earth_km * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def estimate_cable_length_from_location(
    project_lat: float,
    project_lng: float,
    nearest_grid_node_lat: float,
    nearest_grid_node_lng: float,
    settlement_type: Literal["urban", "suburban", "rural"] = "suburban",
) -> CableLengthEstimate:
    airline_km = haversine_distance(project_lat, project_lng, nearest_grid_node_lat, nearest_grid_node_lng)
    routing_factor = ROUTING_FACTORS.get(settlement_type, ROUTING_FACTORS["suburban"])
    length_km = airline_km * routing_factor

    if airline_km < 0.1:
        confidence: Literal["high", "medium", "low"] = "high"
    elif airline_km < 1.0:
        confidence = "medium"
    else:
        confidence = "low"

    return {
        "length_km": round(length_km, 3),
        "source": "geo_calculated",
        "airline_km": round(airline_km, 3),
        "routing_factor": routing_factor,
        "confidence": confidence,
        "note": (
            f"Luftlinie {airline_km:.2f} km × Trassenfaktor {routing_factor} ({settlement_type}). "
            "Genaue Laenge durch Netzbetreiber zu bestaetigen."
        ),
    }
