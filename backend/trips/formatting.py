"""Paper log formatting — city/state labels and remark text."""
from __future__ import annotations

import re
from typing import Any

_STATE_TO_ABBR = {
    "alabama": "AL", "alaska": "AK", "arizona": "AZ", "arkansas": "AR",
    "california": "CA", "colorado": "CO", "connecticut": "CT", "delaware": "DE",
    "florida": "FL", "georgia": "GA", "maryland": "MD", "massachusetts": "MA",
    "michigan": "MI", "minnesota": "MN", "mississippi": "MS", "missouri": "MO",
    "new jersey": "NJ", "new york": "NY", "north carolina": "NC", "ohio": "OH",
    "pennsylvania": "PA", "tennessee": "TN", "texas": "TX", "virginia": "VA",
    "washington": "WA", "west virginia": "WV", "district of columbia": "DC",
}

_SKIP_REMARK_NOTES = frozenset(
    {
        "off duty",
        "continued 10-hour off-duty / sleeper rest",
        "10-hour off-duty rest",
        "10-hour off-duty / sleeper rest",
    }
)

_SPAN_THRESHOLD_MIN = 45


def short_place(label: str, fallback: str = "") -> str:
    if not label:
        return fallback
    parts = [p.strip() for p in label.split(",") if p.strip()]
    if not parts:
        return fallback
    city = parts[0]
    for part in parts[1:]:
        if re.fullmatch(r"[A-Za-z]{2}", part):
            return f"{city}, {part.upper()}"
        abbr = _STATE_TO_ABBR.get(part.lower())
        if abbr:
            return f"{city}, {abbr}"
    if len(parts) >= 2:
        return f"{city}, {parts[1][:2].upper()}"
    return city[:36]


def _time_to_minutes(time_str: str) -> int:
    parts = time_str.split(":")
    h = int(parts[0]) if parts else 0
    m = int(parts[1]) if len(parts) > 1 else 0
    return h * 60 + m


def _segment_notable(seg: dict[str, Any]) -> bool:
    note_l = (seg.get("note") or "").strip().lower()
    status = seg.get("status", "")
    if status == "driving":
        return False
    if status == "off_duty":
        return "lunch" in note_l
    return status in ("on_duty_not_driving", "sleeper_berth")


def _end_minutes(start_m: int, end_time: str) -> int:
    end_m = _time_to_minutes(end_time)
    if end_m <= start_m:
        return 1440 if start_m > 0 else start_m + 15
    return end_m


def build_remark_brackets(segments: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merged: list[dict[str, Any]] = []
    for seg in segments:
        if not _segment_notable(seg):
            continue
        note_l = (seg.get("note") or "").strip().lower()
        if note_l in _SKIP_REMARK_NOTES:
            continue
        loc = short_place(seg.get("location", ""))
        if not loc:
            continue
        start = seg.get("start_time", "00:00")
        end = seg.get("end_time", start)
        start_m = _time_to_minutes(start)
        end_m = _end_minutes(start_m, end)
        if merged and merged[-1]["location"] == loc:
            merged[-1]["end_time"] = end
            merged[-1]["end_minutes"] = end_m
            continue
        merged.append(
            {
                "location": loc,
                "start_time": start,
                "end_time": end,
                "start_minutes": start_m,
                "end_minutes": end_m,
            }
        )

    brackets: list[dict[str, Any]] = []
    for item in merged:
        span = item["end_minutes"] - item["start_minutes"]
        note_l = ""
        for seg in segments:
            if seg.get("start_time") == item["start_time"]:
                note_l = (seg.get("note") or "").lower()
                break
        is_long_stop = any(k in note_l for k in ("pickup", "dropoff", "lunch", "fuel"))
        status = next(
            (s.get("status") for s in segments if s.get("start_time") == item["start_time"]),
            "",
        )
        use_span = span > _SPAN_THRESHOLD_MIN or is_long_stop or status == "sleeper_berth"
        brackets.append({**item, "kind": "span" if use_span else "ticks"})
    return brackets


def apply_route_labels(
    log: dict,
    current_q: str,
    pickup_q: str,
    dropoff_q: str,
) -> None:
    after_pickup = False
    for seg in log.get("segments", []):
        note = (seg.get("note") or "").lower()
        if "pickup" in note:
            after_pickup = True
            seg["location"] = pickup_q
        elif "dropoff" in note:
            seg["location"] = dropoff_q
        elif not after_pickup:
            seg["location"] = current_q
        else:
            seg["location"] = dropoff_q


def enrich_daily_log(
    log: dict,
    *,
    carrier_name: str,
    office_address: str,
    driver_name: str,
    vehicle_numbers: str,
    shipping_no: str,
    current_q: str = "",
    pickup_q: str = "",
    dropoff_q: str = "",
) -> dict:
    if current_q and pickup_q and dropoff_q:
        apply_route_labels(log, current_q, pickup_q, dropoff_q)
        log["route_from"] = short_place(current_q, current_q)
        log["route_to"] = short_place(dropoff_q, dropoff_q)
    log["remark_brackets"] = build_remark_brackets(log.get("segments", []))
    log["form"] = {
        "carrier_name": carrier_name,
        "office_address": office_address,
        "driver_name": driver_name,
        "vehicle_numbers": vehicle_numbers,
        "shipping_no": shipping_no,
        "co_driver": "",
    }
    return log
