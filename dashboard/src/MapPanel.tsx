import { useEffect } from "react";
import "leaflet/dist/leaflet.css";
import {
  CircleMarker,
  MapContainer,
  TileLayer,
  Tooltip,
  useMap,
} from "react-leaflet";
import type { Site, Tick } from "./types";

function FillMap() {
  const map = useMap();
  useEffect(() => {
    const paint = () => map.invalidateSize();
    paint();
    const frame = window.requestAnimationFrame(paint);
    const timer = window.setTimeout(paint, 80);
    window.addEventListener("resize", paint);
    return () => {
      window.cancelAnimationFrame(frame);
      window.clearTimeout(timer);
      window.removeEventListener("resize", paint);
    };
  }, [map]);
  return null;
}

const AUSTIN: [[number, number], [number, number]] = [
  [30.19, -97.88],
  [30.41, -97.66],
];
const COPPER = "#c47b3a";
const TEAL = "#3ecfc1";
const FAULT = "#e85d4c";
const MUTED = "#7d756c";
const TILES =
  "https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}";
const LABELS =
  "https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Reference/MapServer/tile/{z}/{y}/{x}";
const ATTR = "Tiles &copy; Esri";
const LEGEND = [
  { label: "charge", swatch: "copper" },
  { label: "discharge", swatch: "teal" },
  { label: "idle", swatch: "muted" },
  { label: "unreachable", swatch: "ring" },
] as const;

function siteNetW(site: Site, tick: Tick): number {
  let sum = 0;
  for (const id of site.unit_ids) {
    const u = tick.units[id];
    if (u) {
      sum += u.actual_w;
    }
  }
  return sum;
}

function anyUnreachable(site: Site, tick: Tick): boolean {
  return site.unit_ids.some((id) => tick.units[id]?.reachable === false);
}

function fillColor(netW: number): string {
  if (netW > 1) {
    return COPPER;
  }
  if (netW < -1) {
    return TEAL;
  }
  return MUTED;
}

function kw(watts: number): string {
  const k = watts / 1000;
  const sign = k > 0 ? "+" : "";
  return `${sign}${k.toFixed(1)} kW`;
}

export default function MapPanel({
  sites,
  tick,
}: {
  sites: Site[];
  tick: Tick;
}) {
  return (
    <>
      <MapContainer
        className="fleet-map"
        bounds={AUSTIN}
        boundsOptions={{ padding: [24, 24] }}
        center={[30.29, -97.74]}
        zoom={12}
        zoomControl
        attributionControl
        scrollWheelZoom
      >
        <FillMap />
        <TileLayer url={TILES} attribution={ATTR} />
        <TileLayer url={LABELS} attribution="" />
        {sites.map((site) => {
          const net = siteNetW(site, tick);
          const fill = fillColor(net);
          const down = anyUnreachable(site, tick);
          return (
            <CircleMarker
              key={site.id}
              center={[site.lat, site.lon]}
              radius={9}
              bubblingMouseEvents={false}
              eventHandlers={{
                mouseover: (e) => {
                  e.target.bringToFront();
                },
              }}
              pathOptions={{
                color: down ? FAULT : fill,
                weight: down ? 2.5 : 1.25,
                fillColor: fill,
                fillOpacity: down ? 0.25 : 0.72,
                opacity: 1,
              }}
            >
              <Tooltip
                className="site-tip"
                sticky
                direction="top"
                offset={[0, -8]}
                opacity={1}
              >
                <div className="site-tip-body">
                  <div className="site-tip-id">{site.id}</div>
                  {site.unit_ids.map((id) => {
                    const u = tick.units[id];
                    if (!u) {
                      return (
                        <div key={id} className="site-tip-row">
                          {id} —
                        </div>
                      );
                    }
                    const soc = `${(u.soc * 100).toFixed(0)}%`;
                    const reach = u.reachable ? "ok" : "OFF";
                    return (
                      <div key={id} className="site-tip-row">
                        <span>{id}</span>
                        <span>{kw(u.actual_w)}</span>
                        <span>SOC {soc}</span>
                        <span className={u.reachable ? "" : "tip-off"}>
                          {reach}
                        </span>
                        <span>cmd {u.commanded_w.toFixed(0)} W</span>
                      </div>
                    );
                  })}
                </div>
              </Tooltip>
            </CircleMarker>
          );
        })}
      </MapContainer>
      <ul className="map-legend" aria-label="Site colors">
        {LEGEND.map((item) => (
          <li key={item.label}>
            <span className={`map-legend-mark is-${item.swatch}`} />
            {item.label}
          </li>
        ))}
      </ul>
    </>
  );
}
