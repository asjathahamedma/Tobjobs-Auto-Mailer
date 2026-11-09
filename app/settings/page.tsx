"use client";

import { ChangeEvent, FormEvent, useCallback, useEffect, useRef, useState } from "react";
import { BookOpen, CircleAlert, Eye, FileUp, LoaderCircle, Plus, Save, Sparkles, Trash2, X } from "lucide-react";
import { AppShell } from "@/components/AppShell";
import { api, apiBlob, jsonBody } from "@/lib/api";
import { Toast } from "@/components/Toast";

type Settings = {
  display_name: string;
  your_name: string;
  contact_email: string;
  phone: string;
  portfolio: string;
  linkedin: string;
  github: string;
  preferred_titles: string[];
  preferred_locations: string[];
  employment_preferences: string[];
  recent_job_window_days: number;
  minimum_fit_score: number;
  require_remote: boolean;
  enable_ocr_for_ad_images: boolean;
  auto_apply_enabled: boolean;
  enable_ai_features: boolean;
  ai_feature_toggles: Record<string, boolean>;
  category_urls: string[];
  selected_resume_id: string | null;
  mailer_configured: boolean;
};
type Resume = { id: string; file_name: string; label: string; summary: string; title_keywords: string[]; description_keywords: string[] };
type SettingsResponse = Settings & { profile: { display_name: string } };

const initial: Settings = {
  display_name: "", your_name: "", contact_email: "", phone: "", portfolio: "", linkedin: "", github: "",
  preferred_titles: [], preferred_locations: [], employment_preferences: [], recent_job_window_days: 2,
  minimum_fit_score: 4, require_remote: false, enable_ocr_for_ad_images: false,
  auto_apply_enabled: false, enable_ai_features: true,
  ai_feature_toggles: { resume_analysis: true, job_tuning: true, application_drafts: true },
  category_urls: ["https://www.topjobs.lk/applicant/vacancybyfunctionalarea.jsp?FA=HNS&jst=OPEN", "https://www.topjobs.lk/applicant/vacancybyfunctionalarea.jsp?FA=SDQ&jst=OPEN"],
  selected_resume_id: null, mailer_configured: false,
};
const split = (value: string) => value.split(",").map((part) => part.trim()).filter(Boolean);

