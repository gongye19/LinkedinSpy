export type ViewType = "filtered" | "all" | "dismissed";

export interface JobItem {
  id: number;
  site: string;
  job_url: string;
  title: string;
  company?: string | null;
  location?: string | null;
  search_term?: string | null;
  date_posted?: string | null;
  filter_reason?: string | null;
  dismiss_reason?: string | null;
}

export interface JobsResponse {
  view: ViewType;
  items: JobItem[];
}

export interface StatsResponse {
  raw_jobs: number;
  filtered_jobs: number;
  dismissed_jobs: number;
  latest_sync_status: string | null;
  latest_sync_finished_at: string | null;
}

export interface SyncRunItem {
  id: number;
  status: string;
  attempt_count: number;
  jobs_fetched: number;
  jobs_inserted: number;
  jobs_evaluated: number;
  jobs_filtered: number;
  total_keywords: number;
  completed_keywords: number;
  current_stage?: string | null;
  current_keyword?: string | null;
  progress_message?: string | null;
  error_message?: string | null;
  started_at: string;
  finished_at?: string | null;
}
