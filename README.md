# TopJobs Auto Mailer — Web

A web-only job-search workspace for TopJobs.lk. It uses Next.js for the website, Supabase for sign-in and private user data, and a separate FastAPI service for scraping and Gmail SMTP. The search is started manually; the app does not submit website applications or send email without your explicit review and approval.

## What is included

- Email/password registration and sign-in using Supabase Auth; no Google OAuth.
- User-scoped settings, manageable private PDF resume profiles with authenticated preview and keyword extraction, and RLS-protected job, search, and application records.
- TopJobs.lk category and advert scraping with existing weighted keyword matching.
- Dashboard with recent runs, matched jobs, and a match rate based on jobs reviewed in the most recent 1,000 runs. A fit score is raw points, not a hiring probability.
- Editable email and cover-letter drafts; the resume is attached only after checking the explicit approval box and choosing **Send approved email**.
- Gmail App Password encryption on the API server using Fernet. The password is never returned to the browser or written to application logs.
- Next.js and FastAPI deployed together with Vercel Services, plus a Vercel Queues daemon for durable search work.

PDFs must contain extractable text; scanned-image resume OCR is not provided. Job discovery is limited to TopJobs.lk. SMTP acceptance is recorded as **Gmail accepted**, not proof of delivery or employer receipt. Production searches are queued and processed by a Vercel Daemon; queue delivery is retried if the worker exits.

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
SEARCH_QUEUE_BACKEND=local
VERCEL_QUEUE_REGION=iad1
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

## Deploy frontend, API, and worker on Vercel

The root `vercel.json` defines the Next.js frontend and FastAPI API as Vercel Services in one project. `/api/*` and `/health` route to FastAPI; other paths route to Next.js. The Python search worker runs as a Vercel Daemon and consumes durable Vercel Queue messages. Keep the Vercel project root set to the repository root.

The root `requirements.txt` contains only the FastAPI function's runtime dependencies so Vercel can optimize the Python bundle. The local backend and Docker worker use `web_backend/requirements.txt`; optional image OCR imports OpenCV and NumPy only when enabled.

In the existing Vercel project, configure these environment variables for **Production**:

| Variable | Purpose |
| --- | --- |
| `NEXT_PUBLIC_SUPABASE_URL` | Supabase project URL for browser authentication |
| `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY` | Supabase publishable key for browser authentication (legacy anon key is also accepted) |
| `SUPABASE_URL` | Supabase project URL for FastAPI and the worker |
| `SUPABASE_ANON_KEY` | Supabase publishable/anon key used by the API to validate sessions |
| `SUPABASE_SERVICE_ROLE_KEY` | Server-only API/worker access; never use a `NEXT_PUBLIC_` name |
| `APP_CREDENTIALS_ENCRYPTION_KEY` | Fernet key used to encrypt saved Gmail App Passwords |
| `WEB_ALLOWED_ORIGINS` | Your exact Vercel site origin, e.g. `https://your-site.vercel.app` |
| `SEARCH_QUEUE_BACKEND` | Set to `vercel` in Production to enqueue searches |
| `VERCEL_QUEUE_REGION` | Queue and daemon region; keep both on the same supported region (`iad1` by default) |

Do not set `NEXT_PUBLIC_API_BASE_URL` in Production: the frontend calls same-origin `/api/*` routes. Keep `NEXT_PUBLIC_API_BASE_URL=http://localhost:8000` in `.env.local` for local development. Set the Supabase production redirect URL to `https://YOUR_VERCEL_HOST/auth/callback`.

Vercel Queues and Daemons are currently beta features. Daemons run only for Production, not Preview deployments. Hobby includes 1,000,000 queue operations, but its daemon quotas are 5 active CPU-hours and 420 GB-hours of provisioned memory per month. This worker requests 1 GiB; its memory quota is therefore exhausted before a full month of continuous uptime. If the quota is reached, the worker pauses and queued messages can expire after seven days. Upgrade or monitor quotas before relying on uninterrupted job processing. Check the Vercel deployment logs and `https://YOUR_VERCEL_HOST/health` after deploying.

Vercel does not replace Supabase. Keep the existing Supabase tables, row-level security policies, and private `private-resumes` bucket. Apply the migration only if the project does not already have this schema; it is not necessary to reconnect or recreate Supabase data.

## Hosting limitations

Production search requests are stored in Supabase and sent to Vercel Queues. The daemon processes them outside the HTTP request and the queue can redeliver unacknowledged jobs. Vercel Daemons are production-only and Hobby memory/CPU quotas can pause them; queued messages have a maximum seven-day retention. Preview deployments do not process searches. The app does not scan continuously.

Confirm TopJobs.lk's applicable terms and rate limits before using the scraper. The parser can also need maintenance if the site changes. Free provider plans, quotas, sleep behavior, and availability can change; public hosting is not guaranteed to remain free.

## Gmail App Password and automatic applications

In Settings, follow the in-app guide: enable Google 2-Step Verification, create a Gmail App Password at [Google App Passwords](https://myaccount.google.com/apppasswords), and save it with the sender address. A normal Gmail password is not accepted. The API encrypts the saved App Password; Google SMTP must still accept the sign-in.

Automatic applications are off by default. If explicitly enabled in Settings, the app sends a generated email with the matched private resume to a valid contact email on each newly discovered matching TopJobs listing. This does not submit external website forms. Existing applications are not automatically retried, and uncertain send outcomes remain locked to avoid duplicates. Check the recipient, resume, and generated application content before enabling the setting. When automatic applications are off, each email still requires the explicit approval checkbox on the Applications page. Gmail acceptance does not confirm delivery.

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
