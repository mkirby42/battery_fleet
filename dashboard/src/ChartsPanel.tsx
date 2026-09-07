import { useEffect, useRef } from "react";
import {
  AreaSeries,
  ColorType,
  CrosshairMode,
  HistogramSeries,
  LineSeries,
  LineStyle,
  createChart,
  type IChartApi,
  type ISeriesApi,
  type UTCTimestamp,
} from "lightweight-charts";
import type { Tick } from "./types";

const INK = "#0b0a09";
const COPPER = "#c47b3a";
const TEAL = "#3ecfc1";
const PAPER = "#ddd4c6";
const MUTED = "#7d756c";

function ts(unix: number): UTCTimestamp {
  return unix as UTCTimestamp;
}

function mwLabel(p: number): string {
  return (p / 1e6).toFixed(2);
}

function socLabel(p: number): string {
  return `${(p * 100).toFixed(0)}%`;
}

function linePts(ticks: Tick[], read: (t: Tick) => number | null) {
  return ticks.map((tick) => {
    const value = read(tick);
    return value === null
      ? { time: ts(tick.time_unix) }
      : { time: ts(tick.time_unix), value };
  });
}

function headPts(ticks: Tick[], index: number) {
  return ticks.map((tick, i) =>
    i === index
      ? { time: ts(tick.time_unix), value: 1 }
      : { time: ts(tick.time_unix) },
  );
}

function chartOpts() {
  return {
    autoSize: true,
    layout: {
      background: { type: ColorType.Solid, color: INK },
      textColor: MUTED,
      fontFamily: "IBM Plex Sans, sans-serif",
      fontSize: 10,
      attributionLogo: false,
    },
    grid: {
      vertLines: { color: "rgba(221, 212, 198, 0.06)" },
      horzLines: { color: "rgba(221, 212, 198, 0.06)" },
    },
    crosshair: {
      mode: CrosshairMode.Normal,
      vertLine: {
        color: "rgba(221, 212, 198, 0.55)",
        width: 1 as const,
        style: LineStyle.Solid,
        labelVisible: false,
      },
      horzLine: { visible: false, labelVisible: false },
    },
    leftPriceScale: {
      visible: true,
      borderColor: "rgba(125, 117, 108, 0.35)",
      textColor: MUTED,
      entireTextOnly: true,
    },
    rightPriceScale: {
      visible: true,
      borderColor: "rgba(125, 117, 108, 0.35)",
      textColor: MUTED,
      entireTextOnly: true,
    },
    timeScale: {
      borderColor: "rgba(125, 117, 108, 0.35)",
      timeVisible: true,
      secondsVisible: false,
    },
  };
}

const headOpts = {
  color: "rgba(221, 212, 198, 0.28)",
  priceScaleId: "playhead",
  lastValueVisible: false,
  priceLineVisible: false,
  autoscaleInfoProvider: () => ({
    priceRange: { minValue: 0, maxValue: 1 },
  }),
};

type PowerApi = {
  chart: IChartApi;
  fleet: ISeriesApi<"Area">;
  head: ISeriesApi<"Histogram">;
};

type SocApi = {
  chart: IChartApi;
  soc: ISeriesApi<"Area">;
  company: ISeriesApi<"Line">;
  head: ISeriesApi<"Histogram">;
};

