import type { Tick } from "./types";

function utcClock(timeUnix: number): string {
  const iso = new Date(timeUnix * 1000).toISOString();
  return `${iso.slice(0, 10)} ${iso.slice(11, 16)} UTC`;
}

function mw(watts: number): string {
  return (watts / 1e6).toFixed(3);
}

function money(value: number | null): string {
  return value === null ? "—" : value.toFixed(2);
}

function Cell({
  label,
  value,
  tone,
}: {
  label: string;
  value: string;
  tone?: "copper" | "teal" | "fault" | "paper";
}) {
  return (
    <div className="kpi-cell">
      <span className="kpi-label">{label}</span>
      <span className={`kpi-value${tone ? ` kpi-${tone}` : ""}`}>{value}</span>
    </div>
  );
}

export default function KpiBar({ tick }: { tick: Tick }) {
  const target =
    tick.target_w === null ? "—" : `${mw(tick.target_w)} MW`;
  const price =
    tick.price_usd_per_mwh === null
      ? "—"
      : tick.price_usd_per_mwh.toFixed(1);
  const fault = tick.n_unreachable > 0;

  return (
    <div className="kpi-bar">
      <Cell label="clock" value={utcClock(tick.time_unix)} tone="paper" />
      <Cell label="RT $/MWh" value={price} tone="copper" />
      <Cell label="fleet" value={`${mw(tick.fleet_w)} MW`} tone="copper" />
      <Cell label="target" value={target} tone="teal" />
      <Cell
        label="error W"
        value={tick.error_w.toLocaleString("en-US", {
          maximumFractionDigits: 0,
        })}
      />
      <Cell
        label="unreachable"
        value={String(tick.n_unreachable)}
        tone={fault ? "fault" : undefined}
      />
      <Cell label="company $" value={money(tick.score_usd)} tone="paper" />
      <Cell
        label="customer $"
        value={money(tick.customer_bill_usd)}
        tone="teal"
      />
    </div>
  );
}
