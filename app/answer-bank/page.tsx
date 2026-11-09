"use client";

import { useCallback, useEffect, useState } from "react";
import { Plus, Save } from "lucide-react";
import { AppShell } from "@/components/AppShell";
import { api, jsonBody } from "@/lib/api";

type AnswerEntry = {
  id: string;
  question: string;
  answer: string;
  tags: string[];
  is_default?: boolean;
};

const emptyEntry = { question: "", answer: "", tags: "" };

export default function AnswerBankPage() {
  const [entries, setEntries] = useState<AnswerEntry[]>([]);
  const [draft, setDraft] = useState(emptyEntry);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    try {
      const data = await api<AnswerEntry[]>("/api/answer-bank");
      setEntries(data);
      setError("");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not load answer bank.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void load(); }, [load]);

  async function saveEntry() {
    setSaving(true);
    setError("");
    try {
      const payload = {
        question: draft.question.trim(),
        answer: draft.answer.trim(),
        tags: draft.tags.split(",").map((tag) => tag.trim()).filter(Boolean),
      };
      if (!payload.question || !payload.answer) {
        throw new Error("Question and answer are required.");
      }
      const created = await api<AnswerEntry>("/api/answer-bank", { method: "POST", body: jsonBody(payload) });
      setEntries((current) => [created, ...current]);
      setDraft(emptyEntry);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not save answer.");
    } finally {
      setSaving(false);
    }
  }

  if (loading) {
    return (
      <AppShell>
        <div className="loading-state">Loading answer bank…</div>
      </AppShell>
    );
  }

  return (
    <AppShell>
      <header className="page-header">
        <div>
          <p className="eyebrow">ANSWER BANK</p>
          <h1>Reusable application answers</h1>
          <p className="muted">Store your strongest interview and introduction responses for faster, more consistent applications.</p>
        </div>
      </header>
      {error && <div className="notice error">{error}</div>}

      <section className="panel" style={{ marginBottom: 18 }}>
        <div className="section-heading">
          <div><h2>Add a new answer</h2></div>
        </div>
        <div style={{ display: "grid", gap: 14 }}>
          <label style={{ display: "grid", gap: 7 }}>
            <span className="muted">Question</span>
            <input value={draft.question} onChange={(event) => setDraft((current) => ({ ...current, question: event.target.value }))} style={{ border: "1px solid #e7ebf1", borderRadius: 8, padding: "10px 12px" }} />
          </label>
          <label style={{ display: "grid", gap: 7 }}>
            <span className="muted">Answer</span>
            <textarea rows={5} value={draft.answer} onChange={(event) => setDraft((current) => ({ ...current, answer: event.target.value }))} style={{ border: "1px solid #e7ebf1", borderRadius: 8, padding: "10px 12px", resize: "vertical" }} />
          </label>
          <label style={{ display: "grid", gap: 7 }}>
            <span className="muted">Tags (comma separated)</span>
            <input value={draft.tags} onChange={(event) => setDraft((current) => ({ ...current, tags: event.target.value }))} style={{ border: "1px solid #e7ebf1", borderRadius: 8, padding: "10px 12px" }} />
          </label>
          <button className="button primary" onClick={() => void saveEntry()} disabled={saving} style={{ justifySelf: "start" }}>
            <Plus size={17} />{saving ? "Saving…" : "Save answer"}
          </button>
        </div>
      </section>

      <section className="panel">
        <div className="section-heading">
          <div><h2>Stored responses</h2><p className="muted">Review and reuse your strongest answers before sending applications.</p></div>
        </div>
        {entries.length === 0 ? <div className="empty-state"><Save size={26} /><strong>No answers saved yet</strong><p>Add your intro, motivation, and role-fit responses here.</p></div> : (
          <div style={{ display: "grid", gap: 14 }}>
            {entries.map((entry) => (
              <article key={entry.id} className="panel" style={{ padding: 16, background: "#fafcff" }}>
                <div className="row-between" style={{ marginBottom: 10 }}>
                  <strong>{entry.question}</strong>
                  {entry.is_default && <span className="badge completed">default</span>}
                </div>
                <p style={{ margin: 0, color: "#4c5a71", lineHeight: 1.7 }}>{entry.answer}</p>
                {entry.tags.length > 0 && (
                  <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginTop: 12 }}>
                    {entry.tags.map((tag) => <span key={`${entry.id}-${tag}`} className="badge" style={{ background: "#edf2ff", color: "#4965be" }}>{tag}</span>)}
                  </div>
                )}
              </article>
            ))}
          </div>
        )}
      </section>
    </AppShell>
  );
}
