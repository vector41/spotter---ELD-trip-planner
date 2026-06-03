import type { DailyLog, LogSegment } from "../types";

const INK = "#000000";
const GRID = "#000000";
const SUBGRID = "#888888";

const ROWS = [
  { key: "off_duty", label: "1. Off Duty" },
  { key: "sleeper_berth", label: "2. Sleeper Berth" },
  { key: "driving", label: "3. Driving" },
  { key: "on_duty_not_driving", label: "4. On Duty (not driving)" },
] as const;

const LABEL_W = 132;
const GRID_LEFT = LABEL_W;
const GRID_WIDTH = 620;
const ROW_H = 32;
const TIME_BAR_H = 18;
const GRID_TOP = TIME_BAR_H;
const GRID_BOTTOM = GRID_TOP + ROWS.length * ROW_H;
const TOTAL_X = GRID_LEFT + GRID_WIDTH + 4;
const TOTAL_W = 58;
const SVG_W = TOTAL_X + TOTAL_W;
const SVG_H = GRID_BOTTOM + 2;

function minFromTime(time: string): number {
  const [h, m] = time.split(":").map(Number);
  return (h || 0) * 60 + (m || 0);
}

function segStartMin(seg: LogSegment): number {
  if (seg.start_time) return minFromTime(seg.start_time);
  return 0;
}

function segEndMin(seg: LogSegment): number {
  const start = segStartMin(seg);
  if (seg.end_time) {
    const end = minFromTime(seg.end_time);
    if (end <= start) return 1440;
    return end;
  }
  return start + 15;
}

function xMin(minutes: number): number {
  return GRID_LEFT + (minutes / 1440) * GRID_WIDTH;
}

function rowY(idx: number): number {
  return GRID_TOP + idx * ROW_H + ROW_H / 2;
}

function hourLabel(i: number): string {
  if (i === 0) return "Mid-night";
  if (i === 12) return "Noon";
  if (i === 24) return "";
  if (i > 12) return String(i - 12);
  return String(i);
}

function formatTotal(h: number): string {
  const r = Math.round(h * 100) / 100;
  if (Math.abs(r - Math.round(r)) < 0.01) return String(Math.round(r));
  return r.toFixed(2);
}

function sortedSegments(segments: LogSegment[]) {
  return [...segments].sort((a, b) => segStartMin(a) - segStartMin(b));
}

function buildDutyPath(segments: LogSegment[]): string {
  const sorted = sortedSegments(segments);
  if (!sorted.length) return "";
  let path = "";
  sorted.forEach((seg, i) => {
    const ri = ROWS.findIndex((r) => r.key === seg.status);
    if (ri < 0) return;
    const x1 = xMin(segStartMin(seg));
    const x2 = xMin(Math.max(segEndMin(seg), segStartMin(seg) + 2));
    const y = rowY(ri);
    if (i === 0) {
      path += `M ${x1} ${y} H ${x2}`;
      return;
    }
    const prev = sorted[i - 1];
    const pri = ROWS.findIndex((r) => r.key === prev.status);
    const px = xMin(segEndMin(prev));
    path += ` H ${px}`;
    if (pri !== ri) path += ` V ${y}`;
    path += ` H ${x2}`;
  });
  const last = sorted[sorted.length - 1];
  if (segEndMin(last) >= 1440) {
    const ri = ROWS.findIndex((r) => r.key === last.status);
    if (ri >= 0) path += ` H ${xMin(1440)}`;
  }
  return path;
}

function formatRemarks(log: DailyLog): string {
  const lines: string[] = [];
  for (const r of log.remarks ?? []) {
    const loc = r.location ? `${r.location} — ` : "";
    lines.push(`${r.time}  ${loc}${r.note}`);
  }
  if (!lines.length && log.remark_brackets?.length) {
    for (const b of log.remark_brackets) {
      lines.push(`${b.start_time}–${b.end_time}  ${b.location}`);
    }
  }
  return lines.join("\n");
}

