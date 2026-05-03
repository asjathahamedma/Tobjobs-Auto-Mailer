import json
import logging
import os
import sys
from datetime import datetime

import pandas as pd


def setup_logging(use_console=True, extra_handlers=None):
    """Sets up logging to print to console and save to a file."""
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "automation_log.log")

    logger = logging.getLogger("JobAutomation")
    logger.setLevel(logging.DEBUG)

    if logger.hasHandlers():
        logger.handlers.clear()

    if use_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter("%(message)s")
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)

    file_handler = logging.FileHandler(log_file, mode="a")
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(
        "%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)

    for handler in extra_handlers or []:
        logger.addHandler(handler)

    return logger


def load_processed_jobs(filename):
    """Loads the set of already applied job URLs from the tracking file."""
    if not os.path.exists(filename):
        return set()

    try:
        df = pd.read_csv(filename)
    except (pd.errors.EmptyDataError, FileNotFoundError):
        return set()

    if "url" not in df.columns:
        return set()

    return set(df["url"].dropna().astype(str))


def save_processed_jobs(filename, url_set):
    """Saves the updated set of applied job URLs to the tracking file."""
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    df = pd.DataFrame(sorted(url_set), columns=["url"])
    df.to_csv(filename, index=False)


def has_startup_run_today(filename):
    """Returns True if startup mode already ran today."""
    if not os.path.exists(filename):
        return False

    try:
        with open(filename, "r", encoding="utf-8") as file:
            payload = json.load(file)
    except (json.JSONDecodeError, OSError):
        return False

    return payload.get("last_startup_attempt_date") == datetime.now().date().isoformat()


def record_startup_run(filename, status, summary=None):
    """Stores the last startup attempt so repeated PC restarts do not rerun the workflow."""
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    payload = {
        "last_startup_attempt_date": datetime.now().date().isoformat(),
        "last_startup_timestamp": datetime.now().isoformat(timespec="seconds"),
        "status": status,
    }

    if summary:
        payload["summary"] = summary

    with open(filename, "w", encoding="utf-8") as file:
        json.dump(payload, file, indent=2)


def load_json_state(filename, default=None):
    """Loads a JSON state file and returns the provided default on failure."""
    default = {} if default is None else default
    if not os.path.exists(filename):
        return default

    try:
        with open(filename, "r", encoding="utf-8") as file:
            return json.load(file)
    except (json.JSONDecodeError, OSError):
        return default


def save_json_state(filename, payload):
    """Saves a JSON state file, creating its directory if necessary."""
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    with open(filename, "w", encoding="utf-8") as file:
        json.dump(payload, file, indent=2)
