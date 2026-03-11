import type { JobsResponse, StatsResponse, SyncRunItem, ViewType } from "./types";


const API_BASE =
  import.meta.env.VITE_API_BASE_URL ?? "https://backend-production-26a6b.up.railway.app/api";

export async function fetchJobs(view: ViewType): Promise<JobsResponse> {
  const res = await fetch(`${API_BASE}/jobs?view=${view}`);
  if (!res.ok) {
    throw new Error(`Failed to fetch jobs: ${res.status}`);
  }
  return res.json() as Promise<JobsResponse>;
}

export async function fetchStats(): Promise<StatsResponse> {
  const res = await fetch(`${API_BASE}/stats`);
  if (!res.ok) {
    throw new Error(`Failed to fetch stats: ${res.status}`);
  }
  return res.json() as Promise<StatsResponse>;
}

export async function dismissJob(jobId: number): Promise<void> {
  const res = await fetch(`${API_BASE}/jobs/${jobId}/dismiss`, {
    method: "POST",
  });
  if (!res.ok) {
    throw new Error(`Failed to dismiss job: ${res.status}`);
  }
}

export async function triggerSync(): Promise<number> {
  const res = await fetch(`${API_BASE}/jobs/sync`, {
    method: "POST",
  });
  if (!res.ok) {
    throw new Error(`Failed to trigger sync: ${res.status}`);
  }
  const payload = (await res.json()) as { sync_run_id: number };
  return payload.sync_run_id;
}

export async function fetchKeywords(): Promise<string[]> {
  const res = await fetch(`${API_BASE}/settings/keywords`);
  if (!res.ok) {
    throw new Error(`Failed to fetch keywords: ${res.status}`);
  }
  const payload = (await res.json()) as { keywords: string[] };
  return payload.keywords;
}

export async function saveKeywords(keywords: string[]): Promise<string[]> {
  const res = await fetch(`${API_BASE}/settings/keywords`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ keywords }),
  });
  if (!res.ok) {
    throw new Error(`Failed to save keywords: ${res.status}`);
  }
  const payload = (await res.json()) as { keywords: string[] };
  return payload.keywords;
}

export async function fetchSyncRun(syncRunId: number): Promise<SyncRunItem> {
  const res = await fetch(`${API_BASE}/sync-runs/${syncRunId}`);
  if (!res.ok) {
    throw new Error(`Failed to fetch sync run: ${res.status}`);
  }
  return (await res.json()) as SyncRunItem;
}