export default function ChartsPanel({
  ticks,
  index,
}: {
  ticks: Tick[];
  index: number;
}) {
  const powerEl = useRef<HTMLDivElement>(null);
  const socEl = useRef<HTMLDivElement>(null);
  const powerApi = useRef<PowerApi | null>(null);
  const socApi = useRef<SocApi | null>(null);

  useEffect(() => {
    const a = powerEl.current;
    const b = socEl.current;
    if (!a || !b || ticks.length === 0) {
      return;
    }

    const power = createChart(a, chartOpts());
    const fleet = power.addSeries(AreaSeries, {
      lineColor: COPPER,
      topColor: "rgba(196, 123, 58, 0.38)",
      bottomColor: "rgba(196, 123, 58, 0.02)",
      lineWidth: 2,
      priceScaleId: "right",
      lastValueVisible: false,
      priceLineVisible: false,
      priceFormat: { type: "custom", minMove: 1, formatter: mwLabel },
    });
    const target = power.addSeries(LineSeries, {
      color: TEAL,
      lineWidth: 2,
      lineStyle: LineStyle.Dashed,
      priceScaleId: "right",
      lastValueVisible: false,
      priceLineVisible: false,
      priceFormat: { type: "custom", minMove: 1, formatter: mwLabel },
    });
    const price = power.addSeries(LineSeries, {
      color: PAPER,
      lineWidth: 2,
      priceScaleId: "left",
      lastValueVisible: false,
      priceLineVisible: false,
      priceFormat: { type: "price", precision: 0, minMove: 1 },
    });
    const pHead = power.addSeries(HistogramSeries, headOpts);
    power.priceScale("playhead").applyOptions({ visible: false });
    fleet.setData(linePts(ticks, (t) => t.fleet_w));
    target.setData(linePts(ticks, (t) => t.target_w));
    price.setData(linePts(ticks, (t) => t.price_usd_per_mwh));
    power.timeScale().fitContent();
    powerApi.current = { chart: power, fleet, head: pHead };

    const socChart = createChart(b, chartOpts());
    const soc = socChart.addSeries(AreaSeries, {
      lineColor: TEAL,
      topColor: "rgba(62, 207, 193, 0.32)",
      bottomColor: "rgba(62, 207, 193, 0.02)",
      lineWidth: 2,
      priceScaleId: "left",
      lastValueVisible: false,
      priceLineVisible: false,
      priceFormat: { type: "custom", minMove: 0.01, formatter: socLabel },
      autoscaleInfoProvider: () => ({
        priceRange: { minValue: 0, maxValue: 1 },
      }),
    });
    const company = socChart.addSeries(LineSeries, {
      color: COPPER,
      lineWidth: 2,
      priceScaleId: "right",
      lastValueVisible: false,
      priceLineVisible: false,
      priceFormat: { type: "price", precision: 0, minMove: 0.01 },
    });
    const customer = socChart.addSeries(LineSeries, {
      color: PAPER,
      lineWidth: 2,
      priceScaleId: "right",
      lastValueVisible: false,
      priceLineVisible: false,
      priceFormat: { type: "price", precision: 0, minMove: 0.01 },
    });
    const sHead = socChart.addSeries(HistogramSeries, headOpts);
    socChart.priceScale("playhead").applyOptions({ visible: false });
    soc.setData(linePts(ticks, (t) => t.mean_soc));
    company.setData(linePts(ticks, (t) => t.cumulative_score_usd));
    customer.setData(linePts(ticks, (t) => t.cumulative_customer_bill_usd));
    socChart.timeScale().fitContent();
    socApi.current = { chart: socChart, soc, company, head: sHead };

    return () => {
      power.remove();
      socChart.remove();
      powerApi.current = null;
      socApi.current = null;
    };
  }, [ticks]);

  useEffect(() => {
    const p = powerApi.current;
    const s = socApi.current;
    const tick = ticks[index];
    if (!p || !s || !tick) {
      return;
    }
    p.head.setData(headPts(ticks, index));
    s.head.setData(headPts(ticks, index));
    const t = ts(tick.time_unix);
    p.chart.setCrosshairPosition(tick.fleet_w, t, p.fleet);
    s.chart.setCrosshairPosition(tick.mean_soc, t, s.soc);
  }, [index, ticks]);

  return (
    <div className="charts">
      <div className="chart-label">power · price</div>
      <div className="chart-pane" ref={powerEl} />
      <div className="chart-label">SOC · company $ · customer $</div>
      <div className="chart-pane" ref={socEl} />
    </div>
  );
}
