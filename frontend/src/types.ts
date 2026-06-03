export interface GeoLocation {
  label: string;
  lat: number;
  lon: number;
  query: string;
}

export interface LogSegment {
  status: string;
  start: string;
  end: string;
  start_time: string;
  end_time: string;
  hours: number;
  location: string;
  note: string;
}

export interface RemarkBracket {
  location: string;
  start_time: string;
  end_time: string;
  start_minutes: number;
  end_minutes: number;
  /** span = horizontal bracket; ticks = paired vertical marks for brief stops */
  kind?: "span" | "ticks";
}

export interface DailyLogForm {
  carrier_name: string;
  office_address: string;
  driver_name: string;
  vehicle_numbers: string;
  shipping_no: string;
  co_driver: string;
}

export interface DailyLog {
  date: string;
  segments: LogSegment[];
  remarks: { time: string; location: string; note: string }[];
  remark_brackets?: RemarkBracket[];
  totals: Record<string, number>;
  total_hours: number;
  total_miles: number;
  route_from: string;
  route_to: string;
  form?: DailyLogForm;
  recap: {
    on_duty_today: number;
    total_7_days_including_today: number;
    available_tomorrow_70: number;
    total_8_days_including_today: number;
    rule_set: string;
  };
}

export interface TripPlanResponse {
  summary: {
    total_miles: number;
    estimated_drive_hours: number;
    log_days: number;
    cycle_used_at_start: number;
    rule_set: string;
  };
  locations: {
    current: GeoLocation;
    pickup: GeoLocation;
    dropoff: GeoLocation;
  };
  route: {
    geometry: GeoJSON.LineString;
    distance_miles: number;
  };
  stops: {
    kind: string;
    location: string;
    lat: number;
    lon: number;
    miles_from_start: number;
    scheduled_at: string | null;
    note: string;
  }[];
  instructions: { order: number; title: string; detail: string }[];
  daily_logs: DailyLog[];
}
