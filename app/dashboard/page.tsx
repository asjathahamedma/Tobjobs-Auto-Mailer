"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { Activity, ArrowRight, BriefcaseBusiness, CheckCircle2, CircleAlert, LoaderCircle, Search } from "lucide-react";
import { AppShell } from "@/components/AppShell";
import { api, jsonBody } from "@/lib/api";

type Run = {
  id: string;
  status: string;
  jobs_found: number;
  progress: { matched?: number; jobs_reviewed?: number; detail?: string; percent?: number };
  created_at: string;
};
type Page<T> = { items: T[] };
type Analytics = {
  matched_jobs: number;
  applications: number;
  sent_applications: number;
  match_rate_recent_runs: number;
};

function dateLabel(value: string) {
  return new Date(value).toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" });
}

export default function DashboardPage() {
  const [runs, setRuns] = useState<Run[]>([]);
  const [matchedCount, setMatchedCount] = useState(0);
  const [applicationCount, setApplicationCount] = useState(0);
  const [sentCount, setSentCount] = useState(0);
  const [matchRate, setMatchRate] = useState(0);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const refresh = useCallback(async () => {
    try {
      const [runPage, analytics] = await Promise.all([
        api<Page<Run>>("/api/search-runs?page_size=20"),
        api<Analytics>("/api/analytics"),
      ]);
      setRuns(runPage.items);
      setMatchedCount(analytics.matched_jobs);
      setApplicationCount(analytics.applications);
      setSentCount(analytics.sent_applications);
      setMatchRate(analytics.match_rate_recent_runs);
      setError("");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not load dashboard.");
    }
  }, []);

  useEffect(() => { void refresh(); }, [refresh]);
  const isRunning = useMemo(() => runs.some((run) => ["queued", "running"].includes(run.status)), [runs]);
  useEffect(() => {
    if (!isRunning) return;
    const timer = window.setInterval(() => { void refresh(); }, 4000);
    return () => window.clearInterval(timer);
  }, [isRunning, refresh]);

  async function startSearch() {
    setBusy(true);
    setError("");
    try {
      await api("/api/search-runs", { method: "POST", body: jsonBody({}) });
      await refresh();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not start search.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <AppShell>
      <header className="page-header">
        <div><p className="eyebrow">YOUR WORKSPACE</p><h1>Job search overview</h1><p className="muted">Find relevant opportunities and review every application before sending.</p></div>
        <button className="button primary" onClick={startSearch} disabled={busy || isRunning}>
          {busy || isRunning ? <LoaderCircle className="spin" size={17} /> : <Search size={17} />}
          {isRunning ? "Search running" : busy ? "Starting…" : "Run job search"}
        </button>
      </header>
      {error && <div className="notice error"><CircleAlert size={18} />{error}</div>}
      <section className="stat-grid" aria-label="Job search analytics">
        <article className="stat-card"><span className="stat-icon blue"><Activity size={19} /></span><span className="stat-label">Search runs</span><strong>{runs.length}</strong><small>Recent activity</small></article>
        <article className="stat-card"><span className="stat-icon purple"><BriefcaseBusiness size={19} /></span><span className="stat-label">Matched jobs</span><strong>{matchedCount}</strong><small>Across recent runs</small></article>
        <article className="stat-card"><span className="stat-icon green"><CheckCircle2 size={19} /></span><span className="stat-label">Match rate</span><strong>{matchRate}%</strong><small>Matched / reviewed jobs</small></article>
        <article className="stat-card"><span className="stat-icon amber"><CheckCircle2 size={19} /></span><span className="stat-label">Applications</span><strong>{applicationCount}</strong><small>{sentCount} sent according to run history</small></article>
      </section>
      {isRunning && <div className="progress-card"><div className="row-between"><strong>Searching TopJobs.lk</strong><span>{runs.find((run) => ["queued", "running"].includes(run.status))?.progress?.percent ?? 0}%</span></div><p className="muted">{runs.find((run) => ["queued", "running"].includes(run.status))?.progress?.detail || "Loading results…"}</p><div className="progress-track"><span style={{ width: `${runs.find((run) => ["queued", "running"].includes(run.status))?.progress?.percent ?? 0}%` }} /></div></div>}
      <section className="panel">
        <div className="section-heading"><div><h2>Recent search runs</h2><p className="muted">Searches are manual; no background job applications are submitted.</p></div><Link className="inline-link" href="/jobs">View matched jobs <ArrowRight size={15} /></Link></div>
        {runs.length === 0 ? <div className="empty-state"><Search size={25} /><strong>Your workspace is ready</strong><p>Upload a resume and set your preferences to start finding relevant roles.</p><Link className="button secondary" href="/settings">Set up your profile</Link></div> : <div className="table-wrap"><table><thead><tr><th>Started</th><th>Status</th><th>Jobs reviewed</th><th>Matches</th></tr></thead><tbody>{runs.slice(0, 8).map((run) => <tr key={run.id}><td>{dateLabel(run.created_at)}</td><td><span className={`badge ${run.status}`}>{run.status.replaceAll("_", " ")}</span></td><td>{run.progress?.jobs_reviewed ?? run.jobs_found}</td><td>{run.progress?.matched ?? "—"}</td></tr>)}</tbody></table></div>}
      </section>
    </AppShell>
  );
}
