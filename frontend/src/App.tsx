import { useState } from "react";
import TripForm from "./components/TripForm";
import RouteMap from "./components/RouteMap";
import LogGrid from "./components/LogGrid";
import { apiUrl } from "./lib/api";
import type { TripPlanResponse } from "./types";

export default function App() {
  const [plan, setPlan] = useState<TripPlanResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const planTrip = async (body: {
    current_location: string;
    pickup_location: string;
    dropoff_location: string;
    cycle_used_hours: number;
  }) => {
    setLoading(true);
    setError(null);
    setPlan(null);
    try {
      const res = await fetch(apiUrl("/api/plan/"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Planning failed");
      setPlan(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen">
      <header className="bg-navy-900 text-white">
        <div className="max-w-7xl mx-auto px-4 py-8">
          <p className="text-road-500 text-sm font-semibold uppercase tracking-wider">
            FMCSA HOS · Property · 70/8
          </p>
          <h1 className="font-display text-4xl mt-1">Spotter</h1>
          <p className="text-slate-300 mt-2 max-w-2xl">
            Plan interstate trips, map your route with free OpenStreetMap data, and generate
            driver daily log grids with 14-hour window, 11-hour driving, 30-minute break, and
            rolling 8-day recap.
          </p>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 py-8">
        <div className="grid lg:grid-cols-3 gap-8">
          <div className="lg:col-span-1">
            <TripForm onSubmit={planTrip} loading={loading} />
            {error && (
              <p className="mt-4 text-sm text-red-700 bg-red-50 border border-red-200 rounded-lg p-3">
                {error}
              </p>
            )}
          </div>

          <div className="lg:col-span-2 space-y-6">
            {plan && (
              <>
                <div className="grid sm:grid-cols-3 gap-3">
                  {[
                    ["Total miles", plan.summary.total_miles],
                    ["Drive hours (est.)", plan.summary.estimated_drive_hours],
                    ["Log days", plan.summary.log_days],
                  ].map(([label, val]) => (
                    <div
                      key={String(label)}
                      className="bg-white rounded-lg border border-slate-200 p-4 text-center"
                    >
                      <p className="text-xs text-slate-500 uppercase">{label}</p>
                      <p className="text-2xl font-bold text-navy-900">{val}</p>
                    </div>
                  ))}
                </div>

                <RouteMap plan={plan} />

                <section className="bg-white rounded-xl border border-slate-200 p-5">
                  <h2 className="text-lg font-semibold text-navy-900 mb-3">Route instructions</h2>
                  <ol className="space-y-3">
                    {plan.instructions.map((step) => (
                      <li key={step.order} className="flex gap-3 text-sm">
                        <span className="flex-shrink-0 w-7 h-7 rounded-full bg-navy-900 text-white flex items-center justify-center text-xs font-bold">
                          {step.order}
                        </span>
                        <div>
                          <p className="font-semibold">{step.title}</p>
                          <p className="text-slate-600">{step.detail}</p>
                        </div>
                      </li>
                    ))}
                  </ol>
                </section>
              </>
            )}
            {!plan && !loading && (
              <div className="bg-white/60 border border-dashed border-slate-300 rounded-xl p-12 text-center text-slate-500">
                Enter trip details and plan a route to see the map and ELD logs.
              </div>
            )}
          </div>
        </div>

        {plan && plan.daily_logs.length > 0 && (
          <section className="mt-12 space-y-8">
            <h2 className="text-2xl font-display text-navy-900">Daily log sheets</h2>
            {plan.daily_logs.map((log) => (
              <LogGrid key={log.date} log={log} />
            ))}
          </section>
        )}
      </main>

      <footer className="text-center text-xs text-slate-500 py-8 border-t border-slate-200 mt-8">
        Based on FMCSA Interstate Truck Driver&apos;s Guide to HOS (April 2022). Guidance only — not legal advice.
      </footer>
    </div>
  );
}
