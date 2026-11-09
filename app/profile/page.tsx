"use client";

import { useCallback, useEffect, useState } from "react";
import { Save, Sparkles } from "lucide-react";
import { AppShell } from "@/components/AppShell";
import { api, jsonBody } from "@/lib/api";

type Profile = {
  id?: string | null;
  full_name: string;
  headline: string;
  summary: string;
  target_roles: string[];
  include_keywords: string[];
  exclude_keywords: string[];
  seniority_level: string;
  years_experience: number;
  domains: string[];
  preferred_locations: string[];
  remote_preference: boolean;
  daily_apply_cap: number;
  min_match_score: number;
  active: boolean;
  strengths: string[];
};
type Education = {
  id: string;
  school: string;
  degree: string;
  field_of_study: string;
  start_year: number | null;
  end_year: number | null;
  notes: string;
};
type Experience = {
  id: string;
  company: string;
  role: string;
  start_date: string;
  end_date: string;
  summary: string;
  achievements: string[];
};

const emptyProfile: Profile = {
  full_name: "",
  headline: "",
  summary: "",
  target_roles: [],
  include_keywords: [],
  exclude_keywords: [],
  seniority_level: "unspecified",
  years_experience: 0,
  domains: [],
  preferred_locations: [],
  remote_preference: false,
  daily_apply_cap: 5,
  min_match_score: 4,
  active: true,
  strengths: [],
};

function splitList(value: string) {
  return value.split(",").map((part) => part.trim()).filter(Boolean);
}

