# Architecture Audit

**Status:** Phase One audit, based on the repository as inspected on 2026-11-01. This document records current behavior; it does not claim that a web version has been implemented or deployed.

**Historical baseline:** This audit describes the desktop source before the web conversion. See [the current migration status](./MIGRATION_PLAN.md) and [README](../README.md) for what has since changed and what remains unverified.

## Executive summary

The current application is a Windows desktop application built from a React/Vite UI, a Rust/Tauri shell, and a Python automation engine. The UI invokes Tauri commands; the shell starts Python subprocesses and exchanges JSON over stdin/stdout. The automation is not exposed as an HTTP API and has no web authentication, multi-user database, or deployment configuration.

The existing search source is TopJobs.lk. It is scraped using `requests` and BeautifulSoup; job-ad images can be analyzed using EasyOCR and OpenCV. Matching is deterministic keyword scoring against local resume profiles. For matching jobs with a contact email and a configured resume, the mailer sends an application email through Gmail SMTP. The sending is automatic rather than a user-reviewed web application submission.

The current design can provide reusable scraping, matching, resume parsing, email-content generation, and cover-letter code, but those pieces must be separated from local files, desktop keyring, and Tauri process management before they can safely serve a browser-based account.

## Repository and entry points

| Area | Current implementation |
|---|---|
| Desktop UI | React 19, TypeScript, Tailwind, Vite under `ui/`; `ui/src/main.tsx` mounts `ui/src/App.tsx`. |
| Desktop host | Rust/Tauri 2 under `src-tauri/`; `src-tauri/src/main.rs` registers native commands and launches Python. Tauri is configured to create a Windows NSIS installer. |
| Python workflow entry | `run_automation.py`; `run_workflow()` runs scraper, then optionally the mailer, and emits progress through a callback. |
| Desktop/Python bridge | `tauri_bridge/cli.py` serves one-shot commands; `tauri_bridge/workflow_runner.py` runs the workflow and streams JSON progress/log records to the Tauri shell. |
| Job discovery and match | `src/scraper.py`. |
| Application emails and cover letters | `src/mailer.py`. |
| Configuration and profile templates | `src/config.py`; defaults, profile templates, user settings, and profile definitions are stored as JSON. |
| Resume profile parsing | `tauri_bridge/resume_profiles.py`; PDF text is extracted with `pypdf`, then keywords are matched against a fixed vocabulary and profile templates. |
| Desktop account and secret storage | `desktop_app/account_service.py` stores a local account hash in JSON; `desktop_app/gmail_credentials.py` stores the Gmail App Password via OS keyring. |
| History and analytics | `desktop_app/database.py` writes SQLite activity and synchronizes CSV artifacts; `desktop_app/history_service.py` builds dashboard snapshots from CSV and log files. |
| Desktop release | `.github/workflows/release.yml` builds and publishes a Windows installer from a `v*` tag. The README describes manual installation and updates. |

There is no Next.js App Router project, FastAPI service, Supabase integration, PostgreSQL migration, browser session, or production hosting configuration in the repository.

## Existing job-search behavior

1. `run_automation.py` reloads the configuration-sensitive modules and invokes `scraper.main()`.
2. `src/scraper.py` fetches the configured category pages (the defaults are two TopJobs.lk category URLs), parses listing rows and dates, and constructs TopJobs advert URLs.
3. It filters by the configured recent-job window (default: two days) and URLs already in `data/processed_jobs.csv`.
4. It fetches each advert page, extracts the title-adjacent visible fields and company email, and optionally downloads ad images for OCR.
5. It scores the advert text against the configured profile title and description keywords. Seniority, excluded-title, remote-only, and minimum-score rules can reject jobs.
6. Matched leads are saved to timestamped CSV files in `data/leads/`. The matching score is a weighted integer point total; it is not currently a normalized percentage.
7. Unless scan-only mode is enabled, `src/mailer.py` reads the most recent leads file. If a lead has an email and existing resume path, it generates a professional email and optionally a PDF cover letter, then sends it through Gmail SMTP. It does not show a review/approval screen before sending.
8. A URL is added to the processed-jobs CSV after `smtplib.sendmail()` returns without an exception. This confirms SMTP accepted the message for sending; it does not confirm delivery or an employer's receipt.
9. Run summaries, logs, candidate leads, application-feedback reports, and SQLite activity feed the desktop dashboard.

The scraper uses HTTP GET requests with timeouts and retries; the inspected source contains no Selenium, Playwright, or other browser automation. It supports TopJobs.lk only. The repository does not establish that scraping is permitted by TopJobs' terms or provide an official API integration; terms, rate limits, and permitted access must be checked before public hosting.

## Runtime and dependency constraints

