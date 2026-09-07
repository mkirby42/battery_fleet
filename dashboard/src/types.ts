export type CommandKind = "target" | "setpoint" | "offline" | "online" | "clip";

export type Site = {
  id: string;
  lat: number;
  lon: number;
  unit_ids: string[];
};

export type Unit = {
  id: string;
  site_id: string;
  capacity_kwh: number;
};

export type UnitTick = {
  soc: number;
  actual_w: number;
  commanded_w: number;
  reachable: boolean;
};

export type Tick = {
  time_unix: number;
  price_usd_per_mwh: number | null;
  target_w: number | null;
  fleet_w: number;
  commanded_w: number;
  error_w: number;
  load_w: number;
  score_usd: number | null;
  wholesale_pnl_usd: number | null;
  customer_bill_usd: number | null;
  no_battery_customer_bill_usd: number | null;
  n_unreachable: number;
  mean_soc: number;
  cumulative_score_usd: number;
  cumulative_customer_bill_usd: number;
  units: Record<string, UnitTick>;
};

export type CommandEvent = {
  time_unix: number;
  kind: CommandKind;
  unit_id: string | null;
  site_id: string | null;
  watts: number | null;
  note: string;
};

export type Run = {
  id: string;
  dt_seconds: number;
  started_at_unix: number;
  sites: Site[];
  units: Unit[];
  ticks: Tick[];
  commands: CommandEvent[];
};

export type RunSummary = {
  id: string;
  started_at_unix: number;
  n_ticks: number;
};
