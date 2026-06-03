from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .formatting import enrich_daily_log, short_place
from .geocoding import build_trip_legs, geocode
from .hos_engine import HOSPlanner


@api_view(["GET"])
def health(request):
    return Response({"status": "ok", "service": "spotter-hos-api"})


@api_view(["POST"])
def plan_trip(request):
    data = request.data
    current = (data.get("current_location") or "").strip()
    pickup = (data.get("pickup_location") or "").strip()
    dropoff = (data.get("dropoff_location") or "").strip()
    cycle_used = float(data.get("cycle_used_hours") or 0)

    if not all([current, pickup, dropoff]):
        return Response(
            {"error": "current_location, pickup_location, and dropoff_location are required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        current_geo = geocode(current)
        pickup_geo = geocode(pickup)
        dropoff_geo = geocode(dropoff)
        legs, routing = build_trip_legs(current_geo, pickup_geo, dropoff_geo)

        planner = HOSPlanner(cycle_used_hours=cycle_used)
        daily_logs, trip_stops = planner.plan_trip(legs, routing["distance_miles"])
        log_payloads = planner.build_log_payloads(daily_logs)
        office = short_place(pickup_geo["label"], pickup)
        for i, log in enumerate(log_payloads):
            enrich_daily_log(
                log,
                carrier_name="Spotter Transport",
                office_address=office,
                driver_name="Driver Name",
                vehicle_numbers=f"123, {20544 + i}",
                shipping_no=f"{log['date'].replace('-', '')}01",
                current_q=current,
                pickup_q=pickup,
                dropoff_q=dropoff,
            )

        instructions = _build_instructions(
            current_geo,
            pickup_geo,
            dropoff_geo,
            routing,
            trip_stops,
            log_payloads,
        )

        return Response(
            {
                "summary": {
                    "total_miles": round(routing["distance_miles"], 1),
                    "estimated_drive_hours": round(routing["duration_hours"], 2),
                    "log_days": len(log_payloads),
                    "cycle_used_at_start": cycle_used,
                    "rule_set": "70_hour_8_day",
                },
                "locations": {
                    "current": current_geo,
                    "pickup": pickup_geo,
                    "dropoff": dropoff_geo,
                },
                "route": {
                    "geometry": routing["geometry"],
                    "distance_miles": round(routing["distance_miles"], 1),
                },
                "stops": [s.to_dict() for s in trip_stops],
                "instructions": instructions,
                "daily_logs": log_payloads,
            }
        )
    except ValueError as exc:
        return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as exc:
        return Response(
            {"error": f"Trip planning failed: {exc}"},
            status=status.HTTP_502_BAD_GATEWAY,
        )


def _build_instructions(current, pickup, dropoff, routing, stops, logs):
    steps = [
        {
            "order": 1,
            "title": "Depart current location",
            "detail": f"Start from {current['query']} ({current['label'][:60]}…)",
        },
        {
            "order": 2,
            "title": "Proceed to pickup",
            "detail": f"Drive to {pickup['query']} — first leg of {routing['distance_miles']:.0f} mi total.",
        },
        {
            "order": 3,
            "title": "Pickup (1 hour on duty)",
            "detail": f"Load at {pickup['query']}. Log as on-duty not driving.",
        },
        {
            "order": 4,
            "title": "Proceed to delivery",
            "detail": f"Drive to {dropoff['query']}.",
        },
        {
            "order": 5,
            "title": "Dropoff (1 hour on duty)",
            "detail": f"Unload at {dropoff['query']}.",
        },
    ]
    for log in logs:
        recap = log.get("recap", {})
        if recap.get("total_8_days_including_today", 0) >= 65:
            steps.append(
                {
                    "order": len(steps) + 1,
                    "title": f"HOS recap — {log['date']}",
                    "detail": (
                        f"8-day on-duty total: {recap['total_8_days_including_today']} hr "
                        f"({recap['available_tomorrow_70']} hr available tomorrow)."
                    ),
                }
            )
    steps.append(
        {
            "order": len(steps) + 1,
            "title": "Compliance notes",
            "detail": (
                "70-hour/8-day property carrier rules applied. "
                "30-min break after 8 hr driving; 10 hr off-duty between shifts; "
                "fuel stop planned every 1,000 mi. No adverse driving or short-haul exceptions."
            ),
        }
    )
    return steps
