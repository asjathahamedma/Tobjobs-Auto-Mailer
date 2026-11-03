# Web Edition Migration Status

## Current state

The repository has been converted locally to a Next.js web application with a FastAPI scraper/API and Supabase migrations. Windows/Tauri source, installer scripts, desktop tests, and the release workflow were removed at the user's explicit request. This is a source-code change only: the web service has not been deployed, the Supabase migration has not been applied to a live project, and the old published GitHub releases have not been deleted.

The architecture audit and feature inventory document the previous desktop implementation as a historical baseline. The new app uses Supabase email/password sign-in, user-scoped RLS, private resume storage, TopJobs.lk search, reviewable application drafts, and Gmail App Password email sending.

## Components and deployment

- **Frontend:** Next.js App Router, TypeScript, Tailwind, Vercel-compatible.
- **Auth and persistence:** Supabase Auth/Postgres/Storage; migration is in `supabase/migrations/`.
- **Python service:** FastAPI and the existing TopJobs parser/matcher; Docker deployment definition is `web_backend/Dockerfile`.
- **Hosting blueprint:** `render.yaml` describes the API service. Set every provider secret in the hosting dashboard, never in Git.
- **Mailer credential:** encrypted at rest with a backend-only Fernet key; rotating that key requires re-entering saved Gmail App Passwords.

The API persists search-run state and results incrementally, but the current runner uses in-process FastAPI background tasks, not a durable queue. A service restart can interrupt a run. Free hosting sleep/limits can also affect longer searches; use an always-on API/worker or add a durable queue before relying on long runs. Scraping is manually started, not continuous.

## Implemented code

- First-run email/password account flow and protected workspace pages.
- Profile/settings persistence and text-based PDF resume upload/private storage.
- TopJobs category URL validation, real scraper parsing, user-profile keyword matching, run progress, and persisted matched listings.
- Dashboard analytics, matched jobs view, editable email/cover-letter drafts, resume attachment, and an explicit send-approval checkbox.
- Backend authorization through Supabase Auth bearer tokens and RLS; server-only service role is limited in code to shared job-listing writes.
- Unit tests for settings validation, resume keyword extraction, content drafting, token forwarding, and the search adapter.
- Local setup/deployment instructions in the repository README.

## Known gaps and verification gates

- No legacy desktop JSON/CSV/SQLite/keyring importer was implemented. Existing data remains on the old machine; keep a backup, upload resumes to the web app, and re-enter the Gmail App Password.
- No live Supabase project, Render service, or Vercel project was provided. Database migrations, provider environment variables, auth redirects, CORS, private file access, and cross-device behavior remain to be verified after deployment.
- The production Next.js build and Python unit tests must pass before hosting. The live scraper also needs a real TopJobs run and terms/rate-limit review.
- SMTP success means Gmail accepted the email, not that the employer received or read it. If a connection fails after transmission, verify Gmail Sent before retrying.
- Scanned-image resume OCR is unsupported. Optional job-ad OCR requires EasyOCR to be installed on the API host; the default is off.

## Desktop retirement

The local desktop source and release workflow are removed as requested, before deployment verification. Published GitHub releases and assets are external GitHub resources and remain untouched; retire them only after the web app and data needs are verified. No GitHub releases, tags, or repository settings were changed.
