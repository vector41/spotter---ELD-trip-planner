import { MapContainer, TileLayer, Polyline, Marker, Popup } from "react-leaflet";
import L from "leaflet";
import type { GeoLocation, TripPlanResponse } from "../types";

const icon = L.divIcon({
  className: "custom-marker",
  html: `<div style="background:#0c1e3a;width:12px;height:12px;border-radius:50%;border:2px solid #fff;box-shadow:0 1px 4px rgba(0,0,0,.4)"></div>`,
  iconSize: [12, 12],
  iconAnchor: [6, 6],
});

interface Props {
  plan: TripPlanResponse;
}

export default function RouteMap({ plan }: Props) {
  const coords = plan.route.geometry.coordinates.map(
    ([lon, lat]) => [lat, lon] as [number, number]
  );
  const points: { loc: GeoLocation; role: string }[] = [
    { loc: plan.locations.current, role: "Current" },
    { loc: plan.locations.pickup, role: "Pickup" },
    { loc: plan.locations.dropoff, role: "Dropoff" },
  ];
  const center = coords[Math.floor(coords.length / 2)] ?? [
    plan.locations.pickup.lat,
    plan.locations.pickup.lon,
  ];

  return (
    <div className="rounded-xl overflow-hidden border border-slate-300 shadow-md h-[420px]">
      <MapContainer center={center} zoom={5} className="h-full w-full" scrollWheelZoom>
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        <Polyline positions={coords} pathOptions={{ color: "#b45309", weight: 5, opacity: 0.85 }} />
        {points.map((p) => (
          <Marker key={p.role} position={[p.loc.lat, p.loc.lon]} icon={icon}>
            <Popup>
              <strong>{p.role}</strong>
              <br />
              {p.loc.query}
            </Popup>
          </Marker>
        ))}
      </MapContainer>
    </div>
  );
}
