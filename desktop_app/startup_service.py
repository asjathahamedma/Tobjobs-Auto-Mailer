import os


STARTUP_FOLDER = os.path.join(
    os.environ.get("APPDATA", ""),
    "Microsoft",
    "Windows",
    "Start Menu",
    "Programs",
    "Startup",
)


class StartupService:
    """Manages the Windows startup launcher for the Tauri desktop app."""

    def __init__(self, project_dir):
        self.project_dir = os.path.abspath(project_dir)
        self.install_dir = os.path.abspath(
            os.environ.get("TOPJOBS_INSTALL_DIR", self.project_dir)
        )
        self.app_exe = os.path.abspath(
            os.environ.get(
                "TOPJOBS_APP_EXE",
                os.path.join(self.install_dir, "topjobs-auto-mailer-shell.exe"),
            )
        )
        self.startup_script_path = os.path.join(STARTUP_FOLDER, "TopJobs-Auto-Mailer.vbs")
        self.legacy_paths = (
            os.path.join(STARTUP_FOLDER, "TopJobs-Auto-Mailer-Desktop.vbs"),
            os.path.join(STARTUP_FOLDER, "TopJobs-Auto-Mailer-Desktop.bat"),
            os.path.join(STARTUP_FOLDER, "run_startup_automation.bat"),
        )

    def is_enabled(self):
        return os.path.exists(self.startup_script_path)

    def _launcher_contents(self, delay_seconds=15):
        delay_ms = max(0, int(delay_seconds)) * 1000
        project_dir = self.project_dir
        install_dir = self.install_dir
        app_exe = self.app_exe
        return f"""Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
projectDir = "{project_dir}"
installDir = "{install_dir}"
appExe = "{app_exe}"
releaseExeA = projectDir & "\\src-tauri\\target\\release\\topjobs-auto-mailer-shell.exe"
releaseExeB = projectDir & "\\src-tauri\\target\\release\\TopJobs Auto Mailer.exe"
rootLauncher = projectDir & "\\TopJobs Auto Mailer.vbs"
fallbackBatch = projectDir & "\\run_desktop_app.bat"
shell.CurrentDirectory = installDir
WScript.Sleep {delay_ms}
If fso.FileExists(appExe) Then
    shell.Run Chr(34) & appExe & Chr(34) & " --startup", 0, False
ElseIf fso.FileExists(releaseExeA) Then
    shell.Run Chr(34) & releaseExeA & Chr(34) & " --startup", 0, False
ElseIf fso.FileExists(releaseExeB) Then
    shell.Run Chr(34) & releaseExeB & Chr(34) & " --startup", 0, False
ElseIf fso.FileExists(rootLauncher) Then
    shell.Run Chr(34) & rootLauncher & Chr(34) & " startup", 0, False
ElseIf fso.FileExists(fallbackBatch) Then
    shell.Run "cmd /c " & Chr(34) & fallbackBatch & Chr(34) & " startup", 0, False
End If
"""

    def enable(self, delay_seconds=15):
        os.makedirs(STARTUP_FOLDER, exist_ok=True)
        with open(self.startup_script_path, "w", encoding="utf-8") as file:
            file.write(self._launcher_contents(delay_seconds))
        self._remove_legacy_entries()

    def disable(self):
        for path in (self.startup_script_path, *self.legacy_paths):
            if os.path.exists(path):
                os.remove(path)

    def _remove_legacy_entries(self):
        for path in self.legacy_paths:
            if os.path.exists(path):
                os.remove(path)