export default function ProfilePage() {
  const [profile, setProfile] = useState<Profile>(emptyProfile);
  const [education, setEducation] = useState<Education[]>([]);
  const [experience, setExperience] = useState<Experience[]>([]);
  const [educationDraft, setEducationDraft] = useState({ school: "", degree: "", field_of_study: "", start_year: "", end_year: "", notes: "" });
  const [experienceDraft, setExperienceDraft] = useState({ company: "", role: "", start_date: "", end_date: "", summary: "", achievements: "" });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    try {
      const [data, educationData, experienceData] = await Promise.all([
        api<Profile>("/api/profile"),
        api<Education[]>("/api/education"),
        api<Experience[]>("/api/work-experience"),
      ]);
      setProfile({ ...emptyProfile, ...data });
      setEducation(educationData);
      setExperience(experienceData);
      setError("");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not load profile.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void load(); }, [load]);

  async function save() {
    setSaving(true);
    setError("");
    try {
      const payload = { ...profile };
      delete payload.id;
      Object.assign(payload, {
        target_roles: splitList(profile.target_roles.join(",")),
        include_keywords: splitList(profile.include_keywords.join(",")),
        exclude_keywords: splitList(profile.exclude_keywords.join(",")),
        domains: splitList(profile.domains.join(",")),
        preferred_locations: splitList(profile.preferred_locations.join(",")),
        strengths: splitList(profile.strengths.join(",")),
      });
      await api("/api/profile", { method: "PATCH", body: jsonBody(payload) });
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not save profile.");
    } finally {
      setSaving(false);
    }
  }

  const update = <K extends keyof Profile>(key: K, value: Profile[K]) => {
    setProfile((current) => ({ ...current, [key]: value }));
  };

  async function addEducation() {
    try {
      const saved = await api<Education>("/api/education", {
        method: "POST",
        body: jsonBody({
          ...educationDraft,
          start_year: educationDraft.start_year ? Number(educationDraft.start_year) : null,
          end_year: educationDraft.end_year ? Number(educationDraft.end_year) : null,
        }),
      });
      setEducation((current) => [saved, ...current]);
      setEducationDraft({ school: "", degree: "", field_of_study: "", start_year: "", end_year: "", notes: "" });
      setError("");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not save education.");
    }
  }

  async function removeEducation(id: string) {
    try {
      await api(`/api/education/${id}`, { method: "DELETE" });
      setEducation((current) => current.filter((entry) => entry.id !== id));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not delete education.");
    }
  }

  async function addExperience() {
    try {
      const saved = await api<Experience>("/api/work-experience", {
        method: "POST",
        body: jsonBody({
          ...experienceDraft,
          achievements: splitList(experienceDraft.achievements),
        }),
      });
      setExperience((current) => [saved, ...current]);
      setExperienceDraft({ company: "", role: "", start_date: "", end_date: "", summary: "", achievements: "" });
      setError("");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not save work experience.");
    }
  }

  async function removeExperience(id: string) {
    try {
      await api(`/api/work-experience/${id}`, { method: "DELETE" });
      setExperience((current) => current.filter((entry) => entry.id !== id));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not delete work experience.");
    }
  }

  if (loading) {
    return (
      <AppShell>
        <div className="loading-state">Loading your profile…</div>
      </AppShell>
    );
  }

  return (
    <AppShell>
      <header className="page-header">
        <div>
          <p className="eyebrow">PROFILE</p>
          <h1>FastApply profile</h1>
          <p className="muted">Keep your core story, target roles, and application preferences in one place.</p>
        </div>
        <button className="button primary" onClick={() => void save()} disabled={saving}>
          <Save size={17} />{saving ? "Saving…" : "Save profile"}
        </button>
      </header>
      {error && <div className="notice error">{error}</div>}
      <section className="panel">
        <div className="section-heading">
          <div>
            <h2>Candidate overview</h2>
            <p className="muted">This information powers shortlist explanations, tailoring prompts, and review suggestions.</p>
          </div>
          <div className="inline-link"><Sparkles size={15} />Profile ready</div>
        </div>
        <div style={{ display: "grid", gap: 18 }}>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(2, minmax(0, 1fr))", gap: 16 }}>
            <label style={{ display: "grid", gap: 7 }}>
              <span className="muted">Full name</span>
              <input value={profile.full_name} onChange={(event) => update("full_name", event.target.value)} style={{ border: "1px solid #e7ebf1", borderRadius: 8, padding: "10px 12px" }} />
            </label>
            <label style={{ display: "grid", gap: 7 }}>
              <span className="muted">Seniority level</span>
              <input value={profile.seniority_level} onChange={(event) => update("seniority_level", event.target.value)} placeholder="Enter your level, or leave unspecified" style={{ border: "1px solid #e7ebf1", borderRadius: 8, padding: "10px 12px" }} />
            </label>
          </div>

          <label style={{ display: "grid", gap: 7 }}>
            <span className="muted">Headline</span>
            <input value={profile.headline} onChange={(event) => update("headline", event.target.value)} style={{ border: "1px solid #e7ebf1", borderRadius: 8, padding: "10px 12px" }} />
          </label>

          <label style={{ display: "grid", gap: 7 }}>
            <span className="muted">Summary</span>
            <textarea value={profile.summary} onChange={(event) => update("summary", event.target.value)} rows={5} style={{ border: "1px solid #e7ebf1", borderRadius: 8, padding: "10px 12px", resize: "vertical" }} />
          </label>

          <div style={{ display: "grid", gridTemplateColumns: "repeat(2, minmax(0, 1fr))", gap: 16 }}>
            <label style={{ display: "grid", gap: 7 }}>
              <span className="muted">Target roles</span>
              <input value={profile.target_roles.join(", ")} onChange={(event) => update("target_roles", splitList(event.target.value))} style={{ border: "1px solid #e7ebf1", borderRadius: 8, padding: "10px 12px" }} />
            </label>
            <label style={{ display: "grid", gap: 7 }}>
              <span className="muted">Domains</span>
              <input value={profile.domains.join(", ")} onChange={(event) => update("domains", splitList(event.target.value))} style={{ border: "1px solid #e7ebf1", borderRadius: 8, padding: "10px 12px" }} />
            </label>
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(2, minmax(0, 1fr))", gap: 16 }}>
            <label style={{ display: "grid", gap: 7 }}>
              <span className="muted">Include keywords</span>
              <input value={profile.include_keywords.join(", ")} onChange={(event) => update("include_keywords", splitList(event.target.value))} style={{ border: "1px solid #e7ebf1", borderRadius: 8, padding: "10px 12px" }} />
            </label>
            <label style={{ display: "grid", gap: 7 }}>
              <span className="muted">Exclude title keywords</span>
              <input value={profile.exclude_keywords.join(", ")} onChange={(event) => update("exclude_keywords", splitList(event.target.value))} style={{ border: "1px solid #e7ebf1", borderRadius: 8, padding: "10px 12px" }} />
            </label>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "repeat(2, minmax(0, 1fr))", gap: 16 }}>
            <label style={{ display: "grid", gap: 7 }}>
              <span className="muted">Years of experience</span>
              <input type="number" min={0} max={60} value={profile.years_experience} onChange={(event) => update("years_experience", Number(event.target.value || 0))} style={{ border: "1px solid #e7ebf1", borderRadius: 8, padding: "10px 12px" }} />
            </label>
            <label style={{ display: "grid", gap: 7 }}>
              <span className="muted">Preferred locations</span>
              <input value={profile.preferred_locations.join(", ")} onChange={(event) => update("preferred_locations", splitList(event.target.value))} style={{ border: "1px solid #e7ebf1", borderRadius: 8, padding: "10px 12px" }} />
            </label>
            <label style={{ display: "grid", gap: 7 }}>
              <span className="muted">Daily apply cap</span>
              <input type="number" min={1} max={50} value={profile.daily_apply_cap} onChange={(event) => update("daily_apply_cap", Number(event.target.value || 1))} style={{ border: "1px solid #e7ebf1", borderRadius: 8, padding: "10px 12px" }} />
            </label>
            <label style={{ display: "grid", gap: 7 }}>
              <span className="muted">Minimum fit points</span>
              <input type="number" min={0} max={100} value={profile.min_match_score} onChange={(event) => update("min_match_score", Number(event.target.value || 0))} style={{ border: "1px solid #e7ebf1", borderRadius: 8, padding: "10px 12px" }} />
            </label>
          </div>

          <div style={{ display: "grid", gap: 7 }}>
            <span className="muted">Strengths</span>
            <input value={profile.strengths.join(", ")} onChange={(event) => update("strengths", splitList(event.target.value))} style={{ border: "1px solid #e7ebf1", borderRadius: 8, padding: "10px 12px" }} />
          </div>

          <label style={{ display: "flex", alignItems: "center", gap: 10, color: "#42516a" }}>
            <input type="checkbox" checked={profile.remote_preference} onChange={(event) => update("remote_preference", event.target.checked)} />
            Open to remote roles
          </label>
          <label style={{ display: "flex", alignItems: "center", gap: 10, color: "#42516a" }}>
            <input type="checkbox" checked={profile.active} onChange={(event) => update("active", event.target.checked)} />
            Active profile for job matching
          </label>
        </div>
      </section>
      <section className="panel" style={{ marginTop: 18 }}>
        <div className="section-heading">
          <div><h2>Education</h2><p className="muted">Add qualifications you want available for application tailoring.</p></div>
        </div>
        <div style={{ display: "grid", gap: 12, marginBottom: 18 }}>
          <input aria-label="School" placeholder="School or institution" value={educationDraft.school} onChange={(event) => setEducationDraft((current) => ({ ...current, school: event.target.value }))} style={{ border: "1px solid #e7ebf1", borderRadius: 8, padding: "10px 12px" }} />
          <div style={{ display: "grid", gridTemplateColumns: "repeat(2, minmax(0, 1fr))", gap: 12 }}>
            <input aria-label="Degree" placeholder="Degree" value={educationDraft.degree} onChange={(event) => setEducationDraft((current) => ({ ...current, degree: event.target.value }))} style={{ border: "1px solid #e7ebf1", borderRadius: 8, padding: "10px 12px" }} />
            <input aria-label="Field of study" placeholder="Field of study" value={educationDraft.field_of_study} onChange={(event) => setEducationDraft((current) => ({ ...current, field_of_study: event.target.value }))} style={{ border: "1px solid #e7ebf1", borderRadius: 8, padding: "10px 12px" }} />
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(2, minmax(0, 1fr))", gap: 12 }}>
            <input aria-label="Start year" type="number" placeholder="Start year" value={educationDraft.start_year} onChange={(event) => setEducationDraft((current) => ({ ...current, start_year: event.target.value }))} style={{ border: "1px solid #e7ebf1", borderRadius: 8, padding: "10px 12px" }} />
            <input aria-label="End year" type="number" placeholder="End year" value={educationDraft.end_year} onChange={(event) => setEducationDraft((current) => ({ ...current, end_year: event.target.value }))} style={{ border: "1px solid #e7ebf1", borderRadius: 8, padding: "10px 12px" }} />
          </div>
          <textarea aria-label="Education notes" placeholder="Notes" rows={2} value={educationDraft.notes} onChange={(event) => setEducationDraft((current) => ({ ...current, notes: event.target.value }))} style={{ border: "1px solid #e7ebf1", borderRadius: 8, padding: "10px 12px" }} />
          <button className="button secondary" onClick={() => void addEducation()} style={{ justifySelf: "start" }}>Add education</button>
        </div>
        {education.map((entry) => <div key={entry.id} className="row-between" style={{ borderTop: "1px solid #eef0f4", padding: "12px 0" }}>
          <div><strong>{entry.degree || entry.field_of_study || "Education"}</strong><p className="muted">{entry.school}{entry.start_year ? ` · ${entry.start_year}` : ""}{entry.end_year ? `–${entry.end_year}` : ""}</p></div>
          <button className="button secondary" onClick={() => void removeEducation(entry.id)}>Remove</button>
        </div>)}
      </section>
      <section className="panel" style={{ marginTop: 18 }}>
        <div className="section-heading">
          <div><h2>Work experience</h2><p className="muted">Keep role and achievement details grounded in your actual history.</p></div>
        </div>
        <div style={{ display: "grid", gap: 12, marginBottom: 18 }}>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(2, minmax(0, 1fr))", gap: 12 }}>
            <input aria-label="Company" placeholder="Company" value={experienceDraft.company} onChange={(event) => setExperienceDraft((current) => ({ ...current, company: event.target.value }))} style={{ border: "1px solid #e7ebf1", borderRadius: 8, padding: "10px 12px" }} />
            <input aria-label="Role" placeholder="Role" value={experienceDraft.role} onChange={(event) => setExperienceDraft((current) => ({ ...current, role: event.target.value }))} style={{ border: "1px solid #e7ebf1", borderRadius: 8, padding: "10px 12px" }} />
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(2, minmax(0, 1fr))", gap: 12 }}>
            <input aria-label="Start date" placeholder="Start date (e.g. 2022-01)" value={experienceDraft.start_date} onChange={(event) => setExperienceDraft((current) => ({ ...current, start_date: event.target.value }))} style={{ border: "1px solid #e7ebf1", borderRadius: 8, padding: "10px 12px" }} />
            <input aria-label="End date" placeholder="End date or Present" value={experienceDraft.end_date} onChange={(event) => setExperienceDraft((current) => ({ ...current, end_date: event.target.value }))} style={{ border: "1px solid #e7ebf1", borderRadius: 8, padding: "10px 12px" }} />
          </div>
          <textarea aria-label="Role summary" placeholder="Role summary" rows={3} value={experienceDraft.summary} onChange={(event) => setExperienceDraft((current) => ({ ...current, summary: event.target.value }))} style={{ border: "1px solid #e7ebf1", borderRadius: 8, padding: "10px 12px" }} />
          <input aria-label="Achievements" placeholder="Achievements, separated by commas" value={experienceDraft.achievements} onChange={(event) => setExperienceDraft((current) => ({ ...current, achievements: event.target.value }))} style={{ border: "1px solid #e7ebf1", borderRadius: 8, padding: "10px 12px" }} />
          <button className="button secondary" onClick={() => void addExperience()} style={{ justifySelf: "start" }}>Add work experience</button>
        </div>
        {experience.map((entry) => <div key={entry.id} className="row-between" style={{ borderTop: "1px solid #eef0f4", padding: "12px 0" }}>
          <div><strong>{entry.role}</strong><p className="muted">{entry.company} · {entry.start_date}{entry.end_date ? `–${entry.end_date}` : ""}</p><p className="muted">{entry.summary}</p></div>
          <button className="button secondary" onClick={() => void removeExperience(entry.id)}>Remove</button>
        </div>)}
      </section>
    </AppShell>
  );
}