function TimeTicks({ uid }: { uid: string }) {
  const ticks = [];
  for (let m = 0; m <= 1440; m += 15) {
    const x = xMin(m);
    const isHour = m % 60 === 0;
    const isHalf = m % 30 === 0 && !isHour;
    const len = isHour ? ROW_H : isHalf ? ROW_H * 0.55 : ROW_H * 0.3;
    ticks.push(
      <line
        key={`${uid}-t-${m}`}
        x1={x}
        y1={GRID_BOTTOM - len}
        x2={x}
        y2={GRID_BOTTOM}
        stroke={isHour ? GRID : SUBGRID}
        strokeWidth={isHour ? 0.7 : 0.35}
      />
    );
  }
  return <g>{ticks}</g>;
}

function BoxField({
  label,
  value,
  className = "",
}: {
  label: string;
  value: string;
  className?: string;
}) {
  return (
    <div className={`border border-black flex flex-col ${className}`}>
      <div className="flex-1 px-1.5 py-1 text-[15px] min-h-[22px]">{value || "\u00a0"}</div>
      <p className="text-[9px] text-center border-t border-black leading-tight px-0.5 py-0.5 bg-white">{label}</p>
    </div>
  );
}

function LineField({ label, value, className = "" }: { label: string; value: string; className?: string }) {
  return (
    <div className={className}>
      <div className="border-b border-black text-[15px] pb-0.5 min-h-[20px] truncate">{value || "\u00a0"}</div>
      <p className="text-[9px] text-center mt-0.5 leading-tight">{label}</p>
    </div>
  );
}

interface Props {
  log: DailyLog;
}

