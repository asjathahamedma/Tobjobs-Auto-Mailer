import argparse
import json
import logging
import sys

from desktop_app.database import AppDatabase
from run_automation import run_workflow
from tauri_bridge.common import ensure_project_root


class JsonLogHandler(logging.Handler):
    def __init__(self, database=None, run_id=None):
        super().__init__(level=logging.DEBUG)
        self.database = database
        self.run_id = run_id
        self.setFormatter(logging.Formatter("%(message)s"))

    def emit(self, record):
        try:
            message = self.format(record)
        except Exception:
            message = record.getMessage()

        if self.database is not None and self.run_id is not None:
            try:
                self.database.add_event(self.run_id, record.levelname, message)
            except Exception:
                pass

        payload = {
            "type": "log",
            "level": record.levelname,
            "message": message,
        }
        sys.stdout.write(json.dumps(payload) + "\n")
        sys.stdout.flush()


def emit_progress(payload):
    event = {
        "type": "progress",
        "percent": payload.get("percent", 0),
        "stage": payload.get("stage", ""),
        "detail": payload.get("detail", ""),
    }
    if payload.get("current") is not None:
        event["current"] = payload.get("current")
    if payload.get("total") is not None:
        event["total"] = payload.get("total")
    sys.stdout.write(json.dumps(event) + "\n")
    sys.stdout.flush()


def main():
    ensure_project_root()
    parser = argparse.ArgumentParser(description="Workflow runner for the Tauri UI.")
    parser.add_argument("--startup", action="store_true")
    args = parser.parse_args()
    database = AppDatabase()
    run_mode = "startup" if args.startup else "manual"
    run_id, started_at = database.create_run(run_mode)

    sys.stdout.write(json.dumps({"type": "state", "status": "starting"}) + "\n")
    sys.stdout.flush()

    try:
        summary = run_workflow(
            startup=args.startup,
            use_console=False,
            extra_handlers=[JsonLogHandler(database=database, run_id=run_id)],
            progress_callback=emit_progress,
        )
        database.complete_run(run_id, summary)
        database.sync_run_artifacts(run_id, started_at)
        sys.stdout.write(json.dumps({"type": "summary", "summary": summary}) + "\n")
        sys.stdout.write(json.dumps({"type": "state", "status": "finished"}) + "\n")
        sys.stdout.flush()
    except Exception as exc:
        database.add_event(run_id, "ERROR", f"Workflow crashed: {exc}")
        database.complete_run(run_id, {"status": "failed", "error": str(exc)})
        sys.stdout.write(
            json.dumps({"type": "error", "message": f"Workflow crashed: {exc}"}) + "\n"
        )
        sys.stdout.flush()
        raise


if __name__ == "__main__":
    main()
