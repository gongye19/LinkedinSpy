import { useEffect, useMemo, useState } from "react";

import { dismissJob, fetchJobs, fetchKeywords, fetchStats, fetchSyncRun, saveKeywords, triggerSync } from "./api";
import { JobList } from "./components/JobList";
import { StatsBar } from "./components/StatsBar";
import type { JobItem, StatsResponse, SyncRunItem, ViewType } from "./types";


function App() {
  const [view, setView] = useState<ViewType>("filtered");
  const [jobs, setJobs] = useState<JobItem[]>([]);
  const [stats, setStats] = useState<StatsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [pendingDismissId, setPendingDismissId] = useState<number | null>(null);
  const [syncing, setSyncing] = useState(false);
  const [activeSyncRunId, setActiveSyncRunId] = useState<number | null>(null);
  const [syncProgress, setSyncProgress] = useState<SyncRunItem | null>(null);
  const [lastSyncSummary, setLastSyncSummary] = useState<string | null>(null);
  const [keywordInputs, setKeywordInputs] = useState<string[]>(["", "", "", ""]);
  const [savingKeywords, setSavingKeywords] = useState(false);
  const [isKeywordEditing, setIsKeywordEditing] = useState(false);

  useEffect(() => {
    let canceled = false;
    setLoading(true);
    setError(null);

    Promise.all([fetchJobs(view), fetchStats(), fetchKeywords()])
      .then(([jobsResp, statsResp, keywords]) => {
        if (canceled) return;
        setJobs(jobsResp.items);
        setStats(statsResp);
        const normalized = [...keywords];
        while (normalized.length < 4) normalized.push("");
        setKeywordInputs(normalized.slice(0, 4));
        setIsKeywordEditing(false);
      })
      .catch((err: Error) => {
        if (canceled) return;
        setError(err.message);
      })
      .finally(() => {
        if (canceled) return;
        setLoading(false);
      });

    return () => {
      canceled = true;
    };
  }, [view]);

  const title = useMemo(() => {
    if (view === "filtered") return "通过岗位";
    if (view === "dismissed") return "已忽略岗位";
    return "全部岗位";
  }, [view]);

  const stageLabel = useMemo(() => {
    if (!syncProgress) return "未开始";
    const stage = syncProgress.current_stage ?? syncProgress.status;
    if (stage === "scraping") return "爬取关键词中";
    if (stage === "llm_processing") return "大模型处理中";
    if (stage === "completed" || syncProgress.status === "success") return "已结束";
    if (stage === "error" || syncProgress.status === "failed") return "执行失败";
    if (stage === "queued") return "排队中";
    return "执行中";
  }, [syncProgress]);

  async function handleDismiss(jobId: number) {
    try {
      setPendingDismissId(jobId);
      await dismissJob(jobId);
      const [jobsResp, statsResp] = await Promise.all([fetchJobs(view), fetchStats()]);
      setJobs(jobsResp.items);
      setStats(statsResp);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setPendingDismissId(null);
    }
  }

  async function handleManualSync() {
    try {
      setSyncing(true);
      setError(null);
      const syncRunId = await triggerSync();
      setActiveSyncRunId(syncRunId);
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function handleSaveKeywords() {
    try {
      setSavingKeywords(true);
      setError(null);
      const prepared = keywordInputs.map((item) => item.trim()).filter(Boolean).slice(0, 4);
      const saved = await saveKeywords(prepared);
      const normalized = [...saved];
      while (normalized.length < 4) normalized.push("");
      setKeywordInputs(normalized.slice(0, 4));
      setIsKeywordEditing(false);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setSavingKeywords(false);
    }
  }

  function handleKeywordAction() {
    if (isKeywordEditing) {
      void handleSaveKeywords();
      return;
    }
    setIsKeywordEditing(true);
  }

  function updateKeywordAt(index: number, value: string) {
    setKeywordInputs((prev) => {
      const next = [...prev];
      next[index] = value;
      return next;
    });
  }

  useEffect(() => {
    if (!activeSyncRunId) return;
    let canceled = false;
    let timer: number | undefined;

    const poll = async () => {
      try {
        const run = await fetchSyncRun(activeSyncRunId);
        if (canceled) return;
        setSyncProgress(run);
        if (run.status === "success" || run.status === "failed") {
          setSyncing(false);
          const [jobsResp, statsResp] = await Promise.all([fetchJobs(view), fetchStats()]);
          if (canceled) return;
          setJobs(jobsResp.items);
          setStats(statsResp);
          if (run.status === "success") {
            setLastSyncSummary(
              `本轮已结束：抓取 ${run.jobs_fetched} 条，新增 ${run.jobs_inserted} 条，已刷新列表`,
            );
          } else {
            setLastSyncSummary(`本轮失败：${run.error_message ?? "未知错误"}`);
          }
          return;
        }
        timer = window.setTimeout(poll, 1500);
      } catch (err) {
        if (canceled) return;
        setSyncing(false);
        setError((err as Error).message);
      }
    };

    void poll();
    return () => {
      canceled = true;
      if (timer) window.clearTimeout(timer);
    };
  }, [activeSyncRunId, view]);

  return (
    <main className="container">
      <header>
        <h1>JobSpy 职位看板</h1>
        <p>每天 19:00 自动抓取并过滤职位</p>
      </header>

      <StatsBar stats={stats} />

      <section className="keyword-panel">
        <h2>爬取关键词设置（最多 4 个）</h2>
        <div className="keyword-grid">
          {keywordInputs.map((item, idx) => (
            <input
              key={`kw-${idx}`}
              value={item}
              onChange={(e) => updateKeywordAt(idx, e.target.value)}
              placeholder={`关键词 ${idx + 1}`}
              disabled={!isKeywordEditing}
            />
          ))}
        </div>
        <div className="keyword-actions">
          <button
            className={isKeywordEditing ? "btn btn-primary" : "btn btn-outline"}
            type="button"
            onClick={handleKeywordAction}
            disabled={savingKeywords}
          >
            {savingKeywords ? "保存中..." : isKeywordEditing ? "保存关键词" : "编辑关键词"}
          </button>
          {isKeywordEditing ? (
            <button className="btn btn-ghost" type="button" onClick={() => setIsKeywordEditing(false)} disabled={savingKeywords}>
              取消编辑
            </button>
          ) : null}
        </div>
        <p className="meta-note">保存后，手动爬取和每天 19:00 定时爬取都会默认使用这些关键词。</p>
        <div className="sync-cta-inline">
          <button className="sync-cta-btn" type="button" onClick={handleManualSync} disabled={syncing}>
            {syncing ? "正在爬取..." : "立即开始爬取"}
          </button>
        </div>
        {syncProgress ? (
          <div className="progress-card">
            <div className="progress-title">当前任务进度</div>
            <div className="progress-row">
              <span>阶段</span>
              <strong>{stageLabel}</strong>
            </div>
            <div className="progress-row">
              <span>关键词</span>
              <strong>{syncProgress.current_keyword ?? "-"}</strong>
            </div>
            <div className="progress-row">
              <span>关键词进度</span>
              <strong>
                {syncProgress.completed_keywords}/{syncProgress.total_keywords || 0}
              </strong>
            </div>
            <div className="progress-bar">
              <div
                className="progress-bar-inner"
                style={{
                  width:
                    syncProgress.total_keywords > 0
                      ? `${Math.min(100, (syncProgress.completed_keywords / syncProgress.total_keywords) * 100)}%`
                      : "0%",
                }}
              />
            </div>
            <p className="meta-note">{syncProgress.progress_message ?? "处理中..."}</p>
          </div>
        ) : null}
      </section>

      <section className="toolbar">
        <button
          className={view === "filtered" ? "active" : ""}
          onClick={() => setView("filtered")}
          type="button"
        >
          通过岗位
        </button>
        <button
          className={view === "all" ? "active" : ""}
          onClick={() => setView("all")}
          type="button"
        >
          全部岗位
        </button>
        <button
          className={view === "dismissed" ? "active" : ""}
          onClick={() => setView("dismissed")}
          type="button"
        >
          已忽略
        </button>
      </section>

      <h2>{title}</h2>
      {loading ? <p>加载中...</p> : null}
      {error ? <p className="error">{error}</p> : null}
      {lastSyncSummary ? <p className="sync-summary">{lastSyncSummary}</p> : null}
      {pendingDismissId ? <p>正在忽略职位 #{pendingDismissId} ...</p> : null}
      {!loading && !error ? (
        <JobList jobs={jobs} onDismiss={view === "filtered" ? handleDismiss : undefined} />
      ) : null}
    </main>
  );
}

export default App;
