import type { JobItem } from "../types";


interface JobCardProps {
  job: JobItem;
  onDismiss?: (jobId: number) => void;
}

export function JobCard({ job, onDismiss }: JobCardProps) {
  return (
    <article className="job-card">
      <h3>{job.title}</h3>
      <p>
        {job.company ?? "Unknown"} · {job.location ?? "Unknown"}
      </p>
      <p className="meta">
        发布日期：{job.date_posted ?? "Unknown date"}
      </p>
      {job.dismiss_reason ? <p className="reason">忽略原因: {job.dismiss_reason}</p> : null}
      <div className="job-actions">
        <a className="btn btn-primary" href={job.job_url} target="_blank" rel="noreferrer">
          查看职位
        </a>
        {onDismiss ? (
          <button className="btn btn-danger" type="button" onClick={() => onDismiss(job.id)}>
            Dismiss
          </button>
        ) : null}
      </div>
    </article>
  );
}
