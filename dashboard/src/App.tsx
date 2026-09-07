import { useEffect, useState } from "react";
import { getRun, listRuns } from "./api";
import ChartsPanel from "./ChartsPanel";
import CommandLog from "./CommandLog";
import KpiBar from "./KpiBar";
import MapPanel from "./MapPanel";
import { bookmarks, playStart, usePlayback } from "./playback";
import Scrubber from "./Scrubber";
import type { Run } from "./types";
import "./App.css";
import "./rail.css";

const HINT =
  "Generate a run: .venv/bin/python scripts/demo_market_day.py then .venv/bin/python -m battery_fleet serve";

function Console({ run }: { run: Run }) {
  const marks = bookmarks(run);
  const { index, playing, setIndex, toggle, pause } = usePlayback(
    run.ticks.length,
    playStart(marks),
  );
  const tick = run.ticks[index];
  if (!tick) {
    return (
      <main className="shell">
        <p className="hint">{HINT}</p>
      </main>
    );
  }

  return (
    <div className="console">
      <div className="map-stage">
        <MapPanel sites={run.sites} tick={tick} />
        <KpiBar tick={tick} />
        <p className="run-chip">{run.id}</p>
      </div>
      <aside className="rail">
        <ChartsPanel ticks={run.ticks} index={index} />
        <CommandLog commands={run.commands} timeUnix={tick.time_unix} />
      </aside>
      <Scrubber
        nTicks={run.ticks.length}
        index={index}
        playing={playing}
        setIndex={setIndex}
        toggle={toggle}
        pause={pause}
        bookmarks={marks}
      />
    </div>
  );
}

export default function App() {
  const [run, setRun] = useState<Run | null>(null);
  const [failed, setFailed] = useState(false);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        const runs = await listRuns();
        if (cancelled) {
          return;
        }
        if (runs.length === 0) {
          setFailed(true);
          setReady(true);
          return;
        }
        const newest = await getRun(runs[0].id);
        if (cancelled) {
          return;
        }
        setRun(newest);
        setReady(true);
      } catch {
        if (!cancelled) {
          setFailed(true);
          setReady(true);
        }
      }
    }

    void load();
    return () => {
      cancelled = true;
    };
  }, []);

  if (!ready) {
    return <main className="shell" />;
  }

  if (failed || run === null) {
    return (
      <main className="shell">
        <p className="hint">{HINT}</p>
      </main>
    );
  }

  return <Console run={run} />;
}
