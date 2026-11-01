# TopJobs Auto Mailer

TopJobs Auto Mailer is a Windows desktop app that searches TopJobs.lk, matches jobs against resume profiles, and helps send tailored applications through Gmail.

Version 2 rebuilt the old Python script into a production-style desktop app using **Tauri + React + Tailwind + Vite**, while keeping the existing Python automation engine.

## Workflow Demo

[Watch the Version 2 workflow demo](docs/media/topjobs-automailer-workflow-v2.mp4)

## Download and Install

Normal users only need the Windows setup file. They do not need to download the source code, install Python, install Node.js, or run any commands.

1. Open the GitHub Releases page:

[TopJobs Auto Mailer Releases](https://github.com/asjathahamedma/Tobjobs-Auto-Mailer/releases)

2. Download the latest setup file:

`TopJobs Auto Mailer_2.3.2_x64-setup.exe`

3. Double-click the setup file and install the app.

4. On first launch, create a local account, add your Gmail address and app password using the in-app guide, and set up your sender profile. Then import a PDF resume and start a workflow when ready.

Developer note: the installer is a large build artifact, so it is uploaded to GitHub Releases instead of being committed into this repository.

## Version 2 Features

- Modern desktop UI with Dashboard, Jobs, Resume Profiles, and Settings pages.
- First-launch local account registration and sign-in; no demo profile or job activity is created for a new install.
- New installs wait for setup before automation can run.
- A GitHub release check shows an in-app update prompt when a newer published version is available.
- Gmail app passwords are saved in the computer's operating-system credential store.
- The Gmail App Password field includes a step-by-step guide that opens Google's app-password page.
- Professional job-specific application emails and optional generated cover-letter PDF attachments.
- Start and stop the automation from the app UI.
- Live workflow progress, logs, stage counter, and progress bar.
- Today Summary with scanned, reviewed, matched, skipped, and applied totals.
- Skip reason breakdown for no email, already applied, low fit, senior role, excluded role, remote required, and missing resume.
- Profile performance analytics showing which resume/profile gets the most matches and applications.
- Jobs table with filters, match score, resume used, status badge, skipped reason, and apply status.
- Resume import flow that analyzes a PDF and creates an editable resume profile.
- Local history from SQLite, CSV files, and logs.
- Windows startup automation can be enabled or disabled from Settings.

## How It Works

1. Register or sign in to the local account on this computer.
2. Add sender details in Settings or during first-run setup.
3. Enter a Gmail address and Gmail app password during first-run setup (or later in Settings).
4. Import one or more PDF resumes in Resume Profiles.
5. The app creates resume profiles with detected title keywords, description keywords, and summaries.
6. Start the workflow from the Dashboard.
7. Python automation scans TopJobs, filters jobs by date and role fit, chooses the matching resume profile, and applies when an email is available.
8. The UI shows live progress and stores the result history locally.

The local app account and resume/profile data stay on this computer. Account passwords are stored as salted PBKDF2 hashes. Gmail app passwords are stored in the operating-system credential store and are not written to the app config or `.env` file.

## Gmail App Password Setup

The app never asks for a user's normal Google password. Each user supplies a Gmail address and a dedicated app password.

The app includes a **How do I get a Gmail app password?** guide beside the password field. In brief: enable 2-Step Verification on the Google account, open [Google App Passwords](https://myaccount.google.com/apppasswords), create an app password, then paste it into the app. If Google does not offer App Passwords for an account, its account type, administrator, or security settings may not allow them.

Generated cover letters are saved locally as PDFs and attached with the resume when the cover-letter setting is enabled. The letter uses only the profile summary and matched job keywords; review your profile details before enabling automated applications.

## App Updates

The desktop app checks GitHub Releases when it opens and shows a prompt when a newer published version is available. The prompt opens that release page; users download and run the Windows installer themselves. It does **not** silently download or install updates.

To publish an update:

1. Make and push your code changes to `main`.
2. Set the same new version (for example `2.4.0`) in `package.json`, the root `package-lock.json`, `src-tauri/tauri.conf.json`, and `src-tauri/Cargo.toml` / `src-tauri/Cargo.lock`.
3. Commit and push those version changes.
4. Create and push a matching version tag, for example `git tag v2.4.0` and `git push origin v2.4.0`.
5. The GitHub Actions workflow at `.github/workflows/release.yml` builds the Windows installer and attaches it to a published GitHub Release automatically.

The workflow requires GitHub Actions to be enabled and the repository's `GITHUB_TOKEN` to have release write access (the workflow requests `contents: write`). The desktop app compares its bundled version with the latest non-draft, non-prerelease GitHub Release; pushing to a branch without publishing a versioned release does not trigger an update prompt.

## Tech Stack

- `ui/` - React, Tailwind CSS, Vite, Framer Motion
- `src-tauri/` - Tauri Windows desktop shell
- `tauri_bridge/` - Python bridge used by the Tauri app
- `src/` - TopJobs scraper, mailer, config, and matching logic
- `desktop_app/` - history, startup, profile import, and app services
- `run_automation.py` - main Python automation entrypoint

## Local Development

Install dependencies:

```powershell
npm install
uv python install 3.12 --install-dir .python/runtime
$python = Get-ChildItem .python/runtime -Filter python.exe -Recurse | Select-Object -First 1 -ExpandProperty FullName
uv pip install --python $python --target .python/site-packages -r requirements.txt
```

Run the desktop app in development:

```powershell
npm run tauri:dev
```

Build the production installer:

```powershell
.\build_desktop_app.bat
```

The installer is generated at:

```text
src-tauri/target/release/bundle/nsis/TopJobs Auto Mailer_2.3.2_x64-setup.exe
```

## Manual Windows Build

```powershell
npm ci
uv python install 3.12 --install-dir .python/runtime
$python = Get-ChildItem .python/runtime -Filter python.exe -Recurse | Select-Object -First 1 -ExpandProperty FullName
uv pip install --python $python --target .python/site-packages -r requirements.txt
npm run tauri:build
```

## Local Data

The app stores runtime data locally and does not commit it to GitHub:

- `.env` (email address only; legacy installations are migrated)
- `resumes/`
- `data/`
- `logs/`
- `.python/` (bundled portable Python runtime in release builds)
- `.venv/` (optional local development environment)
- `src-tauri/target/`

## Notes

- This app automates email-based applications only when a job email is found.
- Users should review their resume profiles and settings before enabling automation.
- TopJobs pages can change over time, so scraper behavior may need updates if the website changes.
