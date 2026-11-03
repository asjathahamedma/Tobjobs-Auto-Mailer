"use client";

import { useCallback, useEffect, useState } from "react";
import { Check, CircleAlert, FileText, LoaderCircle, MailCheck, WandSparkles } from "lucide-react";
import { AppShell } from "@/components/AppShell";
import { api, jsonBody } from "@/lib/api";

type Application = {
  id: string;
  status: string;
  updated_at: string;
  generated_subject: string;
  generated_email: string;
  cover_letter: string;
  notes: string;
  last_error: string;
  job_listings: { title: string; company: string | null; company_email: string | null; source_url: string };
};
type Page<T> = { items: T[] };

export default function ApplicationsPage() {
  const [items, setItems] = useState<Application[]>([]);
  const [approvals, setApprovals] = useState<Record<string, boolean>>({});
  const [busy, setBusy] = useState<Record<string, string>>({});
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const refresh = useCallback(async () => {
    try {
      const result = await api<Page<Application>>("/api/applications?page_size=100");
      setItems(result.items);
      setError("");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not load applications.");
    }
  }, []);
  useEffect(() => { void refresh(); }, [refresh]);

  async function generate(item: Application) {
    setBusy((current) => ({ ...current, [item.id]: "generate" }));
    setError("");
    try {
      await api(`/api/applications/${item.id}/generate-content`, { method: "POST" });
      setNotice("Draft generated. Review and edit every field before sending.");
      await refresh();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not generate the draft.");
    } finally {
      setBusy((current) => ({ ...current, [item.id]: "" }));
    }
  }

  async function save(item: Application, values: Partial<Application>) {
    setBusy((current) => ({ ...current, [item.id]: "save" }));
    setError("");
    try {
      await api(`/api/applications/${item.id}`, { method: "PATCH", body: jsonBody(values) });
      setNotice("Your edits have been saved.");
      await refresh();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not save your edits.");
    } finally {
      setBusy((current) => ({ ...current, [item.id]: "" }));
    }
  }

  async function send(item: Application) {
    if (!approvals[item.id]) return;
    setBusy((current) => ({ ...current, [item.id]: "send" }));
    setError("");
    setNotice("");
    try {
      await api(`/api/applications/${item.id}/send`, { method: "POST", body: jsonBody({ approved: true }) });
      setNotice("Gmail accepted the message. This does not confirm delivery to the employer.");
      await refresh();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not send this email.");
    } finally {
      setBusy((current) => ({ ...current, [item.id]: "" }));
    }
  }

  return (
    <AppShell>
      <header className="page-header"><div><p className="eyebrow">APPLICATION PIPELINE</p><h1>Review applications</h1><p className="muted">Draft emails and cover letters are editable. Sending always requires your explicit approval.</p></div></header>
      {error && <div className="notice error"><CircleAlert size={18} />{error}</div>}
      {notice && <div className="notice success"><Check size={18} />{notice}</div>}
      {items.length === 0 ? <div className="panel empty-state"><FileText size={28} /><strong>No applications to review</strong><p>Run a job search to create review drafts for matching roles.</p></div> : <div className="application-list">
        {items.map((item) => <article className="panel application-card" key={item.id}>
          <div className="section-heading"><div><span className={`badge ${item.status}`}>{item.status.replaceAll("_", " ")}</span><h2>{item.job_listings.title}</h2><p className="muted">{item.job_listings.company || "Company not listed"}</p><p className="muted">Application email: {item.job_listings.company_email || "No email address found"}</p></div><a className="inline-link" target="_blank" rel="noreferrer" href={item.job_listings.source_url}>Original listing ↗</a></div>
          {item.last_error && <div className="notice error">{item.last_error}</div>}
          {!item.generated_email ? <button className="button secondary" disabled={Boolean(busy[item.id])} onClick={() => generate(item)}>{busy[item.id] === "generate" ? <LoaderCircle className="spin" size={16} /> : <WandSparkles size={16} />}Generate email and cover letter</button> : <>
            <label>Email subject<input key={`${item.id}-subject-${item.updated_at}`} defaultValue={item.generated_subject} onBlur={(event) => { if (event.target.value !== item.generated_subject) void save(item, { generated_subject: event.target.value }); }} /></label>
            <label>Application email<textarea key={`${item.id}-email-${item.updated_at}`} rows={8} defaultValue={item.generated_email} onBlur={(event) => { if (event.target.value !== item.generated_email) void save(item, { generated_email: event.target.value }); }} /></label>
            <label>Cover letter<textarea key={`${item.id}-letter-${item.updated_at}`} rows={9} defaultValue={item.cover_letter} onBlur={(event) => { if (event.target.value !== item.cover_letter) void save(item, { cover_letter: event.target.value }); }} /></label>
            <p className="muted">The cover letter is a separate editable draft; this email sends the email text and attaches your selected resume PDF.</p>
            <label>Private notes<textarea key={`${item.id}-notes-${item.updated_at}`} rows={2} defaultValue={item.notes || ""} onBlur={(event) => { if (event.target.value !== (item.notes || "")) void save(item, { notes: event.target.value }); }} /></label>
            {item.status === "sending" && <div className="notice"><CircleAlert size={18} />Email submission is in progress or its result is uncertain. Check Gmail Sent before taking further action; sending is locked to avoid a duplicate.</div>}
            {["awaiting_review", "ready_to_apply", "failed"].includes(item.status) && <div className="approval-row"><label className="check-label"><input type="checkbox" checked={Boolean(approvals[item.id])} onChange={(event) => setApprovals((current) => ({ ...current, [item.id]: event.target.checked }))} />I reviewed this email and cover letter, confirmed the recipient, and approve sending it with my resume attached.</label><button className="button primary" disabled={!approvals[item.id] || Boolean(busy[item.id])} onClick={() => send(item)}>{busy[item.id] === "send" ? <LoaderCircle className="spin" size={16} /> : <MailCheck size={16} />}Send approved email</button></div>}
            {item.status === "applied" && <p className="muted"><Check size={15} /> Gmail accepted the email. Delivery is not confirmed.</p>}
          </>}
        </article>)}
      </div>}
    </AppShell>
  );
}