Python dependencies are listed without version pins in `requirements.txt`: `requests`, `beautifulsoup4`, `pandas`, `easyocr`, `python-dotenv`, `opencv-python`, `pypdf`, `keyring`, and `reportlab`.

- `easyocr` and `opencv-python` make the deployment bundle and runtime materially heavier than a basic API. OCR initializes lazily and can fail/fall back; ad-image processing can also add network and CPU time.
- Search duration has not been benchmarked. It scales with categories, discovered ads, retries/timeouts, image OCR, and candidate emails. The current scraper sleeps between requests and the mailer sleeps five seconds after each successful send. Therefore, a single short serverless request cannot be assumed to complete a whole run safely.
- A persistent/ephemeral Python API function can handle short operations, but the complete search should first be measured and tested against the selected host's package-size, memory, CPU, and execution-time limits. If it exceeds them, use a triggered job/worker that records progress and can be polled; this does not require continuous polling for new jobs.
- `keyring` relies on a desktop operating-system credential store and is not an appropriate hosted secret store. The web version needs a server-only secret-storage design for SMTP credentials.
- There are no current migrations or service definitions for hosted storage. SQLite is local and is not a safe shared multi-user database.

## Current identity, configuration, and data

The app's registration is device-local. `AccountService` stores the email and a salted PBKDF2 password hash in `data/account.json`; it is not Supabase Auth and does not create a reusable server session. Frontend authentication is held in React state and is not a secure web session.

The app configuration is JSON (`data/app_config.json`), with profiles, scraper settings, contact data, mailer settings, and app settings. Legacy installations may also have an `.env`; current code migrates a saved Gmail App Password into the OS keyring and strips it from plaintext config/environment files. Each profile points to a local PDF path.

| Local artifact | Use | Web migration implications |
|---|---|---|
| `data/app_config.json` | Scraper settings, profile definitions, sender/contact settings | Export and validate; map settings to a user-owned settings row and profiles to user-owned profile/resume rows. |
| `data/account.json` | Device-local account hash | Do not import as a Supabase password. User must create or confirm a Supabase Auth account. |
| OS keyring / legacy `.env` | Gmail App Password and sender address | Keyring contents cannot be migrated by a normal data-file importer. Re-enter the App Password through an authenticated web flow; encrypt/store server-side or avoid persistence. |
| `resumes/*.pdf` | Resume files referenced by profiles | Upload explicitly to private object storage; validate file type and size; preserve a local backup. |
| `data/processed_jobs.csv` | URLs previously sent to, used as duplicate-send guard | Import into application records with an idempotency key before enabling sending. |
| `data/leads/topjobs_leads_*.csv` | Matched job details and profile/match evidence | Import jobs and per-user matches; deduplicate by normalized source URL. |
| `data/application_feedback/*.csv` | Per-run send/skip/failure results | Import into application history while preserving old status, notes, timestamps inferred from filenames, and source rows. |
| `logs/automation_log.log` | Run summaries, progress diagnostics, skip evidence | Optional archival import; summaries are parsed from human-readable log lines, not a canonical run database. Exclude sensitive log messages from routine uploads. |
| `data/app_state.db` | SQLite runs, events, jobs, applications | Export/import through a dedicated migration path. Its schema has no `user_id`; it is local single-user data. |
| `data/startup_state.json` | Windows startup-run bookkeeping | Desktop-only; not needed in a manually triggered web workflow. |

Runtime paths (`data/`, `resumes/`, `logs/`, `.env`) are ignored by Git. No private local data was present in the workspace at audit time, so record counts and an import canary could not be tested.

## Existing UI surface

The desktop UI contains Account/Welcome, Dashboard, Jobs, Resume Profiles, and Settings views:

- Dashboard shows run summaries, match/apply/skip analytics, profile performance, recent runs/logs, and workflow progress controls.
- Jobs merges matched-job and application-feedback data and provides search/status/profile/date filters. It has no persistent per-user server query, paginated API, or full job-details/review workflow.
- Resume Profiles imports PDFs, previews extracted profile suggestions, and lets the user edit profile data. The analysis is a fixed-vocabulary heuristic, not an AI provider.
- Settings include local startup behavior, scan and fit filters, category URLs, contact data, Gmail address/App Password, and cover-letter attachment behavior.
- The UI already uses responsive CSS patterns, but is embedded in a Tauri application. Native operations and all API calls go through `@tauri-apps/api`; replacing those calls with authenticated web APIs and converting the Vite shell to Next.js are required.

## Testing currently available

The repository contains Python unit tests for local account/config behavior, Gmail credentials, cover-letter generation, history analytics, and mail content. There are no web API, Supabase, RLS, browser, deployment, import, or end-to-end multi-device tests. Passing existing Python tests does not validate hosted behavior.