export default function LogGrid({ log }: Props) {
  const uid = log.date.replace(/-/g, "");
  const d = new Date(log.date + "T12:00:00");
  const month = d.toLocaleDateString("en-US", { month: "2-digit" });
  const day = d.toLocaleDateString("en-US", { day: "2-digit" });
  const year = String(d.getFullYear());
  const form = log.form ?? {
    carrier_name: "Spotter Transport",
    office_address: "",
    driver_name: "Driver Name",
    vehicle_numbers: "—",
    shipping_no: `${uid}01`,
    co_driver: "",
  };
  const recap = log.recap;
  const segments = sortedSegments(log.segments);
  const dutyPath = buildDutyPath(segments);
  const remarksText = formatRemarks(log);
  const routeFrom = log.route_from || "—";
  const routeTo = log.route_to || "—";
  const miles = String(Math.round(log.total_miles));

  return (
    <article className="bg-white border-2 border-black mx-auto print:shadow-none text-black font-sans">
      {/* ── Header ── */}
      <div className="flex border-b border-black items-start px-3 pt-2 pb-2 gap-3">
        <div className="flex-shrink-0">
          <h2 className="text-[28px] font-bold leading-none tracking-tight">Drivers Daily Log</h2>
          <p className="text-[16px] text-center mt-1">(24 hours)</p>
        </div>

        <div className="flex-1 flex justify-center items-end gap-2 pt-1">
          <div className="text-center">
            <div className="border-b border-black w-16 text-[24px] font-semibold pb-1">{month}</div>
            <p className="text-[13px] text-gray-600 mt-0.5">(month)</p>
          </div>
          <span className="text-[24px] font-semibold pb-4">/</span>
          <div className="text-center">
            <div className="border-b border-black w-16 text-[24px] font-semibold pb-1">{day}</div>
            <p className="text-[13px] text-gray-600 mt-0.5">(day)</p>
          </div>
          <span className="text-[24px] font-semibold pb-4">/</span>
          <div className="text-center">
            <div className="border-b border-black w-24 text-[24px] font-semibold pb-1">{year}</div>
            <p className="text-[13px] text-gray-600 mt-0.5">(year)</p>
          </div>
        </div>

        <div className="flex-shrink-0 text-[14px] leading-snug text-right max-w-[250px]">
          <p>Original — File at home terminal.</p>
          <p>Duplicate — Driver retains in his/her possession for 8 days.</p>
        </div>
      </div>

      {/* ── From / To ── */}
      <div className="px-2 py-1 border-b border-black space-y-0.5">
        <div className="flex items-end gap-1">
          <span className="text-[14px] font-semibold flex-shrink-0">From:</span>
          <div className="flex-1 border-b border-black text-[15px] pb-0.5 min-h-[18px]">{routeFrom}</div>
        </div>
        <div className="flex items-end gap-1">
          <span className="text-[14px] font-semibold flex-shrink-0">To:</span>
          <div className="flex-1 border-b border-black text-[15px] pb-0.5 min-h-[18px]">{routeTo}</div>
        </div>
      </div>

      {/* ── Vehicle & Carrier ── */}
      <div className="flex border-b border-black">
        <div className="w-[52%] border-r border-black p-1.5 space-y-1">
          <div className="flex gap-1">
            <BoxField label="Total Miles Driving Today" value={miles} className="flex-1" />
            <BoxField label="Total Mileage Today" value={miles} className="flex-1" />
          </div>
          <BoxField
            label="Truck/Tractor and Trailer Numbers or License Plate(s)/State (show each unit)"
            value={form.vehicle_numbers}
            className="min-h-[44px]"
          />
        </div>
        <div className="flex-1 p-1.5 space-y-2">
          <LineField label="Name of Carrier or Carriers" value={form.carrier_name} />
          <LineField label="Main Office Address" value={form.office_address} />
          <LineField label="Home Terminal Address" value={form.office_address} />
        </div>
      </div>

      {/* ── 24-hour grid ── */}
      <svg viewBox={`0 0 ${SVG_W} ${SVG_H}`} className="w-full block" aria-label={`Log grid ${log.date}`}>
        {/* Black time bar */}
        <rect x={0} y={0} width={SVG_W} height={TIME_BAR_H} fill={INK} />
        {Array.from({ length: 25 }, (_, i) => {
          const label = hourLabel(i);
          const x = GRID_LEFT + (i / 24) * GRID_WIDTH;
          return (
            <text
              key={`tb-${i}`}
              x={x}
              y={TIME_BAR_H - 4}
              textAnchor="middle"
              fontSize="9"
              fill="#ffffff"
              fontFamily="Arial, sans-serif"
            >
              {label}
            </text>
          );
        })}
        <text
          x={TOTAL_X + TOTAL_W / 2}
          y={TIME_BAR_H - 4}
          textAnchor="middle"
          fontSize="9"
          fill="#ffffff"
          fontFamily="Arial, sans-serif"
          fontWeight="600"
        >
          Total Hours
        </text>

        {/* Grid frame */}
        <rect
          x={0}
          y={GRID_TOP}
          width={SVG_W}
          height={GRID_BOTTOM - GRID_TOP}
          fill="none"
          stroke={GRID}
          strokeWidth="1"
        />
        <line x1={TOTAL_X} y1={GRID_TOP} x2={TOTAL_X} y2={GRID_BOTTOM} stroke={GRID} strokeWidth="1" />

        <TimeTicks uid={uid} />

        {ROWS.map((row, idx) => {
          const y = GRID_TOP + idx * ROW_H;
          return (
            <g key={`${uid}-${row.key}`}>
              <text x={3} y={y + ROW_H / 2 + 4} fontSize="9.5" fontFamily="Arial, sans-serif">
                {row.label}
              </text>
              <line x1={GRID_LEFT} y1={y} x2={GRID_LEFT + GRID_WIDTH} y2={y} stroke={GRID} strokeWidth="0.5" />
            </g>
          );
        })}

        {/* Total hour lines + values */}
        {ROWS.map((row, idx) => {
          const y = GRID_TOP + idx * ROW_H + ROW_H / 2 + 2;
          const lineY = GRID_TOP + idx * ROW_H + ROW_H / 2 + 5;
          return (
            <g key={`${uid}-tot-${row.key}`}>
              <line
                x1={TOTAL_X + 4}
                y1={lineY}
                x2={TOTAL_X + TOTAL_W - 4}
                y2={lineY}
                stroke={GRID}
                strokeWidth="0.5"
              />
              <text
                x={TOTAL_X + TOTAL_W / 2}
                y={y}
                textAnchor="middle"
                fontSize="12"
                fill={INK}
                fontFamily="Arial, sans-serif"
              >
                {formatTotal(log.totals[row.key] ?? 0)}
              </text>
            </g>
          );
        })}

        {dutyPath && (
          <path d={dutyPath} fill="none" stroke={INK} strokeWidth="3.5" strokeLinecap="butt" strokeLinejoin="miter" />
        )}
      </svg>

      {/* ── Remarks ── */}
      <div className="border-t border-black px-2 pt-1 pb-1.5">
        <p className="text-[13px] font-bold mb-1">Remarks</p>
        <div className="border border-black min-h-[72px] p-2 text-[12px] leading-relaxed whitespace-pre-wrap">
          {remarksText || "\u00a0"}
        </div>
        <div className="mt-1.5 flex gap-4 items-start">
          <div className="flex-shrink-0">
            <p className="text-[11px] font-semibold mb-0.5">Shipping Documents:</p>
            <div className="flex items-end gap-1 mb-0.5">
              <span className="text-[11px] whitespace-nowrap">DVL or Manifest No. or</span>
              <span className="border-b border-black text-[12px] min-w-[90px] pb-0.5">{form.shipping_no}</span>
            </div>
            <div className="flex items-end gap-1">
              <span className="text-[11px] whitespace-nowrap">Shipper &amp; Commodity</span>
              <span className="border-b border-black text-[12px] min-w-[90px] pb-0.5">{form.carrier_name}</span>
            </div>
          </div>
          <p className="text-[9px] leading-snug flex-1 pt-2">
            Enter name of place you reported and where released from work and when and where each change of duty
            occurred. Use time standard of home terminal.
          </p>
        </div>
      </div>

      {/* ── Recap ── */}
      <div className="border-t-2 border-black px-4 py-4 text-[13px] leading-normal">
        <div className="flex gap-4 items-start">
          <p className="font-bold flex-shrink-0 w-[140px] text-[15px] leading-snug">
            Recap: Complete at end of day
          </p>

          <div className="flex-shrink-0 w-[150px]">
            <div className="border-b border-black text-[20px] font-semibold pb-1 min-h-[28px] text-center">
              {formatTotal(recap.on_duty_today)}
            </div>
            <p className="text-[13px] text-center mt-1.5 leading-snug">
              On duty hours today, Total lines 3 &amp; 4
            </p>
          </div>

          {/* 70 Hour / 8 Day */}
          <div className="flex-1 border border-black p-3">
            <p className="font-bold text-center mb-2 underline text-[15px]">70 Hour / 8 Day Drivers</p>
            <div className="grid grid-cols-3 gap-3">
              {[
                ["A.", "Total hours on duty last 7 days including today.", formatTotal(recap.total_7_days_including_today)],
                ["B.", "Total hours available tomorrow 70 hr. minus A*", formatTotal(recap.available_tomorrow_70)],
                ["C.", "Total hours on duty last 8 days including today.", formatTotal(recap.total_8_days_including_today)],
              ].map(([letter, desc, val]) => (
                <div key={letter as string}>
                  <p className="font-semibold text-[14px]">{letter as string}</p>
                  <div className="border-b border-black min-h-[26px] text-[20px] font-semibold text-center mb-1.5">{val as string}</div>
                  <p className="text-[12px] leading-snug">{desc as string}</p>
                </div>
              ))}
            </div>
          </div>

          {/* 60 Hour / 7 Day */}
          <div className="flex-1 border border-black p-3">
            <p className="font-bold text-center mb-2 underline text-[15px]">60 Hour / 7 Day Drivers</p>
            <div className="grid grid-cols-3 gap-3">
              {[
                ["A.", "Total hours on duty last 6 days including today.", "—"],
                ["B.", "Total hours available tomorrow 60 hr. minus A*", "—"],
                ["C.", "Total hours on duty last 7 days including today.", "—"],
              ].map(([letter, desc, val]) => (
                <div key={letter as string}>
                  <p className="font-semibold text-[14px]">{letter as string}</p>
                  <div className="border-b border-black min-h-[26px] text-[20px] font-semibold text-center mb-1.5">{val as string}</div>
                  <p className="text-[12px] leading-snug">{desc as string}</p>
                </div>
              ))}
            </div>
          </div>

          <p className="flex-shrink-0 w-[120px] text-[12px] leading-snug self-end">
            *If you took 34 consecutive hours off duty you have 60/70 hours available
          </p>
        </div>
      </div>
    </article>
  );
}
