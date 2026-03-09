import type { StatsResponse } from "../types";


interface StatsBarProps {
  stats: StatsResponse | null;
}

export function StatsBar({ stats }: StatsBarProps) {
  return (
    <section className="stats-bar">
      <div className="stat-card">
        <span className="label">全量职位</span>
        <strong>{stats?.raw_jobs ?? "-"}</strong>
      </div>
      <div className="stat-card">
        <span className="label">通过筛选</span>
        <strong>{stats?.filtered_jobs ?? "-"}</strong>
      </div>
      <div className="stat-card">
        <span className="label">已忽略</span>
        <strong>{stats?.dismissed_jobs ?? "-"}</strong>
      </div>
      <div className="stat-card">
        <span className="label">最近任务状态</span>
        <strong>{stats?.latest_sync_status ?? "-"}</strong>
      </div>
    </section>
  );
}
