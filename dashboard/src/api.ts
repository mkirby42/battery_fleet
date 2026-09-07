import type { Run, RunSummary } from "./types";

export async function listRuns(): Promise<RunSummary[]> {
  const res = await fetch("/api/runs");
  if (!res.ok) {
    throw new Error(`listRuns failed: ${res.status}`);
  }
  return (await res.json()) as RunSummary[];
}

export async function getRun(id: string): Promise<Run> {
  const res = await fetch(`/api/runs/${id}`);
  if (!res.ok) {
    throw new Error(`getRun failed: ${res.status}`);
  }
  return (await res.json()) as Run;
}
