import type { CommandEvent, CommandKind } from "./types";

const WATTS_EPS = 1e-6;

type LogRow = {
  time_unix: number;
  kind: CommandKind;
  label: string;
  watts: number | null;
  n: number;
};

function utcShort(timeUnix: number): string {
  return new Date(timeUnix * 1000).toISOString().slice(11, 16);
}

function who(ev: CommandEvent): string {
  return ev.unit_id ?? ev.site_id ?? "fleet";
}

function formatWatts(value: number | null): string {
  if (value === null) {
    return "—";
  }
  return value.toLocaleString("en-US", { maximumFractionDigits: 0 });
}

function wattsKey(value: number | null): string {
  if (value === null) {
    return "null";
  }
  return String(Math.round(value / WATTS_EPS));
}

function collapse(commands: CommandEvent[], timeUnix: number): LogRow[] {
  const rows: LogRow[] = [];
  const groupAt = new Map<string, number>();

  for (const ev of commands.filter((c) => c.time_unix <= timeUnix).reverse()) {
    if (ev.kind !== "setpoint") {
      rows.push({
        time_unix: ev.time_unix,
        kind: ev.kind,
        label: who(ev),
        watts: ev.watts,
        n: 1,
      });
      continue;
    }
    const key = `${ev.time_unix}:${wattsKey(ev.watts)}`;
    const i = groupAt.get(key);
    if (i === undefined) {
      groupAt.set(key, rows.length);
      rows.push({
        time_unix: ev.time_unix,
        kind: "setpoint",
        label: who(ev),
        watts: ev.watts,
        n: 1,
      });
      continue;
    }
    const row = rows[i];
    row.n += 1;
    row.label = `${row.n} units`;
  }
  return rows;
}

const KIND_CLASS: Record<CommandKind, string> = {
  target: "kind-target",
  setpoint: "kind-setpoint",
  clip: "kind-clip",
  offline: "kind-fault",
  online: "kind-fault",
};

export default function CommandLog({
  commands,
  timeUnix,
}: {
  commands: CommandEvent[];
  timeUnix: number;
}) {
  const rows = collapse(commands, timeUnix);

  return (
    <section className="cmd-log">
      <header className="cmd-head">
        <span>command log</span>
        <span className="cmd-count">{rows.length}</span>
      </header>
      <div className="cmd-cols">
        <span>time</span>
        <span>kind</span>
        <span>unit/site</span>
        <span>watts</span>
      </div>
      <ol className="cmd-rows">
        {rows.map((row, i) => (
          <li
            key={`${row.time_unix}-${row.kind}-${row.label}-${i}`}
            className="cmd-row"
          >
            <span className="cmd-time">{utcShort(row.time_unix)}</span>
            <span className={`cmd-kind ${KIND_CLASS[row.kind]}`}>{row.kind}</span>
            <span className="cmd-who">{row.label}</span>
            <span className="cmd-w">{formatWatts(row.watts)}</span>
          </li>
        ))}
      </ol>
    </section>
  );
}
