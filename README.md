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

`TopJobs Auto Mailer_2.0.0_x64-setup.exe`

3. Double-click the setup file and install the app.

4. Open TopJobs Auto Mailer, add your Gmail/app password details, import your resumes, and start the workflow.

Developer note: the installer is a large build artifact, so it is uploaded to GitHub Releases instead of being committed into this repository.

## Version 2 Features

- Modern desktop UI with Dashboard, Jobs, Resume Profiles, and Settings pages.
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

1. Add sender details in Settings.
2. Import one or more PDF resumes in Resume Profiles.
3. The app creates resume profiles with detected title keywords, description keywords, and summaries.
4. Start the workflow from the Dashboard.
5. Python automation scans TopJobs, filters jobs by date and role fit, chooses the matching resume profile, and applies when an email is available.
6. The UI shows live progress and stores the result history locally.

## Email Login

Current Version 2 email sending uses a Gmail address plus Gmail App Password.

Google OAuth is planned for a future public release so users can connect their Google account without manually creating an app password.

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
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
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
src-tauri/target/release/bundle/nsis/TopJobs Auto Mailer_2.0.0_x64-setup.exe
```

## Publishing Version 2

Commit and push the source code:

```powershell
git add .
git commit -m "Release TopJobs Auto Mailer v2"
git push origin main
```

Create and push the Version 2 tag:

```powershell
git tag v2.0.0
git push origin v2.0.0
```

Then create a GitHub Release from tag `v2.0.0` and upload:

```text
src-tauri/target/release/bundle/nsis/TopJobs Auto Mailer_2.0.0_x64-setup.exe
```

## Local Data

The app stores runtime data locally and does not commit it to GitHub:

- `.env`
- `resumes/`
- `data/`
- `logs/`
- `.venv/`
- `src-tauri/target/`

## Notes

- This app automates email-based applications only when a job email is found.
- Users should review their resume profiles and settings before enabling automation.
- TopJobs pages can change over time, so scraper behavior may need updates if the website changes.
