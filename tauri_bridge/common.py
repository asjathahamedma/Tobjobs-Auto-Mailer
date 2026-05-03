import json
import os
import sys
from pathlib import Path


APP_NAME = "TopJobs Auto Mailer"


def project_root() -> Path:
    env_root = os.environ.get("TOPJOBS_RESOURCE_DIR")
    if env_root:
        return Path(env_root)

    current = Path(__file__).resolve()
    for base in (current.parent, *current.parents):
        if (base / "run_automation.py").exists():
            return base

    exe_path = Path(sys.executable).resolve()
    for candidate in (
        exe_path.parent / "_up_",
        exe_path.parent / "resources",
        exe_path.parent.parent / "resources",
        exe_path.parent,
    ):
        if (candidate / "run_automation.py").exists():
            return candidate

    return Path.cwd()


def app_home() -> Path:
    env_home = os.environ.get("TOPJOBS_APP_HOME")
    if env_home:
        return Path(env_home)

    root = project_root()
    if (root / ".git").exists() or (root / "src-tauri").exists():
        return root

    appdata = os.environ.get("APPDATA")
    if appdata:
        return Path(appdata) / APP_NAME
    return root


def ensure_project_root():
    code_root = project_root()
    data_root = app_home()
    data_root.mkdir(parents=True, exist_ok=True)
    if str(code_root) not in sys.path:
        sys.path.insert(0, str(code_root))
    os.chdir(data_root)


def write_json(payload):
    sys.stdout.write(json.dumps(payload, ensure_ascii=True))
    sys.stdout.flush()
