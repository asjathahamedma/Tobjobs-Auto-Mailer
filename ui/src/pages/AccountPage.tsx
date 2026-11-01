import { LockKeyhole, ShieldCheck, UserRoundPlus } from "lucide-react";
import { useState, type FormEvent } from "react";

import type { AccountStatus } from "@/lib/types";

interface AccountPageProps {
  account: AccountStatus;
  busy: boolean;
  error: string | null;
  onAuthenticate: (mode: "register" | "login", email: string, password: string) => Promise<void>;
}

export function AccountPage({ account, busy, error, onAuthenticate }: AccountPageProps) {
  const [mode, setMode] = useState<"register" | "login">(account.registered ? "login" : "register");
  const [email, setEmail] = useState(account.email);
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [formError, setFormError] = useState("");
  const registering = mode === "register";

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (registering && password !== confirmPassword) {
      setFormError("The passwords do not match.");
      return;
    }
    if (registering && password.length < 10) {
      setFormError("Choose a password with at least 10 characters.");
      return;
    }
    setFormError("");
    await onAuthenticate(mode, email.trim(), password);
  };

  const switchMode = (nextMode: "register" | "login") => {
    setMode(nextMode);
    setPassword("");
    setConfirmPassword("");
    setFormError("");
  };

  return (
    <main className="flex h-screen items-center justify-center overflow-y-auto bg-horizon-background px-5 py-10">
      <section className="w-full max-w-md rounded-[28px] border border-white bg-white p-7 shadow-horizon sm:p-9">
        <div className="mb-8 flex items-center gap-3">
          <span className="flex h-12 w-12 items-center justify-center rounded-2xl bg-brand-600 text-white">
            {registering ? <UserRoundPlus className="h-6 w-6" /> : <LockKeyhole className="h-6 w-6" />}
          </span>
          <div>
            <p className="font-bold text-horizon-text">TopJobs Mailer</p>
            <p className="text-xs text-horizon-muted">{registering ? "Create your account" : "Welcome back"}</p>
          </div>
        </div>

        <h1 className="text-2xl font-bold tracking-tight text-horizon-text">
          {registering ? "Create your local account" : "Sign in to continue"}
        </h1>
        <p className="mt-2 text-sm leading-6 text-horizon-muted">
          This local sign-in is stored on this computer. After registration, enter your Gmail address
          and a separate Gmail app password in the first-run setup.
        </p>

        <form className="mt-7 space-y-4" onSubmit={(event) => void submit(event)}>
          <label className="block space-y-2">
            <span className="text-sm font-semibold text-horizon-text">Email</span>
            <input
              autoComplete="email"
              className="input-base"
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              required
            />
          </label>
          <label className="block space-y-2">
            <span className="text-sm font-semibold text-horizon-text">Password</span>
            <input
              autoComplete={registering ? "new-password" : "current-password"}
              className="input-base"
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              minLength={registering ? 10 : undefined}
              required
            />
          </label>
          {registering ? (
            <label className="block space-y-2">
              <span className="text-sm font-semibold text-horizon-text">Confirm password</span>
              <input
                autoComplete="new-password"
                className="input-base"
                type="password"
                value={confirmPassword}
                onChange={(event) => setConfirmPassword(event.target.value)}
                minLength={10}
                required
              />
            </label>
          ) : null}
          {formError || error ? (
            <p role="alert" className="text-sm font-medium text-horizon-danger">
              {formError || error}
            </p>
          ) : null}
          <button type="submit" className="action-button action-button-primary w-full" disabled={busy}>
            {busy ? "Please wait..." : registering ? "Create account" : "Sign in"}
          </button>
        </form>

        <div className="mt-6 flex items-start gap-3 rounded-2xl bg-horizon-background p-4">
          <ShieldCheck className="mt-0.5 h-5 w-5 shrink-0 text-brand-600" />
          <p className="text-xs leading-5 text-horizon-muted">
            Passwords are stored as salted, iterated hashes. Local account access is not cloud
            identity or encryption of files on this computer.
          </p>
        </div>

        <button
          type="button"
          className="mt-5 w-full text-sm font-semibold text-brand-700 hover:text-brand-900"
          onClick={() => switchMode(registering ? "login" : "register")}
        >
          {registering ? "Already registered? Sign in" : "New to this computer? Create an account"}
        </button>
      </section>
    </main>
  );
}
