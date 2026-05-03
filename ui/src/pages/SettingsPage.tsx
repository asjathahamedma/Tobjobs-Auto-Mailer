import { MailCheck, ShieldCheck } from "lucide-react";

import type { AppConfig } from "@/lib/types";
import { parseMultiline, toMultiline } from "@/lib/utils";

interface SettingsPageProps {
  config: AppConfig | null;
  onConfigChange: (config: AppConfig) => void;
}

export function SettingsPage({ config, onConfigChange }: SettingsPageProps) {
  if (!config) {
    return <div className="panel p-6 text-sm text-horizon-muted">Loading settings...</div>;
  }

  const updateConfig = (updater: (current: AppConfig) => AppConfig) => {
    onConfigChange(updater(config));
  };

  return (
    <div className="grid gap-6 xl:grid-cols-[0.9fr_1.1fr]">
      <section className="panel overflow-hidden">
        <div className="panel-header">
          <div>
            <h3 className="text-lg font-bold text-horizon-text">Automation</h3>
            <p className="text-sm text-horizon-muted">Launch, startup, and job scanning behavior.</p>
          </div>
        </div>
        <div className="panel-body space-y-5">
          <CheckboxField
            label="Run automatically at Windows startup"
            checked={config.app.run_at_startup}
            onChange={(checked) =>
              updateConfig((current) => ({
                ...current,
                app: { ...current.app, run_at_startup: checked },
              }))
            }
          />
          <CheckboxField
            label="Start automation when the app opens"
            checked={config.app.auto_run_on_launch}
            onChange={(checked) =>
              updateConfig((current) => ({
                ...current,
                app: { ...current.app, auto_run_on_launch: checked },
              }))
            }
          />
          <CheckboxField
            label="Start minimized"
            checked={config.app.start_minimized}
            onChange={(checked) =>
              updateConfig((current) => ({
                ...current,
                app: { ...current.app, start_minimized: checked },
              }))
            }
          />
          <CheckboxField
            label="Scan only mode"
            checked={config.app.scan_only_mode}
            onChange={(checked) =>
              updateConfig((current) => ({
                ...current,
                app: { ...current.app, scan_only_mode: checked },
              }))
            }
          />
          <CheckboxField
            label="Remote jobs only"
            checked={config.scraper.require_remote}
            onChange={(checked) =>
              updateConfig((current) => ({
                ...current,
                scraper: { ...current.scraper, require_remote: checked },
              }))
            }
          />
          <NumberField
            label="Minimum fit score"
            value={config.scraper.minimum_fit_score}
            onChange={(value) =>
              updateConfig((current) => ({
                ...current,
                scraper: { ...current.scraper, minimum_fit_score: value },
              }))
            }
          />
          <NumberField
            label="Recent job window (days)"
            value={config.scraper.recent_job_window_days}
            onChange={(value) =>
              updateConfig((current) => ({
                ...current,
                scraper: { ...current.scraper, recent_job_window_days: value },
              }))
            }
          />
          <NumberField
            label="Startup delay (seconds)"
            value={config.app.startup_delay_seconds}
            onChange={(value) =>
              updateConfig((current) => ({
                ...current,
                app: { ...current.app, startup_delay_seconds: value },
              }))
            }
          />
        </div>
      </section>

      <div className="space-y-6">
        <section className="panel overflow-hidden">
          <div className="panel-header">
            <div>
              <h3 className="text-lg font-bold text-horizon-text">Email Connection</h3>
              <p className="text-sm text-horizon-muted">Current sender access and the public release path.</p>
            </div>
          </div>
          <div className="panel-body grid gap-4 md:grid-cols-2">
            <div className="rounded-2xl border border-horizon-border bg-horizon-background px-4 py-4">
              <div className="mb-3 flex items-center gap-3">
                <div className="rounded-xl bg-horizon-success/10 p-3 text-horizon-success">
                  <MailCheck className="h-5 w-5" />
                </div>
                <div>
                  <p className="font-semibold text-horizon-text">Gmail App Password</p>
                  <p className="text-xs text-horizon-muted">Active for this local build</p>
                </div>
              </div>
              <p className="text-sm text-horizon-muted">
                Uses the Gmail address and app password saved below.
              </p>
            </div>
            <div className="rounded-2xl border border-dashed border-brand-600/25 bg-brand-600/5 px-4 py-4">
              <div className="mb-3 flex items-center gap-3">
                <div className="rounded-xl bg-brand-600/10 p-3 text-brand-600">
                  <ShieldCheck className="h-5 w-5" />
                </div>
                <div>
                  <p className="font-semibold text-horizon-text">Google OAuth</p>
                  <p className="text-xs text-horizon-muted">Planned for public users</p>
                </div>
              </div>
              <button type="button" className="action-button action-button-secondary w-full" disabled>
                Connect with Google
              </button>
            </div>
          </div>
        </section>

        <section className="panel overflow-hidden">
          <div className="panel-header">
            <div>
              <h3 className="text-lg font-bold text-horizon-text">Contact and Search Settings</h3>
              <p className="text-sm text-horizon-muted">Sender details and TopJobs category URLs.</p>
            </div>
          </div>
          <div className="panel-body grid gap-5 xl:grid-cols-2">
            <TextField
              label="Full Name"
              value={config.mailer.your_name}
              onChange={(value) =>
                updateConfig((current) => ({
                  ...current,
                  mailer: { ...current.mailer, your_name: value },
                }))
              }
            />
            <TextField
              label="Gmail Address"
              value={config.mailer.auth.sender_email}
              onChange={(value) =>
                updateConfig((current) => ({
                  ...current,
                  mailer: {
                    ...current.mailer,
                    auth: { ...current.mailer.auth, sender_email: value },
                  },
                }))
              }
            />
            <TextField
              label="Gmail App Password"
              value={config.mailer.auth.app_password}
              type="password"
              onChange={(value) =>
                updateConfig((current) => ({
                  ...current,
                  mailer: {
                    ...current.mailer,
                    auth: { ...current.mailer.auth, app_password: value },
                  },
                }))
              }
            />
            <TextField
              label="Phone"
              value={config.mailer.contact_info.phone}
              onChange={(value) =>
                updateConfig((current) => ({
                  ...current,
                  mailer: {
                    ...current.mailer,
                    contact_info: { ...current.mailer.contact_info, phone: value },
                  },
                }))
              }
            />
            <TextField
              label="Email"
              value={config.mailer.contact_info.email}
              onChange={(value) =>
                updateConfig((current) => ({
                  ...current,
                  mailer: {
                    ...current.mailer,
                    contact_info: { ...current.mailer.contact_info, email: value },
                  },
                }))
              }
            />
            <TextField
              label="Portfolio"
              value={config.mailer.contact_info.portfolio}
              onChange={(value) =>
                updateConfig((current) => ({
                  ...current,
                  mailer: {
                    ...current.mailer,
                    contact_info: { ...current.mailer.contact_info, portfolio: value },
                  },
                }))
              }
            />
            <TextField
              label="LinkedIn"
              value={config.mailer.contact_info.linkedin}
              onChange={(value) =>
                updateConfig((current) => ({
                  ...current,
                  mailer: {
                    ...current.mailer,
                    contact_info: { ...current.mailer.contact_info, linkedin: value },
                  },
                }))
              }
            />
            <TextField
              label="GitHub"
              value={config.mailer.contact_info.github}
              onChange={(value) =>
                updateConfig((current) => ({
                  ...current,
                  mailer: {
                    ...current.mailer,
                    contact_info: { ...current.mailer.contact_info, github: value },
                  },
                }))
              }
            />
            <label className="space-y-2 xl:col-span-2">
              <span className="text-sm font-semibold text-horizon-text">Category URLs</span>
              <textarea
                className="textarea-base min-h-36"
                value={toMultiline(config.scraper.category_urls)}
                onChange={(event) =>
                  updateConfig((current) => ({
                    ...current,
                    scraper: {
                      ...current.scraper,
                      category_urls: parseMultiline(event.target.value),
                    },
                  }))
                }
              />
            </label>
          </div>
        </section>
      </div>
    </div>
  );
}

