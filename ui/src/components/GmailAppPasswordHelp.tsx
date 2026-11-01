import { ExternalLink, KeyRound, X } from "lucide-react";
import { useState } from "react";

import { openGmailAppPasswordPage } from "@/lib/tauri";

export function GmailAppPasswordHelp() {
  const [open, setOpen] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const openGoogleSettings = async () => {
    setError(null);
    try {
      await openGmailAppPasswordPage();
    } catch (openError) {
      setError(openError instanceof Error ? openError.message : String(openError));
    }
  };

  return (
    <>
      <button
        type="button"
        className="text-left text-xs font-semibold text-brand-700 underline decoration-brand-300 underline-offset-2 hover:text-brand-900"
        onClick={() => setOpen(true)}
      >
        How do I get a Gmail app password?
      </button>
      {open ? (
        <div
          className="fixed inset-0 z-[100] flex items-center justify-center bg-[#0f1535]/55 px-4 py-8"
          role="presentation"
          onMouseDown={(event) => {
            if (event.target === event.currentTarget) setOpen(false);
          }}
        >
          <section
            aria-labelledby="gmail-app-password-title"
            aria-modal="true"
            className="max-h-full w-full max-w-xl overflow-y-auto rounded-3xl bg-white p-6 shadow-2xl sm:p-8"
            role="dialog"
          >
            <div className="flex items-start justify-between gap-4">
              <div className="flex items-start gap-3">
                <span className="rounded-2xl bg-brand-600/10 p-3 text-brand-700">
                  <KeyRound className="h-5 w-5" />
                </span>
                <div>
                  <h2 id="gmail-app-password-title" className="text-xl font-bold text-horizon-text">
                    Get a Gmail app password
                  </h2>
                  <p className="mt-1 text-sm leading-6 text-horizon-muted">
                    An app password lets this app send mail without asking for your normal Google password.
                  </p>
                </div>
              </div>
              <button
                type="button"
                aria-label="Close app password help"
                className="rounded-xl p-2 text-horizon-muted hover:bg-horizon-background hover:text-horizon-text"
                onClick={() => setOpen(false)}
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            <ol className="mt-6 list-decimal space-y-3 pl-5 text-sm leading-6 text-horizon-text marker:font-bold marker:text-brand-700">
              <li>Sign in to Google with the Gmail account you want the app to send from.</li>
              <li>Turn on 2-Step Verification in your Google Account security settings.</li>
              <li>Open App Passwords, sign in again if Google asks, and create one for this app.</li>
              <li>Copy the 16-character password and paste it into the Gmail App Password field.</li>
            </ol>
            <p className="mt-5 rounded-2xl border border-horizon-warning/20 bg-horizon-warning/10 p-4 text-xs leading-5 text-horizon-text">
              Never enter your normal Google password here. If Google does not show App Passwords,
              your account type, administrator, or security settings may not allow them.
            </p>
            {error ? (
              <p role="alert" className="mt-4 text-sm text-horizon-danger">{error}</p>
            ) : null}
            <div className="mt-6 flex flex-wrap gap-3">
              <button
                type="button"
                className="action-button action-button-primary"
                onClick={() => void openGoogleSettings()}
              >
                <ExternalLink className="h-4 w-4" />
                Open Google App Passwords
              </button>
              <button
                type="button"
                className="action-button action-button-secondary"
                onClick={() => setOpen(false)}
              >
                Close guide
              </button>
            </div>
          </section>
        </div>
      ) : null}
    </>
  );
}
