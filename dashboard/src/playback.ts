import { useCallback, useEffect, useState } from "react";
import type { Run } from "./types";

const STEP_MS = 125;
const CHARGE_W = 10_000;

export type BookmarkId = "charge" | "spike" | "offline";

export type Bookmark = {
  id: BookmarkId;
  label: "CHARGE" | "SPIKE" | "OFFLINE";
  index: number;
};

export function bookmarks(run: Pick<Run, "ticks">): Bookmark[] {
  const ticks = run.ticks;
  const out: Bookmark[] = [];

  const charge = ticks.findIndex((t) => t.fleet_w > CHARGE_W);
  if (charge >= 0) {
    out.push({ id: "charge", label: "CHARGE", index: charge });
  }

  let spike = -1;
  let maxPrice = -Infinity;
  for (let i = 0; i < ticks.length; i++) {
    const price = ticks[i].price_usd_per_mwh;
    if (price == null) {
      continue;
    }
    if (price > maxPrice) {
      maxPrice = price;
      spike = i;
    }
  }
  if (spike >= 0) {
    out.push({ id: "spike", label: "SPIKE", index: spike });
  }

  const offline = ticks.findIndex((t) => t.n_unreachable > 0);
  if (offline >= 0) {
    out.push({ id: "offline", label: "OFFLINE", index: offline });
  }

  return out;
}

export function playStart(marks: Bookmark[]): number {
  return (
    marks.find((m) => m.id === "charge")?.index ??
    marks.find((m) => m.id === "offline")?.index ??
    marks.find((m) => m.id === "spike")?.index ??
    0
  );
}

export function usePlayback(nTicks: number, startAt = 0) {
  const last = Math.max(0, nTicks - 1);
  const origin = Math.min(last, Math.max(0, startAt));
  const [index, setIndexRaw] = useState(origin);
  const [playing, setPlaying] = useState(false);

  const setIndex = useCallback(
    (next: number) => {
      const hi = Math.max(0, nTicks - 1);
      setIndexRaw(Math.min(hi, Math.max(0, next)));
    },
    [nTicks],
  );

  const play = useCallback(() => {
    setIndexRaw((i) => (nTicks > 0 && i >= nTicks - 1 ? origin : i));
    setPlaying(true);
  }, [nTicks, origin]);

  const pause = useCallback(() => {
    setPlaying(false);
  }, []);

  const toggle = useCallback(() => {
    setPlaying((on) => {
      if (on) {
        return false;
      }
      setIndexRaw((i) => (nTicks > 0 && i >= nTicks - 1 ? origin : i));
      return true;
    });
  }, [nTicks, origin]);

  useEffect(() => {
    setIndexRaw((i) => Math.min(i, last));
  }, [last]);

  useEffect(() => {
    if (!playing || nTicks <= 1) {
      return;
    }
    const id = window.setInterval(() => {
      setIndexRaw((i) => {
        if (i >= nTicks - 1) {
          setPlaying(false);
          return nTicks - 1;
        }
        return i + 1;
      });
    }, STEP_MS);
    return () => window.clearInterval(id);
  }, [playing, nTicks]);

  return { index, playing, setIndex, toggle, play, pause };
}
