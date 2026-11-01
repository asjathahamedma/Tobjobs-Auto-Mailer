import argparse
import json
import os
import sys
from pathlib import Path

from desktop_app.config_store import ConfigStore
from desktop_app.account_service import AccountService
from desktop_app.database import AppDatabase
from desktop_app.gmail_credentials import GmailCredentialStore
from desktop_app.history_service import ArtifactHistoryService
from desktop_app.startup_service import StartupService
from src.config import ENV_FILE, resolve_existing_path
from tauri_bridge.common import app_home, ensure_project_root, project_root, write_json
from tauri_bridge.resume_profiles import (
    create_or_update_profile_for_resume,
    preview_profile_for_resume,
)


def build_resume_inventory(config):
    data_root = app_home()
    inventory = []
    seen_paths = set()

    for profile_key, profile in config.get("profiles", {}).items():
        resume_path = profile.get("resume_path", "").strip()
        if not resume_path or resume_path in seen_paths:
            continue
        seen_paths.add(resume_path)
        absolute_path = Path(resolve_existing_path(resume_path))
        exists = absolute_path.exists()
        inventory.append(
            {
                "profile_key": profile_key,
                "profile_label": profile.get("label", profile_key),
                "resume_path": resume_path,
                "absolute_path": str(absolute_path),
                "file_name": absolute_path.name or Path(resume_path).name,
                "exists": exists,
                "size_bytes": absolute_path.stat().st_size if exists else 0,
            }
        )

    resumes_dir = data_root / "resumes"
    if resumes_dir.exists():
        mapped_paths = {item["resume_path"] for item in inventory}
        for pdf_path in resumes_dir.glob("*.pdf"):
            relative_path = str(pdf_path.relative_to(data_root)).replace("/", "\\")
            if relative_path in mapped_paths:
                continue
            inventory.append(
                {
                    "profile_key": "",
                    "profile_label": "Unassigned",
                    "resume_path": relative_path,
                    "absolute_path": str(pdf_path),
                    "file_name": pdf_path.name,
                    "exists": True,
                    "size_bytes": pdf_path.stat().st_size,
                }
            )

    inventory.sort(key=lambda item: (item["profile_label"], item["file_name"].lower()))
    return inventory


def save_mailer_env(config):
    auth = config.get("mailer", {}).get("auth", {})
    sender_email = (auth.get("sender_email") or "").strip()
    app_password = (auth.get("app_password") or "").strip()
    credential_store = GmailCredentialStore()
    if app_password:
        credential_store.set_password(app_password)
    auth["app_password"] = ""
    auth.pop("app_password_configured", None)
    env_path = app_home() / ENV_FILE
    env_path.parent.mkdir(parents=True, exist_ok=True)
    env_path.write_text(
        f"EMAIL_ADDRESS={json.dumps(sender_email)}\n",
        encoding="utf-8",
    )


def load_config_for_ui(store):
    config = store.snapshot()
    auth = config.setdefault("mailer", {}).setdefault("auth", {})
    credential_store = GmailCredentialStore()
    credential_store.clear_legacy_oauth_token()
    saved_password = auth.get("app_password", "")
    env_path = app_home() / ENV_FILE
    from dotenv import dotenv_values

    legacy_env_password = dotenv_values(env_path).get("EMAIL_PASSWORD", "") or ""
    if not credential_store.is_configured():
        if not saved_password:
            saved_password = legacy_env_password
        if saved_password:
            credential_store.set_password(saved_password)

    if auth.get("app_password") or legacy_env_password:
        auth["app_password"] = ""
        store.save(config)
        sender_email = (auth.get("sender_email") or "").strip()
        env_path.parent.mkdir(parents=True, exist_ok=True)
        env_path.write_text(f"EMAIL_ADDRESS={json.dumps(sender_email)}\n", encoding="utf-8")

    auth["app_password"] = ""
    auth["app_password_configured"] = credential_store.is_configured()
    return config