function CheckboxField({
  label,
  checked,
  onChange,
}: {
  label: string;
  checked: boolean;
  onChange: (value: boolean) => void;
}) {
  return (
    <label className="flex items-center justify-between rounded-2xl border border-horizon-border bg-horizon-background px-4 py-3">
      <span className="text-sm font-medium text-horizon-text">{label}</span>
      <input
        type="checkbox"
        className="h-4 w-4 rounded border-horizon-border text-brand-600 focus:ring-brand-300"
        checked={checked}
        onChange={(event) => onChange(event.target.checked)}
      />
    </label>
  );
}

function TextField({
  label,
  value,
  type = "text",
  onChange,
}: {
  label: string;
  value: string;
  type?: string;
  onChange: (value: string) => void;
}) {
  return (
    <label className="space-y-2">
      <span className="text-sm font-semibold text-horizon-text">{label}</span>
      <input
        type={type}
        className="input-base"
        value={value}
        onChange={(event) => onChange(event.target.value)}
      />
    </label>
  );
}

function NumberField({
  label,
  value,
  onChange,
}: {
  label: string;
  value: number;
  onChange: (value: number) => void;
}) {
  return (
    <label className="space-y-2">
      <span className="text-sm font-semibold text-horizon-text">{label}</span>
      <input
        type="number"
        className="input-base"
        value={value}
        onChange={(event) => onChange(Number(event.target.value || 0))}
      />
    </label>
  );
}
