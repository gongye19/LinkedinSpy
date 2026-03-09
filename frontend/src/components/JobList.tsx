import type { JobItem } from "../types";
import { JobCard } from "./JobCard";


interface JobListProps {
  jobs: JobItem[];
  onDismiss?: (jobId: number) => void;
}

export function JobList({ jobs, onDismiss }: JobListProps) {
  if (!jobs.length) {
    return <p className="empty">暂无职位数据</p>;
  }

  return (
    <section className="job-list">
      {jobs.map((job) => (
        <JobCard key={job.id} job={job} onDismiss={onDismiss} />
      ))}
    </section>
  );
}
