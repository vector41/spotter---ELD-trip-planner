"""
FMCSA property-carrying HOS planner (70-hour/8-day, no exceptions).
Assumes: 10h off before trip start, home-terminal midnight day boundary.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from enum import Enum
from typing import Any


class DutyStatus(str, Enum):
    OFF_DUTY = "off_duty"
    SLEEPER = "sleeper_berth"
    DRIVING = "driving"
    ON_DUTY = "on_duty_not_driving"


ON_DUTY_STATUSES = {DutyStatus.DRIVING, DutyStatus.ON_DUTY}
WEEKLY_LIMIT = 70.0
WINDOW_HOURS = 14.0
DRIVING_LIMIT = 11.0
BREAK_AFTER_DRIVING = 8.0
BREAK_MINUTES = 30
OFF_DUTY_RESET = 10.0
FUEL_INTERVAL_MILES = 1000
FUEL_STOP_HOURS = 0.5
PICKUP_HOURS = 1.0
DROPOFF_HOURS = 1.0
AVG_SPEED_MPH = 55.0


@dataclass
class LogSegment:
    status: DutyStatus
    start: datetime
    end: datetime
    location: str = ""
    note: str = ""

    @property
    def hours(self) -> float:
        return (self.end - self.start).total_seconds() / 3600

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "start": self.start.isoformat(),
            "end": self.end.isoformat(),
            "start_time": self.start.strftime("%H:%M"),
            "end_time": self.end.strftime("%H:%M"),
            "hours": round(self.hours, 2),
            "location": self.location,
            "note": self.note,
        }


@dataclass
class DailyLog:
    log_date: date
    segments: list[LogSegment] = field(default_factory=list)
    remarks: list[dict[str, str]] = field(default_factory=list)
    total_miles: float = 0.0
    route_from: str = ""
    route_to: str = ""

    def totals(self) -> dict[str, float]:
        totals = {s.value: 0.0 for s in DutyStatus}
        for seg in self.segments:
            totals[seg.status.value] += seg.hours
        return {k: round(v, 2) for k, v in totals.items()}

    def on_duty_today(self) -> float:
        return round(
            sum(s.hours for s in self.segments if s.status in ON_DUTY_STATUSES), 2
        )

    def to_dict(
        self,
        cycle_history: list[float],
        rolling_8_day: float,
    ) -> dict[str, Any]:
        t = self.totals()
        on_duty = self.on_duty_today()
        history = list(cycle_history)
        while len(history) < 6:
            history.insert(0, 0.0)
        last_7 = history[-6:] + [on_duty]
        total_7 = round(sum(last_7), 2)
        total_8 = round(rolling_8_day, 2)
        return {
            "date": self.log_date.isoformat(),
            "segments": [s.to_dict() for s in self.segments],
            "remarks": self.remarks,
            "totals": t,
            "total_hours": round(sum(t.values()), 2),
            "total_miles": round(self.total_miles, 1),
            "route_from": self.route_from,
            "route_to": self.route_to,
            "recap": {
                "on_duty_today": on_duty,
                "total_7_days_including_today": total_7,
                "available_tomorrow_70": round(WEEKLY_LIMIT - total_7, 2),
                "total_8_days_including_today": total_8,
                "rule_set": "70_8",
            },
        }


@dataclass
class TripStop:
    kind: str
    location: str
    lat: float
    lon: float
    miles_from_start: float
    scheduled_at: datetime | None = None
    note: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "location": self.location,
            "lat": self.lat,
            "lon": self.lon,
            "miles_from_start": round(self.miles_from_start, 1),
            "scheduled_at": self.scheduled_at.isoformat() if self.scheduled_at else None,
            "note": self.note,
        }


@dataclass
class DriverState:
    window_start: datetime | None = None
    driving_in_window: float = 0.0
    on_duty_in_window: float = 0.0
    driving_since_break: float = 0.0
    break_taken_in_window: bool = False
    off_duty_streak: float = OFF_DUTY_RESET
    cycle_hours: list[float] = field(default_factory=list)
    cycle_base: float = 0.0
    miles_since_fuel: float = 0.0
    current_time: datetime = field(default_factory=datetime.now)
    location_label: str = ""

    def weekly_on_duty(self, today_so_far: float = 0.0) -> float:
        return self.cycle_base + sum(self.cycle_hours) + today_so_far

    def can_drive(self, today_on_duty: float = 0.0) -> bool:
        if self.window_start is None:
            return self.off_duty_streak >= OFF_DUTY_RESET
        elapsed = (self.current_time - self.window_start).total_seconds() / 3600
        if elapsed >= WINDOW_HOURS:
            return False
        if self.driving_in_window >= DRIVING_LIMIT:
            return False
        if self.driving_since_break >= BREAK_AFTER_DRIVING and not self.break_taken_in_window:
            return False
        if self.weekly_on_duty(today_on_duty) >= WEEKLY_LIMIT:
            return False
        return True

    def driving_remaining(self) -> float:
        rem = DRIVING_LIMIT - self.driving_in_window
        if self.driving_since_break >= BREAK_AFTER_DRIVING and not self.break_taken_in_window:
            return 0.0
        until_break = BREAK_AFTER_DRIVING - self.driving_since_break
        if not self.break_taken_in_window:
            rem = min(rem, until_break)
        if self.window_start:
            elapsed = (self.current_time - self.window_start).total_seconds() / 3600
            rem = min(rem, max(0, WINDOW_HOURS - elapsed - self.on_duty_in_window))
        weekly_left = WEEKLY_LIMIT - self.weekly_on_duty()
        return max(0, min(rem, weekly_left / AVG_SPEED_MPH * AVG_SPEED_MPH))


class HOSPlanner:
    def __init__(self, cycle_used_hours: float = 0.0, start_time: datetime | None = None):
        self.cycle_used_start = max(0.0, cycle_used_hours)
        self.rolling_8_day = self.cycle_used_start
        self.state = DriverState(
            off_duty_streak=OFF_DUTY_RESET,
            current_time=start_time or datetime.now().replace(hour=6, minute=0, second=0, microsecond=0),
            cycle_hours=[],
            cycle_base=self.cycle_used_start,
        )

    def _add_segment(
        self,
        log: DailyLog,
        status: DutyStatus,
        hours: float,
        location: str,
        note: str = "",
    ) -> None:
        if hours <= 0:
            return
        end = self.state.current_time + timedelta(hours=hours)
        seg = LogSegment(
            status=status,
            start=self.state.current_time,
            end=end,
            location=location,
            note=note,
        )
        log.segments.append(seg)
        if note or location:
            log.remarks.append(
                {
                    "time": self.state.current_time.strftime("%H:%M"),
                    "location": location,
                    "note": note or status.value.replace("_", " ").title(),
                }
            )
        self.state.current_time = end
        self.state.location_label = location
        if status == DutyStatus.DRIVING:
            self.state.driving_in_window += hours
            self.state.driving_since_break += hours
            self.state.on_duty_in_window += hours
            self.state.miles_since_fuel += hours * AVG_SPEED_MPH
        elif status in ON_DUTY_STATUSES:
            self.state.on_duty_in_window += hours
        elif status in (DutyStatus.OFF_DUTY, DutyStatus.SLEEPER):
            self.state.off_duty_streak += hours

    def _ensure_day_log(self, logs: dict[date, DailyLog], d: date) -> DailyLog:
        if d not in logs:
            logs[d] = DailyLog(log_date=d)
        return logs[d]

    def _start_window_if_needed(self, log: DailyLog, location: str) -> None:
        if self.state.window_start is None and self.state.off_duty_streak >= OFF_DUTY_RESET:
            self.state.window_start = self.state.current_time
            self._add_segment(log, DutyStatus.ON_DUTY, 0.25, location, "Pre-trip / dispatch")

    def _take_break(self, log: DailyLog, location: str) -> None:
        self._add_segment(
            log,
            DutyStatus.ON_DUTY,
            BREAK_MINUTES / 60,
            location,
            "30-minute rest break from driving",
        )
        self.state.break_taken_in_window = True
        self.state.driving_since_break = 0.0

    def _end_shift_rest(
        self,
        logs: dict[date, DailyLog],
        log: DailyLog,
        location: str,
        use_sleeper: bool = True,
    ) -> None:
        if self.state.window_start is None:
            return
        on_duty_today = sum(
            s.hours for s in log.segments if s.status in ON_DUTY_STATUSES
        )
        if on_duty_today > 0:
            self.state.cycle_hours.append(on_duty_today)
        if len(self.state.cycle_hours) > 8:
            self.state.cycle_hours = self.state.cycle_hours[-8:]

        rest_hours = OFF_DUTY_RESET
        status = DutyStatus.SLEEPER if use_sleeper else DutyStatus.OFF_DUTY
        remaining = rest_hours
        while remaining > 0.01:
            d = self.state.current_time.date()
            day_log = self._ensure_day_log(logs, d)
            midnight = (self.state.current_time + timedelta(days=1)).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            until_midnight = (midnight - self.state.current_time).total_seconds() / 3600
            chunk = min(remaining, until_midnight if until_midnight > 0 else remaining)
            if chunk < 0.01:
                chunk = min(remaining, 8.0)
            self._add_segment(
                day_log,
                status,
                chunk,
                location,
                "10-hour off-duty / sleeper rest",
            )
            remaining -= chunk

        self.state.window_start = None
        self.state.driving_in_window = 0.0
        self.state.on_duty_in_window = 0.0
        self.state.driving_since_break = 0.0
        self.state.break_taken_in_window = False
        self.state.off_duty_streak = OFF_DUTY_RESET
        self.state.miles_since_fuel = 0.0

    def _drive_miles(
        self,
        logs: dict[date, DailyLog],
        miles: float,
        location: str,
        label: str,
    ) -> float:
        driven = 0.0
        while driven < miles:
            d = self.state.current_time.date()
            log = self._ensure_day_log(logs, d)
            self._start_window_if_needed(log, location)

            today_od = sum(s.hours for s in log.segments if s.status in ON_DUTY_STATUSES)
            if not self.state.can_drive(today_od):
                self._end_shift_rest(logs, log, location)
                d = self.state.current_time.date()
                log = self._ensure_day_log(logs, d)
                self._start_window_if_needed(log, location)

            if (
                self.state.driving_since_break >= BREAK_AFTER_DRIVING
                and not self.state.break_taken_in_window
            ):
                self._take_break(log, location)

            if self.state.miles_since_fuel >= FUEL_INTERVAL_MILES:
                self._add_segment(
                    log,
                    DutyStatus.ON_DUTY,
                    FUEL_STOP_HOURS,
                    location,
                    "Fueling stop",
                )
                self.state.miles_since_fuel = 0.0

            remaining_miles = miles - driven
            drive_hours = remaining_miles / AVG_SPEED_MPH
            chunk = min(
                drive_hours,
                DRIVING_LIMIT - self.state.driving_in_window,
                (
                    BREAK_AFTER_DRIVING - self.state.driving_since_break
                    if not self.state.break_taken_in_window
                    else DRIVING_LIMIT
                ),
            )
            if self.state.window_start:
                elapsed = (
                    self.state.current_time - self.state.window_start
                ).total_seconds() / 3600
                window_left = WINDOW_HOURS - elapsed - self.state.on_duty_in_window
                chunk = min(chunk, max(0, window_left))

            if chunk <= 0.01:
                self._end_shift_rest(logs, log, location)
                continue

            self._add_segment(log, DutyStatus.DRIVING, chunk, location, label)
            driven += chunk * AVG_SPEED_MPH
            log.total_miles += chunk * AVG_SPEED_MPH

        return driven

    def plan_trip(
        self,
        legs: list[dict[str, Any]],
        total_miles: float,
    ) -> tuple[list[DailyLog], list[TripStop]]:
        """
        legs: [{distance_miles, from_label, to_label, lat, lon, kind}, ...]
        """
        logs: dict[date, DailyLog] = {}
        stops: list[TripStop] = []
        miles_accounted = 0.0

        for leg in legs:
            kind = leg.get("kind", "drive")
            dist = float(leg.get("distance_miles", 0))
            from_l = leg.get("from_label", "")
            to_l = leg.get("to_label", "")
            lat = float(leg.get("lat", 0))
            lon = float(leg.get("lon", 0))

            if kind == "pickup":
                d = self.state.current_time.date()
                log = self._ensure_day_log(logs, d)
                self._start_window_if_needed(log, to_l)
                self._add_segment(log, DutyStatus.ON_DUTY, PICKUP_HOURS, to_l, "Pickup")
                stops.append(
                    TripStop("pickup", to_l, lat, lon, miles_accounted, self.state.current_time)
                )
            elif kind == "dropoff":
                d = self.state.current_time.date()
                log = self._ensure_day_log(logs, d)
                self._start_window_if_needed(log, to_l)
                self._add_segment(log, DutyStatus.ON_DUTY, DROPOFF_HOURS, to_l, "Dropoff")
                stops.append(
                    TripStop("dropoff", to_l, lat, lon, miles_accounted, self.state.current_time)
                )
            else:
                self._drive_miles(logs, dist, to_l, f"Driving toward {to_l}")
                miles_accounted += dist
                stops.append(
                    TripStop("waypoint", to_l, lat, lon, miles_accounted, self.state.current_time)
                )

        ordered = sorted(logs.keys())
        result_logs: list[DailyLog] = []
        history: list[float] = []
        for i, d in enumerate(ordered):
            log = logs[d]
            if log.segments:
                log.route_from = log.segments[0].location or ""
                log.route_to = log.segments[-1].location or ""
            result_logs.append(log)
            history.append(log.on_duty_today())

        return result_logs, stops

    def _normalize_log_day(self, log: DailyLog) -> None:
        """Pad with off-duty so status totals equal 24 hours per FMCSA grid."""
        day_start = datetime.combine(log.log_date, datetime.min.time())
        day_end = day_start + timedelta(days=1)

        if log.segments:
            first = log.segments[0]
            if first.start > day_start:
                log.segments.insert(
                    0,
                    LogSegment(
                        DutyStatus.OFF_DUTY,
                        day_start,
                        first.start,
                        first.location,
                        "Off duty",
                    ),
                )

        if not log.segments:
            log.segments.append(
                LogSegment(
                    DutyStatus.OFF_DUTY,
                    day_start,
                    day_end,
                    note="Off duty",
                )
            )
            return

        last = log.segments[-1]
        if last.end < day_end - timedelta(seconds=30):
            gap = (day_end - last.end).total_seconds() / 3600
            if gap > 0.01:
                if last.status == DutyStatus.OFF_DUTY:
                    log.segments[-1] = LogSegment(
                        last.status,
                        last.start,
                        day_end,
                        last.location,
                        last.note,
                    )
                else:
                    log.segments.append(
                        LogSegment(
                            DutyStatus.OFF_DUTY,
                            last.end,
                            day_end,
                            last.location,
                            "Off duty",
                        )
                    )
        elif last.status != DutyStatus.OFF_DUTY and last.end >= day_end - timedelta(seconds=30):
            note = (last.note or "").lower()
            if "dropoff" in note:
                fixed_end = last.start + timedelta(hours=DROPOFF_HOURS)
            elif "pickup" in note:
                fixed_end = last.start + timedelta(hours=PICKUP_HOURS)
            elif len(log.segments) >= 2:
                fixed_end = log.segments[-2].end
            else:
                fixed_end = last.start + timedelta(hours=1)

            if fixed_end < day_end:
                loc = last.location
                log.segments[-1] = LogSegment(
                    last.status, last.start, fixed_end, loc, last.note
                )
                log.segments.append(
                    LogSegment(
                        DutyStatus.OFF_DUTY,
                        fixed_end,
                        day_end,
                        loc,
                        "Off duty",
                    )
                )

    def build_log_payloads(self, logs: list[DailyLog]) -> list[dict]:
        history: list[float] = []
        payloads = []
        rolling = self.cycle_used_start
        for log in logs:
            self._normalize_log_day(log)
            on_duty = log.on_duty_today()
            rolling = round(rolling + on_duty, 2)
            payloads.append(log.to_dict(history, rolling))
            history.append(on_duty)
        return payloads