def read_stdin_json(default=None):
    default = {} if default is None else default
    if sys.stdin.isatty():
        return default
    raw_payload = sys.stdin.read().strip()
    if not raw_payload:
        return default
    try:
        return json.loads(raw_payload)
    except json.JSONDecodeError:
        return default


def main():
    ensure_project_root()
    parser = argparse.ArgumentParser(description="Bridge commands for the Tauri app.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    snapshot_parser = subparsers.add_parser("snapshot")
    snapshot_parser.add_argument("--days", type=int, default=30)

    resume_import_parser = subparsers.add_parser("resume-import")
    resume_import_parser.add_argument("--path", required=True)
    resume_draft_parser = subparsers.add_parser("resume-profile-draft")
    resume_draft_parser.add_argument("--path", required=True)
    resume_profile_parser = subparsers.add_parser("resume-profile-create")
    resume_profile_parser.add_argument("--path", required=True)

    subparsers.add_parser("config-get")
    subparsers.add_parser("resume-inventory")
    subparsers.add_parser("config-save")
    subparsers.add_parser("account-status")
    subparsers.add_parser("account-register")
    subparsers.add_parser("account-login")

    args = parser.parse_args()
    store = ConfigStore()

    if args.command == "account-status":
        write_json(AccountService().status())
        return

    if args.command in ("account-register", "account-login"):
        credentials = read_stdin_json({})
        account_service = AccountService()
        if args.command == "account-register":
            result = account_service.register(
                credentials.get("email", ""), credentials.get("password", "")
            )
        else:
            result = account_service.login(
                credentials.get("email", ""), credentials.get("password", "")
            )
        write_json(result)
        return

    if args.command == "snapshot":
        payload = ArtifactHistoryService(str(app_home())).collect_snapshot(args.days)
        payload["recent_activity"] = AppDatabase().get_recent_events(limit=80)
        write_json(payload)
        return

    if args.command == "config-get":
        write_json(load_config_for_ui(store))
        return

    if args.command == "resume-inventory":
        payload = build_resume_inventory(store.snapshot())
        write_json(payload)
        return

    if args.command == "resume-import":
        absolute_path = Path(resolve_existing_path(args.path))
        result = create_or_update_profile_for_resume(absolute_path)
        payload = {
            "ok": True,
            "resource_root": str(project_root()),
            "app_home": str(app_home()),
            "imported": result,
            "config": store.snapshot(),
            "resume_inventory": build_resume_inventory(store.snapshot()),
        }
        write_json(payload)
        return

    if args.command == "resume-profile-draft":
        absolute_path = Path(resolve_existing_path(args.path))
        payload = {
            "ok": True,
            "resource_root": str(project_root()),
            "app_home": str(app_home()),
            "preview": preview_profile_for_resume(absolute_path),
        }
        write_json(payload)
        return

    if args.command == "resume-profile-create":
        absolute_path = Path(resolve_existing_path(args.path))
        profile_payload = read_stdin_json({})
        result = create_or_update_profile_for_resume(absolute_path, overrides=profile_payload)
        payload = {
            "ok": True,
            "resource_root": str(project_root()),
            "app_home": str(app_home()),
            "imported": result,
            "config": store.snapshot(),
            "resume_inventory": build_resume_inventory(store.snapshot()),
        }
        write_json(payload)
        return

    if args.command == "config-save":
        payload = json.load(sys.stdin)
        save_mailer_env(payload)
        store.save(payload)
        payload["mailer"]["auth"]["app_password_configured"] = GmailCredentialStore().is_configured()
        startup_service = StartupService(str(project_root()))
        app_settings = payload.get("app", {})
        if app_settings.get("run_at_startup"):
            startup_service.enable(app_settings.get("startup_delay_seconds", 15))
        else:
            startup_service.disable()
        write_json(
            {
                "ok": True,
                "config_path": os.path.abspath(store.path),
                "startup_enabled": startup_service.is_enabled(),
            }
        )
        return


if __name__ == "__main__":
    main()
