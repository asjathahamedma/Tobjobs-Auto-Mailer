# TopJobs Auto Mailer — Web

A web-only job-search workspace for TopJobs.lk. It uses Next.js for the website, Supabase for sign-in and private user data, and a separate FastAPI service for scraping and Gmail SMTP. The search is started manually; the app does not submit website applications or send email without your explicit review and approval.

## What is included

- Email/password registration and sign-in using Supabase Auth; no Google OAuth.
- User-scoped settings, private PDF resume storage, and RLS-protected job, search, and application records.
- TopJobs.lk category and advert scraping with existing weighted keyword matching.
- Dashboard with recent runs, matched jobs, and a match rate based on jobs reviewed in the most recent 1,000 runs. A fit score is raw points, not a hiring probability.
- Editable email and cover-letter drafts; the resume is attached only after checking the explicit approval box and choosing **Send approved email**.
- Gmail App Password encryption on the API server using Fernet. The password is never returned to the browser or written to application logs.
- Vercel frontend and Render Docker API deployment configuration.

PDFs must contain extractable text; scanned-image resume OCR is not provided. Job discovery is limited to TopJobs.lk. SMTP acceptance is recorded as **Gmail accepted**, not proof of delivery or employer receipt. Search work runs inside the API process, so a host restart can interrupt a run; see [hosting limitations](#hosting-limitations).

## Run locally

### 1. Create Supabase resources

1. Create a Supabase project.
2. In the Supabase SQL Editor, run `supabase/migrations/202611010001_initial_web_schema.sql` (or use the Supabase CLI to link the project and run `supabase db push`).
3. In **Authentication → URL Configuration**, set the local site URL to `http://localhost:3000` and allow `http://localhost:3000/auth/callback`. For production, add the deployed Vercel origin and its `/auth/callback` URL.
4. Copy the project URL, anon/publishable key, and service-role key from the project API settings. The service-role key is for the API server only.

### 2. Configure environment variables

Copy `.env.example` to `.env.local` for Next.js and to `.env` for FastAPI, then fill in the values locally:

```text
NEXT_PUBLIC_SUPABASE_URL=https://YOUR_PROJECT.supabase.co
NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY=YOUR_PUBLISHABLE_KEY
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
SUPABASE_URL=https://YOUR_PROJECT.supabase.co
SUPABASE_ANON_KEY=YOUR_PUBLISHABLE_OR_ANON_KEY
SUPABASE_SERVICE_ROLE_KEY=YOUR_SERVER_ONLY_SERVICE_ROLE_KEY
APP_CREDENTIALS_ENCRYPTION_KEY=YOUR_FERNET_KEY
WEB_ALLOWED_ORIGINS=http://localhost:3000
```

Generate a Fernet key locally; keep it private and do not change it after saving Gmail credentials unless you are prepared to re-enter them:

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Never put the service-role key or encryption key in a `NEXT_PUBLIC_` variable, the repository, or a chat message.

### 3. Install and start

In one terminal:

```bash
npm ci
npm run dev
```

In another terminal, from the repository root:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r web_backend/requirements.txt
python -m uvicorn web_backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```

On Windows, activate the virtual environment with `.venv\Scripts\activate` in PowerShell instead. Open `http://localhost:3000`, register, upload a resume, save your search preferences, and run a search.

## Host publicly

There is no production deployment configured by this repository yet. Create the provider resources with your own accounts and add secrets through their dashboards; do not commit them.

### Supabase

Apply the SQL migration, configure the production auth redirect URL, and use the same project URL and anon key in both frontend and API settings. The `SUPABASE_SERVICE_ROLE_KEY` must only be configured on the API service. Keep the private `private-resumes` bucket and RLS policies from the migration enabled.

### FastAPI on Render

1. Connect the GitHub repository to Render and create a Blueprint from `render.yaml`.
2. Set `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`, and `APP_CREDENTIALS_ENCRYPTION_KEY` in the API service's Environment settings.
3. After the Vercel site is created, set `WEB_ALLOWED_ORIGINS` to its exact HTTPS origin, for example `https://your-site.vercel.app` (no trailing slash).
4. Deploy and verify `https://YOUR_API_HOST/health` returns `{"status":"ok"}`.

### Next.js on Vercel

1. Import the same repository into Vercel; use the repository root as the project root and the default Next.js build settings.
2. Set `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY` (or the legacy `NEXT_PUBLIC_SUPABASE_ANON_KEY`), and `NEXT_PUBLIC_API_BASE_URL` to the Supabase project and deployed API URLs.
3. Deploy, add the final Vercel HTTPS origin to Render's `WEB_ALLOWED_ORIGINS`, and add `https://YOUR_VERCEL_HOST/auth/callback` to Supabase's allowed redirect URLs.
4. Redeploy the API after changing its CORS origin, then test sign-up, confirmation, sign-in, resume upload, search, and email review/send.

After connecting both services to the repository, pushes to the configured production branch trigger Vercel and Render deployments. Visitors see the latest version after its build completes; there is no installer or desktop updater.

Do not host the scraper as a Vercel serverless function: scraping may take longer than a serverless execution limit. Vercel serves the UI; FastAPI handles the Python work.

## Hosting limitations

The included search runner uses FastAPI in-process background tasks and persists progress/results incrementally. This is suitable for trying the personal workflow on a small service, but it is **not a durable task queue**: a container restart can interrupt an active run. Render's free service can sleep after inactivity; browser polling keeps the API active during ordinary searches but does not protect against a restart. For reliable long searches, use an always-on API/worker host or add a durable queue before relying on unattended execution. The app does not scan continuously.

Confirm TopJobs.lk's applicable terms and rate limits before using the scraper. The parser can also need maintenance if the site changes. Free provider plans, quotas, sleep behavior, and availability can change; public hosting is not guaranteed to remain free.

## Gmail App Password

In Settings, follow the in-app guide: enable Google 2-Step Verification, create a Gmail App Password at [Google App Passwords](https://myaccount.google.com/apppasswords), and save it with the sender address. A normal Gmail password is not accepted. The API encrypts the saved App Password; Google SMTP must still accept the sign-in. Each email is sent only after the user checks the approval box. The attached resume is the private PDF selected for that job match.

## Data and migration from the old desktop app

The web project uses a new Supabase account and database; it does not read or import the desktop app's local account, keyring, JSON, CSV, SQLite, or logs. Create a web account, upload your resume PDF, and re-enter your Gmail App Password. Keep a backup of any local desktop data you still need. No local desktop data directory was available in the repository to migrate or verify.

The old desktop installer releases on GitHub are external assets and were not deleted. They should only be retired after the hosted site is deployed, tested, and any local-data migration decision is complete. Publishing a Git commit by itself will not update an already installed desktop app.

## Development checks

```bash
npm run typecheck
npm run build
npm audit
python -m unittest discover -s web_backend/tests -p 'test_*.py' -v
```

The historical audit and migration notes are in [`docs/`](./docs/).
