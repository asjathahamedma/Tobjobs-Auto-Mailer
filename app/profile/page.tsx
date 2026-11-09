"use client";

import { useCallback, useEffect, useState } from "react";
import { Save, Sparkles } from "lucide-react";
import { AppShell } from "@/components/AppShell";
import { api, jsonBody } from "@/lib/api";

type Profile = {
  full_name: string;
  headline: string;
  summary: string;
  target_roles: string[];
  seniority_level: string;
  years_experience: number;
  domains: string[];
  preferred_locations: string[];
  remote_preference: boolean;
  daily_apply_cap: number;
  active: boolean;
  strengths: string[];
};

const emptyProfile: Profile = {
  full_name: "",
  headline: "",
  summary: "",
  target_roles: [],
  seniority_level: "mid",
  years_experience: 0,
  domains: [],
  preferred_locations: [],
  remote_preference: false,
  daily_apply_cap: 5,
  active: true,
  strengths: [],
};

function splitList(value: string) {
  return value.split(",").map((part) => part.trim()).filter(Boolean);
}

export default function ProfilePage() {
  const [profile, setProfile] = useState<Profile>(emptyProfile);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    try {
      const data = await api<Profile>("/api/profile");
      setProfile({ ...emptyProfile, ...data });
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
      const payload = {
        ...profile,
        target_roles: splitList(profile.target_roles.join(",")),
        domains: splitList(profile.domains.join(",")),
        preferred_locations: splitList(profile.preferred_locations.join(",")),
        strengths: splitList(profile.strengths.join(",")),
      };
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
              <select value={profile.seniority_level} onChange={(event) => update("seniority_level", event.target.value)} style={{ border: "1px solid #e7ebf1", borderRadius: 8, padding: "10px 12px" }}>
                <option value="intern/trainee">Intern / trainee</option>
                <option value="junior/entry">Junior / entry</option>
                <option value="mid">Mid</option>
                <option value="senior">Senior</option>
                <option value="lead/principal">Lead / principal</option>
                <option value="manager/director">Manager / director</option>
              </select>
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

          <div style={{ display: "grid", gridTemplateColumns: "repeat(3, minmax(0, 1fr))", gap: 16 }}>
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
    </AppShell>
  );
}
