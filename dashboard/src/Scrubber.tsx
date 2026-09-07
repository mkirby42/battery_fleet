import type { Bookmark } from "./playback";

type Props = {
  nTicks: number;
  index: number;
  playing: boolean;
  setIndex: (i: number) => void;
  toggle: () => void;
  pause: () => void;
  bookmarks: Bookmark[];
};

type Chapter = { index: number; label: string };

function chapters(marks: Bookmark[]): Chapter[] {
  const byIndex = new Map<number, string[]>();
  for (const mark of marks) {
    const labels = byIndex.get(mark.index) ?? [];
    labels.push(mark.label);
    byIndex.set(mark.index, labels);
  }
  return [...byIndex.entries()].map(([i, labels]) => ({
    index: i,
    label: labels.join(" · "),
  }));
}

export default function Scrubber({
  nTicks,
  index,
  playing,
  setIndex,
  toggle,
  pause,
  bookmarks: marks,
}: Props) {
  const max = Math.max(0, nTicks - 1);
  const marksOnTrack = chapters(marks);

  return (
    <div className="scrubber">
      <button
        type="button"
        className={`scrub-play${playing ? " is-on" : ""}`}
        onClick={toggle}
        aria-label={playing ? "Pause" : "Play"}
      >
        {playing ? "PAUSE" : "PLAY"}
      </button>
      <div className="scrub-track">
        <input
          className="scrub-range"
          type="range"
          min={0}
          max={max}
          step={1}
          value={index}
          onChange={(e) => setIndex(Number(e.target.value))}
          aria-label="Tick"
        />
        <div className="scrub-marks">
          {marksOnTrack.map((mark) => {
            const t = max === 0 ? 0 : mark.index / max;
            return (
              <button
                key={mark.label}
                type="button"
                className={`scrub-mark${index === mark.index ? " is-on" : ""}`}
                style={{ left: `${t * 100}%` }}
                onClick={() => {
                  setIndex(mark.index);
                  pause();
                }}
                aria-label={`${mark.label}, tick ${mark.index + 1}`}
              >
                <span className="scrub-mark-gem" />
                <span className="scrub-mark-label">{mark.label}</span>
              </button>
            );
          })}
        </div>
      </div>
      <span className="scrub-pos">
        {nTicks === 0 ? "0 / 0" : `${index + 1} / ${nTicks}`}
      </span>
    </div>
  );
}
