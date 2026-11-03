"use client";

import { FormEvent, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { createClient } from "@/lib/supabase/browser";

export function AuthForm() {
  const router = useRouter();
  const search = useSearchParams();
  const [signup, setSignup] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setMessage("");
    try {
      const supabase = createClient();
      const result = signup
        ? await supabase.auth.signUp({
            email,
            password,
            options: { emailRedirectTo: `${window.location.origin}/auth/callback` },
          })
        : await supabase.auth.signInWithPassword({ email, password });
      if (result.error) throw result.error;
      if (signup && !result.data.session) {
        setMessage("Check your email to confirm your account, then sign in.");
        setSignup(false);
        return;
      }
      router.replace(search.get("next") || "/dashboard");
      router.refresh();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Could not authenticate.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="auth-page">
      <form className="auth-card" onSubmit={submit}>
        <div className="brand-mark">TJ</div>
        <p className="eyebrow">TOPJOBS AUTO MAILER</p>
        <h1>{signup ? "Create your account" : "Welcome back"}</h1>
        <p className="muted">Securely manage your job search and application drafts.</p>
        <label>
          Email address
          <input required autoComplete="email" type="email" value={email} onChange={(event) => setEmail(event.target.value)} />
        </label>
        <label>
          Password
          <input required minLength={8} autoComplete={signup ? "new-password" : "current-password"} type="password" value={password} onChange={(event) => setPassword(event.target.value)} />
        </label>
        {message && <p className="notice" role="status">{message}</p>}
        <button className="button primary full" disabled={busy} type="submit">
          {busy ? "Please wait…" : signup ? "Create account" : "Sign in"}
        </button>
        <p className="auth-switch">
          {signup ? "Already registered?" : "New to TopJobs Auto Mailer?"}{" "}
          <button type="button" className="text-button" onClick={() => { setSignup(!signup); setMessage(""); }}>
            {signup ? "Sign in" : "Create account"}
          </button>
        </p>
      </form>
    </main>
  );
}
