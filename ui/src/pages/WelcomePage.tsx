import { BriefcaseBusiness, FileText, Mail, ShieldCheck } from "lucide-react";
import { useState, type FormEvent, type ReactNode } from "react";

import { GmailAppPasswordHelp } from "@/components/GmailAppPasswordHelp";
import type { AppConfig } from "@/lib/types";

interface WelcomePageProps {
  config: AppConfig;
  saving: boolean;
  error: string | null;
  onComplete: (config: AppConfig) => Promise<void>;
}

export function WelcomePage({ config, saving, error, onComplete }: WelcomePageProps) {
  const [name, setName] = useState(config.mailer.your_name);
  const [email, setEmail] = useState(config.mailer.contact_info.email);
  const [senderEmail, setSenderEmail] = useState(config.mailer.auth.sender_email);
  const [appPassword, setAppPassword] = useState(config.mailer.auth.app_password);
  const [formError, setFormError] = useState("");

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!name.trim() || !email.trim() || !senderEmail.trim() || !appPassword.trim()) {
      setFormError("Enter your name, contact email, Gmail address, and Gmail app password to continue.");
      return;
    }

    setFormError("");
    await onComplete({
      ...config,
      mailer: {
        ...config.mailer,
        your_name: name.trim(),
        auth: {
          ...config.mailer.auth,
          sender_email: senderEmail.trim(),
          app_password: appPassword.trim(),
        },
        contact_info: {
          ...config.mailer.contact_info,
          email: email.trim(),
        },
      },
      app: { ...config.app, onboarding_completed: true },
    });
  };

  return (
    <main className="flex h-screen items-center justify-center overflow-y-auto bg-horizon-background px-5 py-10">
      <section className="w-full max-w-5xl overflow-hidden rounded-[30px] border border-white bg-white shadow-horizon">
        <div className="grid lg:grid-cols-[1fr_0.88fr]">
          <div className="p-7 sm:p-10 lg:p-12">
            <div className="mb-9 flex items-center gap-3">
              <span className="flex h-12 w-12 items-center justify-center rounded-2xl bg-gradient-to-br from-brand-600 to-horizon-info font-bold text-white">
                TJ
              </span>
              <div>
                <p className="font-bold text-horizon-text">TopJobs Mailer</p>
                <p className="text-xs text-horizon-muted">First-time setup</p>
              </div>
            </div>

            <h1 className="text-3xl font-bold tracking-tight text-horizon-text sm:text-4xl">
              Let&apos;s set up your workspace
            </h1>
            <p className="mt-3 max-w-xl text-sm leading-6 text-horizon-muted">
              Your profile and application settings stay on this computer. You can add resumes and
              create job-matching profiles from the Resume Profiles page after setup.
            </p>

            <form className="mt-8 space-y-5" onSubmit={(event) => void submit(event)}>
              <label className="block space-y-2">
                <span className="text-sm font-semibold text-horizon-text">Your name</span>
                <input
                  autoComplete="name"
                  className="input-base"
                  value={name}
                  onChange={(event) => setName(event.target.value)}
                  placeholder="Name used in application emails"
                  required
                />
              </label>

              <label className="block space-y-2">
                <span className="text-sm font-semibold text-horizon-text">Contact email</span>
                <input
                  autoComplete="email"
                  className="input-base"
                  type="email"
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                  placeholder="you@example.com"
                  required
                />
              </label>

              <div className="rounded-2xl border border-horizon-border bg-horizon-background p-4">
                <div className="mb-4 flex items-start gap-3">
                  <Mail className="mt-0.5 h-5 w-5 shrink-0 text-brand-600" />
                  <div>
                    <p className="text-sm font-semibold text-horizon-text">Gmail account</p>
                    <p className="mt-1 text-xs leading-5 text-horizon-muted">
                      This password is stored securely in your computer&apos;s credential store. It is not your normal Google password.
                    </p>
                  </div>
                </div>
                <div className="space-y-3">
                  <input
                    autoComplete="username"
                    className="input-base"
                    type="email"
                    value={senderEmail}
                    onChange={(event) => setSenderEmail(event.target.value)}
                    placeholder="Gmail address"
                    required
                  />
                  <input
                    autoComplete="new-password"
                    className="input-base"
                    type="password"
                    value={appPassword}
                    onChange={(event) => setAppPassword(event.target.value)}
                    placeholder="Gmail app password"
                    required
                  />
                  <GmailAppPasswordHelp />
                </div>
              </div>

              {formError ? (
                <p role="alert" className="text-sm font-medium text-horizon-danger">{formError}</p>
              ) : null}
              {error ? (
                <p role="alert" className="text-sm font-medium text-horizon-danger">{error}</p>
              ) : null}
              <button
                className="action-button action-button-primary w-full sm:w-auto"
                type="submit"
                disabled={saving}
              >
                {saving ? "Saving your workspace..." : "Continue to the app"}
              </button>
            </form>
          </div>

          <aside className="flex flex-col justify-between bg-gradient-to-br from-[#18245b] via-[#27387d] to-[#176a9b] p-7 text-white sm:p-10 lg:p-12">
            <div>
              <p className="text-xs font-bold uppercase tracking-[0.24em] text-white/65">Your setup</p>
              <h2 className="mt-4 text-2xl font-bold">A clean start, built around your profile.</h2>
              <div className="mt-9 space-y-6">
                <SetupStep icon={<ShieldCheck />} title="Private by default" text="Your profile and resume files are stored locally." />
                <SetupStep icon={<FileText />} title="Add your resume" text="Import a PDF and review the job profile suggested from it." />
                <SetupStep icon={<BriefcaseBusiness />} title="See your own analytics" text="Dashboard results appear as your job searches run—no demo activity." />
              </div>
            </div>
            <p className="mt-10 text-xs leading-5 text-white/60">
              You can edit your details, email connection, and job-search preferences in Settings at any time.
            </p>
          </aside>
        </div>
      </section>
    </main>
  );
}

function SetupStep({
  icon,
  title,
  text,
}: {
  icon: ReactNode;
  title: string;
  text: string;
}) {
  return (
    <div className="flex gap-4">
      <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-white/10 [&>svg]:h-5 [&>svg]:w-5">
        {icon}
      </span>
      <div>
        <p className="font-semibold">{title}</p>
        <p className="mt-1 text-sm leading-5 text-white/70">{text}</p>
      </div>
    </div>
  );
}
