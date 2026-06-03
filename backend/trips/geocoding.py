"""Free geocoding and routing via OpenStreetMap ecosystem."""
from __future__ import annotations

import os
import time
from typing import Any

import requests

NOMINATIM_URL = os.getenv(
    "NOMINATIM_URL", "https://nominatim.openstreetmap.org/search"
)
OSRM_URL = os.getenv(
    "OSRM_URL", "https://router.project-osrm.org/route/v1/driving"
)
USER_AGENT = os.getenv(
    "GEOCODING_USER_AGENT", "SpotterELD/1.0 (FMCSA HOS trip planner)"
)


def geocode(place: str) -> dict[str, Any]:
    resp = requests.get(
        NOMINATIM_URL,
        params={"q": place, "format": "json", "limit": 1, "countrycodes": "us"},
        headers={"User-Agent": USER_AGENT},
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    if not data:
        raise ValueError(f"Could not geocode location: {place}")
    item = data[0]
    return {
        "label": item.get("display_name", place),
        "lat": float(item["lat"]),
        "lon": float(item["lon"]),
        "query": place,
    }


def route_distance_miles(coords: list[tuple[float, float]]) -> dict[str, Any]:
    """coords: list of (lon, lat)"""
    if len(coords) < 2:
        raise ValueError("Need at least two coordinates")
    coord_str = ";".join(f"{lon},{lat}" for lon, lat in coords)
    url = f"{OSRM_URL}/{coord_str}"
    resp = requests.get(
        url,
        params={"overview": "full", "geometries": "geojson", "steps": "true"},
        headers={"User-Agent": USER_AGENT},
        timeout=60,
    )
    resp.raise_for_status()
    data = resp.json()
    if data.get("code") != "Ok" or not data.get("routes"):
        raise ValueError("Routing failed: " + str(data.get("message", "unknown")))
    route = data["routes"][0]
    miles = route["distance"] / 1609.34
    hours = route["duration"] / 3600
    return {
        "distance_miles": miles,
        "duration_hours": hours,
        "geometry": route["geometry"],
        "legs": route.get("legs", []),
    }


def build_trip_legs(
    current: dict,
    pickup: dict,
    dropoff: dict,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    time.sleep(1)
    coords = [
        (current["lon"], current["lat"]),
        (pickup["lon"], pickup["lat"]),
        (dropoff["lon"], dropoff["lat"]),
    ]
    routing = route_distance_miles(coords)
    legs_meta = routing.get("legs", [])
    distances = []
    if len(legs_meta) >= 2:
        for leg in legs_meta:
            distances.append(leg["distance"] / 1609.34)
    else:
        total = routing["distance_miles"]
        distances = [total * 0.4, total * 0.5, total * 0.1]
        if len(distances) < 2:
            distances = [total * 0.6, total * 0.4]

    d1 = distances[0] if distances else routing["distance_miles"] * 0.45
    d2 = distances[1] if len(distances) > 1 else routing["distance_miles"] - d1

    legs = [
        {
            "kind": "drive",
            "distance_miles": d1,
            "from_label": current["label"],
            "to_label": pickup["label"],
            "lat": pickup["lat"],
            "lon": pickup["lon"],
        },
        {
            "kind": "pickup",
            "from_label": pickup["label"],
            "to_label": pickup["label"],
            "lat": pickup["lat"],
            "lon": pickup["lon"],
        },
        {
            "kind": "drive",
            "distance_miles": d2,
            "from_label": pickup["label"],
            "to_label": dropoff["label"],
            "lat": dropoff["lat"],
            "lon": dropoff["lon"],
        },
        {
            "kind": "dropoff",
            "from_label": dropoff["label"],
            "to_label": dropoff["label"],
            "lat": dropoff["lat"],
            "lon": dropoff["lon"],
        },
    ]
    return legs, routing
