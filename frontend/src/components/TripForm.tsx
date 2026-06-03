interface Props {
  onSubmit: (data: {
    current_location: string;
    pickup_location: string;
    dropoff_location: string;
    cycle_used_hours: number;
  }) => void;
  loading: boolean;
}

export default function TripForm({ onSubmit, loading }: Props) {
  const handle = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const fd = new FormData(e.currentTarget);
    onSubmit({
      current_location: String(fd.get("current") || ""),
      pickup_location: String(fd.get("pickup") || ""),
      dropoff_location: String(fd.get("dropoff") || ""),
      cycle_used_hours: Number(fd.get("cycle") || 0),
    });
  };

  return (
    <form
      onSubmit={handle}
      className="bg-white rounded-xl shadow-lg border border-slate-200 p-6 space-y-4"
    >
      <h2 className="text-lg font-semibold text-navy-900">Trip details</h2>
      <p className="text-sm text-slate-600">
        Property carrier · 70 hr / 8 day · Fuel every 1,000 mi · 1 hr pickup &amp; dropoff
      </p>
      <label className="block">
        <span className="text-sm font-medium text-slate-700">Current location</span>
        <input
          name="current"
          required
          defaultValue="Richmond, VA"
          className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:ring-2 focus:ring-road-500 focus:border-road-500"
          placeholder="City, State"
        />
      </label>
      <label className="block">
        <span className="text-sm font-medium text-slate-700">Pickup location</span>
        <input
          name="pickup"
          required
          defaultValue="Baltimore, MD"
          className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:ring-2 focus:ring-road-500"
        />
      </label>
      <label className="block">
        <span className="text-sm font-medium text-slate-700">Dropoff location</span>
        <input
          name="dropoff"
          required
          defaultValue="Newark, NJ"
          className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:ring-2 focus:ring-road-500"
        />
      </label>
      <label className="block">
        <span className="text-sm font-medium text-slate-700">
          Current cycle used (on-duty hrs, 8-day)
        </span>
        <input
          name="cycle"
          type="number"
          min={0}
          max={70}
          step={0.5}
          defaultValue={0}
          className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
        />
      </label>
      <button
        type="submit"
        disabled={loading}
        className="w-full rounded-lg bg-road-600 hover:bg-road-500 disabled:opacity-60 text-white font-semibold py-3 transition-colors"
      >
        {loading ? "Planning route & logs…" : "Plan trip & generate logs"}
      </button>
    </form>
  );
}
