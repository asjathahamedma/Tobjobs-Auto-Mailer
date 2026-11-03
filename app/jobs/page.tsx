"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import { ExternalLink, Search } from "lucide-react";
import { AppShell } from "@/components/AppShell";
import { api } from "@/lib/api";

type Job = {
  id: string;
  match_score: number;
  match_explanation: string;
  matched_title_keywords: string[];
  matched_description_keywords: string[];
  status: string;
  resumes: { id: string; label: string; file_name: string } | null;
  job_listings: {
    title: string;
    company: string | null;
    location: string | null;
    description: string;
    source_url: string;
    posted_at: string | null;
  };
};
type Page<T> = { items: T[] };

export default function JobsPage() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [query, setQuery] = useState("");
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const result = await api<Page<Job>>(`/api/jobs?page_size=100${search ? `&search=${encodeURIComponent(search)}` : ""}`);
      setJobs(result.items);
      setError("");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not load jobs.");
    } finally {
      setLoading(false);
    }
  }, [search]);
  useEffect(() => { void load(); }, [load]);

  function submit(event: FormEvent) {
    event.preventDefault();
    setSearch(query.trim());
  }

  return (
    <AppShell>
      <header className="page-header">
        <div><p className="eyebrow">OPPORTUNITIES</p><h1>Matched jobs</h1><p className="muted">Fit scores are raw points from your resume keywords, not a probability of getting hired.</p></div>
      </header>
      <form className="search-bar" onSubmit={submit}><Search size={18} /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search role titles" aria-label="Search role titles" /><button className="button secondary" type="submit">Search</button></form>
      {error && <div className="notice error">{error}</div>}
      {loading ? <div className="loading-state">Loading matched jobs…</div> : jobs.length === 0 ? <div className="panel empty-state"><Search size={26} /><strong>No matched jobs yet</strong><p>Run a search from the overview after adding a resume profile.</p></div> : (
        <div className="job-grid">
          {jobs.map((job) => {
            const listing = job.job_listings;
            return <article className="job-card" key={job.id}>
              <div className="row-between"><span className="score-pill">{job.match_score} <small>points</small></span><span className={`badge ${job.status}`}>{job.status.replaceAll("_", " ")}</span></div>
              <h2>{listing.title}</h2><p className="muted">{listing.company || "Company not listed"}{listing.location ? ` · ${listing.location}` : ""}</p>
              <section className="match-reason"><strong>Why it matched</strong><p>{job.match_explanation || "This job met your resume and job-search matching criteria."}</p>{job.resumes && <small>Matched profile: {job.resumes.label}</small>}</section>
              <div className="match-keywords">
                {job.matched_title_keywords.length > 0 && <div><small>Title keywords</small><div className="keyword-list">{job.matched_title_keywords.map((keyword) => <span key={`title-${keyword}`}>{keyword}</span>)}</div></div>}
                {job.matched_description_keywords.length > 0 && <div><small>Skills and description keywords</small><div className="keyword-list">{job.matched_description_keywords.map((keyword) => <span key={`description-${keyword}`}>{keyword}</span>)}</div></div>}
              </div>
              <details className="job-details">
                <summary>Full job description and details</summary>
                <p>{listing.description || "The listing did not provide a readable job description."}</p>
              </details>
              <a className="inline-link job-source" href={listing.source_url} target="_blank" rel="noreferrer">View original listing <ExternalLink size={15} /></a>
            </article>;
          })}
        </div>
      )}
    </AppShell>
  );
}