export default function SettingsPage() {
  const [settings, setSettings] = useState<Settings>(initial);
  const [resumes, setResumes] = useState<Resume[]>([]);
  const [senderEmail, setSenderEmail] = useState("");
  const [appPassword, setAppPassword] = useState("");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [preview, setPreview] = useState<{ id: string; url: string } | null>(null);
  const uploadInput = useRef<HTMLInputElement>(null);

  useEffect(() => {
    return () => {
      if (preview) URL.revokeObjectURL(preview.url);
    };
  }, [preview]);

  const refresh = useCallback(async () => {
    try {
      const [saved, resumePage] = await Promise.all([
        api<SettingsResponse>("/api/settings"),
        api<Resume[]>("/api/resumes"),
      ]);
      const { mailer_configured, profile, ...stored } = saved;
      setSettings({ ...initial, ...stored, display_name: stored.display_name || profile.display_name, mailer_configured });
      setResumes(resumePage);
      setError("");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not load settings.");
    } finally {
      setLoading(false);
    }
  }, []);
  useEffect(() => { void refresh(); }, [refresh]);

  function setField<K extends keyof Settings>(key: K, value: Settings[K]) {
    setSettings((current) => ({ ...current, [key]: value }));
  }

  async function saveSettings() {
    setBusy("settings");
    setError("");
    try {
      const { mailer_configured: _mailer, ...payload } = settings;
      await api("/api/settings", { method: "PATCH", body: jsonBody(payload) });
      setNotice("Profile and search preferences saved.");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not save settings.");
    } finally {
      setBusy("");
    }
  }

  async function uploadResume(event: ChangeEvent<HTMLInputElement>) {
    const input = event.currentTarget;
    const files = Array.from(input.files || []);
    if (!files.length) return;
    setBusy("resume");
    setError("");
    const uploaded: Resume[] = [];
    const failures: string[] = [];
    try {
      for (const file of files) {
        const form = new FormData();
        form.append("file", file);
        try {
          uploaded.push(await api<Resume>("/api/resumes", { method: "POST", body: form }));
        } catch (reason) {
          failures.push(`${file.name}: ${reason instanceof Error ? reason.message : "Could not upload this file."}`);
        }
      }
      if (uploaded.length) {
        setResumes((current) => [...uploaded, ...current]);
        setSettings((current) => ({
          ...current,
          selected_resume_id: current.selected_resume_id || uploaded[0].id,
        }));
        setNotice(`Uploaded ${uploaded.length} resume${uploaded.length === 1 ? "" : "s"}.`);
      }
      if (failures.length) setError(`Could not upload ${failures.join(" ")}`);
      if (!uploaded.length && !failures.length) setError("No resumes were uploaded.");
    } finally {
      setBusy("");
      input.value = "";
    }
  }

  async function previewResume(id: string) {
    setBusy(`preview:${id}`);
    setError("");
    try {
      const blob = await apiBlob(`/api/resumes/${id}/file`);
      setPreview({ id, url: URL.createObjectURL(blob) });
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not preview this resume.");
    } finally {
      setBusy("");
    }
  }

  async function extractKeywords(id: string) {
    setBusy(`keywords:${id}`);
    setError("");
    try {
      const updated = await api<Resume>(`/api/resumes/${id}/extract-keywords`, { method: "POST" });
      setResumes((current) => current.map((resume) => resume.id === id ? updated : resume));
      setNotice(`Extracted ${updated.title_keywords.length + updated.description_keywords.length} keywords from ${updated.file_name}.`);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not extract resume keywords.");
    } finally {
      setBusy("");
    }
  }

  async function saveMailer(event: FormEvent) {
    event.preventDefault();
    setBusy("mailer");
    setError("");
    try {
      await api("/api/mailer-credentials", { method: "PUT", body: jsonBody({ sender_email: senderEmail, app_password: appPassword }) });
      setAppPassword("");
      setField("mailer_configured", true);
      setNotice("Gmail App Password saved securely.");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not save mailer details.");
    } finally {
      setBusy("");
    }
  }

  async function saveResume(id: string, changes: Partial<Resume>) {
    setBusy(`profile:${id}`);
    setError("");
    try {
      const saved = await api<Resume>(`/api/resumes/${id}`, {
        method: "PATCH",
        body: jsonBody(changes),
      });
      setResumes((current) => current.map((resume) => resume.id === id ? saved : resume));
      setNotice("Resume profile updated.");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not update resume profile.");
    } finally {
      setBusy("");
    }
  }

  async function deleteResume(resume: Resume) {
    if (!window.confirm(`Delete "${resume.label}" and its private PDF? Applications will be kept, but job matches will no longer link to this resume.`)) return;
    setBusy(`delete:${resume.id}`);
    setError("");
    try {
      const result = await api<{ selected_resume_id: string | null }>(`/api/resumes/${resume.id}`, { method: "DELETE" });
      setResumes((current) => current.filter((item) => item.id !== resume.id));
      setSettings((current) => ({ ...current, selected_resume_id: result.selected_resume_id }));
      setNotice(`Deleted ${resume.label}. Application history was preserved.`);
      if (preview?.id === resume.id) setPreview(null);
    } catch (reason) {
      const message = reason instanceof Error ? reason.message : "Could not delete this resume profile.";
      await refresh();
      setError(message);
    } finally {
      setBusy("");
    }
  }

  if (loading) return <AppShell><div className="loading-state">Loading settings…</div></AppShell>;

  return (
    <AppShell>
      <header className="page-header"><div><p className="eyebrow">PERSONALIZE YOUR SEARCH</p><h1>Settings and profile</h1><p className="muted">Your resume is stored in a private account folder and used to find relevant job listings.</p></div></header>
      {error && <div className="notice error"><CircleAlert size={18} />{error}</div>}
      <Toast message={notice} onDismiss={() => setNotice("")} />
      <div className="settings-layout">
        <section className="panel settings-section"><div className="section-heading"><div><h2>Resume profiles</h2><p className="muted">Upload a text-based PDF (up to 10 MB). Scanned images are not supported yet.</p></div><button className="button secondary" type="button" onClick={() => uploadInput.current?.click()} disabled={busy === "resume"}><Plus size={16} />Add profile</button></div>
          <input ref={uploadInput} className="resume-upload-input" type="file" accept="application/pdf,.pdf" multiple onChange={uploadResume} disabled={busy === "resume"} />
          {busy === "resume" && <p className="muted">Uploading and analyzing selected resume files…</p>}
          {resumes.length > 0 && <label>Profile used for matching<select value={settings.selected_resume_id || ""} onChange={(event) => setField("selected_resume_id", event.target.value || null)}>{resumes.map((resume) => <option key={resume.id} value={resume.id}>{resume.label}</option>)}</select></label>}
          {resumes.map((resume) => <div className="resume-profile-editor" key={resume.id}>
            <div className="resume-row"><FileUp size={17} /><div><strong>{resume.label}</strong><small>{resume.file_name}</small></div><span>{busy === `profile:${resume.id}` ? "Saving…" : "Edit inferred profile"}</span></div>
            <div className="resume-actions">
              <button className="button secondary" type="button" onClick={() => void previewResume(resume.id)} disabled={busy === `preview:${resume.id}`}>
                {busy === `preview:${resume.id}` ? <LoaderCircle className="spin" size={16} /> : <Eye size={16} />}Preview
              </button>
              <button className="button secondary" type="button" onClick={() => void extractKeywords(resume.id)} disabled={busy === `keywords:${resume.id}`}>
                {busy === `keywords:${resume.id}` ? <LoaderCircle className="spin" size={16} /> : <Sparkles size={16} />}Extract keywords
              </button>
              <button className="button danger" type="button" onClick={() => void deleteResume(resume)} disabled={busy === `delete:${resume.id}`}>
                {busy === `delete:${resume.id}` ? <LoaderCircle className="spin" size={16} /> : <Trash2 size={16} />}Delete profile
              </button>
            </div>
            <label>Profile name<input defaultValue={resume.label} onBlur={(event) => { if (event.target.value !== resume.label) void saveResume(resume.id, { label: event.target.value }); }} /></label>
            <label>Profile summary<textarea rows={2} defaultValue={resume.summary} onBlur={(event) => { if (event.target.value !== resume.summary) void saveResume(resume.id, { summary: event.target.value }); }} /></label>
            <label>Title keywords <small>Comma-separated; used to compare job titles</small><input defaultValue={resume.title_keywords.join(", ")} onBlur={(event) => { if (event.target.value !== resume.title_keywords.join(", ")) void saveResume(resume.id, { title_keywords: split(event.target.value) }); }} /></label>
            <label>Description keywords <small>Comma-separated; used to compare advert text</small><input defaultValue={resume.description_keywords.join(", ")} onBlur={(event) => { if (event.target.value !== resume.description_keywords.join(", ")) void saveResume(resume.id, { description_keywords: split(event.target.value) }); }} /></label>
          </div>)}
        </section>
        {preview && <div className="resume-preview-backdrop" onMouseDown={(event) => { if (event.target === event.currentTarget) setPreview(null); }}>
          <section className="resume-preview-dialog" role="dialog" aria-modal="true" aria-label="Resume preview">
            <div className="resume-preview-heading"><h2>{resumes.find((resume) => resume.id === preview.id)?.file_name || "Resume preview"}</h2><button className="button secondary" type="button" onClick={() => setPreview(null)} aria-label="Close resume preview"><X size={17} /></button></div>
            <iframe title="Private resume PDF preview" src={preview.url} />
          </section>
        </div>}
        <section className="panel settings-section"><h2>Contact details</h2><p className="muted">Used to prepare your professional application drafts.</p><div className="form-grid">
          <label>Display name<input value={settings.display_name} onChange={(event) => setField("display_name", event.target.value)} /></label>
          <label>Name for applications<input value={settings.your_name} onChange={(event) => setField("your_name", event.target.value)} /></label>
          <label>Contact email<input type="email" value={settings.contact_email} onChange={(event) => setField("contact_email", event.target.value)} /></label>
          <label>Phone<input value={settings.phone} onChange={(event) => setField("phone", event.target.value)} /></label>
          <label>LinkedIn URL<input value={settings.linkedin} onChange={(event) => setField("linkedin", event.target.value)} /></label>
          <label>GitHub URL<input value={settings.github} onChange={(event) => setField("github", event.target.value)} /></label>
          <label>Portfolio URL<input value={settings.portfolio} onChange={(event) => setField("portfolio", event.target.value)} /></label>
        </div></section>
        <section className="panel settings-section"><h2>Job matching preferences</h2><p className="muted">Fit scores are weighted keyword points and should be reviewed, not treated as hiring predictions.</p><div className="form-grid">
          <label>Preferred job titles <small>Comma-separated</small><input value={settings.preferred_titles.join(", ")} onChange={(event) => setField("preferred_titles", split(event.target.value))} placeholder="Software Engineer, QA Analyst" /></label>
          <label>Preferred locations <small>Comma-separated</small><input value={settings.preferred_locations.join(", ")} onChange={(event) => setField("preferred_locations", split(event.target.value))} placeholder="Colombo, Remote" /></label>
          <label>Recent job window<select value={settings.recent_job_window_days} onChange={(event) => setField("recent_job_window_days", Number(event.target.value))}><option value={1}>Last day</option><option value={2}>Last 2 days</option><option value={7}>Last 7 days</option><option value={14}>Last 14 days</option><option value={30}>Last 30 days</option></select></label>
          <label>Minimum fit points<input type="number" min={0} max={100} value={settings.minimum_fit_score} onChange={(event) => setField("minimum_fit_score", Number(event.target.value))} /></label>
        </div>
          <label className="check-label"><input type="checkbox" checked={settings.require_remote} onChange={(event) => setField("require_remote", event.target.checked)} />Only include roles explicitly marked remote</label>
          <label className="check-label"><input type="checkbox" checked={settings.enable_ocr_for_ad_images} onChange={(event) => setField("enable_ocr_for_ad_images", event.target.checked)} />Enable OCR for image-based job adverts (slower)</label>
          <div className="auto-apply-option">
            <label className="check-label"><input type="checkbox" checked={settings.auto_apply_enabled} onChange={(event) => setField("auto_apply_enabled", event.target.checked)} />Automatically email applications for new matching jobs</label>
            <p className="muted">When enabled, the app sends a generated email with the matched resume to a valid listing email address for each newly discovered job that passes your current matching filters. This sends without per-job review and does not submit website forms. It is off by default, requires a saved Gmail App Password and resume, and will not automatically retry failed or uncertain sends. Review your profile, resume, and Gmail settings before enabling.</p>
          </div>
        </section>
        <section className="panel settings-section"><h2>AI settings</h2><p className="muted">The AI layer reads provider keys from server-side environment variables only and redacts contact details before every prompt.</p>
          <label className="check-label"><input type="checkbox" checked={settings.enable_ai_features} onChange={(event) => setField("enable_ai_features", event.target.checked)} />Enable AI features</label>
          <div className="form-grid">
            {Object.entries(settings.ai_feature_toggles).map(([feature, enabled]) => (
              <label className="check-label" key={feature}>
                <input type="checkbox" checked={enabled} onChange={(event) => setSettings((current) => ({
                  ...current,
                  ai_feature_toggles: { ...current.ai_feature_toggles, [feature]: event.target.checked },
                }))} />{feature.replace(/_/g, " ")}
              </label>
            ))}
          </div>
          <div className="progress-card" style={{ marginTop: "1rem" }}>
            <div className="row-between"><strong>Today&apos;s AI usage</strong><span>Groq / Gemini</span></div>
            <p className="muted">Usage is tracked per provider and the UI shows the currently configured per-provider daily budgets and minute limits.</p>
            <div className="match-keywords"><span>Groq: 0 / 200k tokens</span><span>Gemini: 0 / 500k tokens</span></div>
          </div>
        </section>
        <section className="panel settings-section"><h2>TopJobs categories</h2><p className="muted">One HTTPS TopJobs applicant category URL per line.</p><label>Category URLs<textarea rows={4} value={settings.category_urls.join("\n")} onChange={(event) => setField("category_urls", event.target.value.split("\n").map((item) => item.trim()).filter(Boolean))} /></label></section>
        <section className="panel settings-section"><div className="section-heading"><div><h2>Gmail sending</h2><p className="muted">{settings.mailer_configured ? "An App Password is saved. It is never displayed here." : "Connect Gmail with an App Password; your normal Gmail password is not accepted."}</p></div><BookOpen size={20} /></div>
          <ol className="help-steps"><li>Enable 2-Step Verification on your Google Account.</li><li>Open <a href="https://myaccount.google.com/apppasswords" target="_blank" rel="noreferrer">Google App Passwords</a> and create one for this app.</li><li>Paste the 16-character password below. Google only shows it once.</li></ol>
          <form onSubmit={saveMailer} className="form-grid mailer-form"><label>Gmail address<input required type="email" value={senderEmail} onChange={(event) => setSenderEmail(event.target.value)} placeholder="you@gmail.com" /></label><label>Gmail App Password<input required minLength={8} type="password" autoComplete="new-password" value={appPassword} onChange={(event) => setAppPassword(event.target.value)} placeholder={settings.mailer_configured ? "Enter a new password to replace it" : "16-character App Password"} /></label><button className="button secondary" type="submit" disabled={busy === "mailer"}>{busy === "mailer" ? <LoaderCircle className="spin" size={16} /> : <Save size={16} />}Save Gmail details</button></form>
        </section>
        <button className="button primary save-settings" type="button" onClick={() => void saveSettings()} disabled={busy === "settings"}>{busy === "settings" ? <LoaderCircle className="spin" size={17} /> : <Save size={17} />}Save profile and preferences</button>
      </div>
    </AppShell>
  );
}
