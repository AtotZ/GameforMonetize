import datetime
# version: 2026-06-23-updater-private-upload-inline-v5
import json
import os
import runpy
import sys
import time
import urllib.request


SCRIPT_BUILD = "2026-06-23-updater-v5"
REPO_RAW_ROOT = "https://raw.githubusercontent.com/AtotZ/GameforMonetize/main"
DOWNLOAD_TIMEOUT_SECONDS = 20
DEFAULT_PRIVATE_SYNC_CONFIG = {
    "owner": "AtotZ",
    "repo": "UploadData",
    "branch": "main",
    "token": "",
    "remote_root": "pythonista-data",
    "commit_message_prefix": "Pythonista data sync",
    "commit_user_name": "",
    "commit_user_email": "",
    "files": [
        {
            "label": "active_offer",
            "local_rel_path": "TestSubjextData/offers/active_offer.json",
            "remote_rel_path": "offers/active_offer.json",
        },
        {
            "label": "active_offer_history",
            "local_rel_path": "TestSubjextData/offers/active_offer_history.jsonl",
            "remote_rel_path": "offers/active_offer_history.jsonl",
        },
        {
            "label": "offer_latest_debug",
            "local_rel_path": "TestSubjextData/offers/TripLog-OnisAI-PostcodeIsolation-latest.json",
            "remote_rel_path": "offers/TripLog-OnisAI-PostcodeIsolation-latest.json",
        },
        {
            "label": "traffic_latest",
            "local_rel_path": "TestSubjextData/traffic/TrafficBeacon-latest.json",
            "remote_rel_path": "traffic/TrafficBeacon-latest.json",
        },
        {
            "label": "traffic_history",
            "local_rel_path": "TestSubjextData/traffic/TrafficBeacon-history.json",
            "remote_rel_path": "traffic/TrafficBeacon-history.json",
        },
        {
            "label": "traffic_db",
            "local_rel_path": "TestSubjextData/traffic/TrafficBeacon-db.json",
            "remote_rel_path": "traffic/TrafficBeacon-db.json",
        },
        {
            "label": "route_db",
            "local_rel_path": "TestSubjextData/traffic/TrafficRoute-db.json",
            "remote_rel_path": "traffic/TrafficRoute-db.json",
        },
    ],
}


def _safe_script_dir():
    try:
        path = os.path.abspath(__file__)
        directory = os.path.dirname(path)
        if directory and os.path.exists(directory):
            return directory
    except Exception:
        pass
    return os.path.expanduser("~/Documents")


SCRIPT_DIR = _safe_script_dir()
STATUS_PATH = os.path.join(SCRIPT_DIR, "update_from_github_status.json")
PRIVATE_SYNC_CONFIG_PATH = os.path.join(SCRIPT_DIR, "github_private_sync_config.json")
PRIVATE_UPLOAD_STATUS_PATH = os.path.join(SCRIPT_DIR, "github_private_upload_status.json")
PRIVATE_UPLOAD_SCRIPT_PATH = os.path.join(SCRIPT_DIR, "upload_data_to_private_github.py")

FILE_MAP = [
    {
        "label": "UberTripLogger",
        "remote_name": "UberTripLoggerPostcodeIsolation.py",
        "local_name": "UberTripLogger.py",
    },
    {
        "label": "traffic_beacon",
        "remote_name": "traffic_beacon.py",
        "local_name": "traffic_beacon.py",
    },
    {
        "label": "update_from_github",
        "remote_name": "update_from_github.py",
        "local_name": "update_from_github.py",
    },
    {
        "label": "upload_data_to_private_github",
        "remote_name": "upload_data_to_private_github.py",
        "local_name": "upload_data_to_private_github.py",
    },
]


def _timestamp():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _download_text(url):
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "PythonistaUpdater/1.0",
            "Cache-Control": "no-cache",
        },
    )
    with urllib.request.urlopen(request, timeout=DOWNLOAD_TIMEOUT_SECONDS) as response:
        raw = response.read()
    return raw.decode("utf-8")


def _write_text(path, text):
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)


def _write_status(payload):
    with open(STATUS_PATH, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)


def _extract_token_from_argv():
    for raw_arg in sys.argv[1:]:
        arg = ("%s" % (raw_arg or "")).strip()
        if not arg:
            continue
        if arg.startswith("github_pat_") or arg.startswith("ghp_"):
            return arg
        if arg.lower().startswith("token="):
            candidate = arg.split("=", 1)[1].strip()
            if candidate.startswith("github_pat_") or candidate.startswith("ghp_"):
                return candidate
    return ""


def _read_existing_json(path):
    try:
        with open(path, "r", encoding="utf-8") as handle:
            payload = json.load(handle)
        if isinstance(payload, dict):
            return payload
    except Exception:
        pass
    return {}


def _bootstrap_private_sync_config():
    token = _extract_token_from_argv()
    if not token:
        return None
    payload = _read_existing_json(PRIVATE_SYNC_CONFIG_PATH)
    merged = dict(DEFAULT_PRIVATE_SYNC_CONFIG)
    if payload:
        merged.update(payload)
    merged["token"] = token
    with open(PRIVATE_SYNC_CONFIG_PATH, "w", encoding="utf-8") as handle:
        json.dump(merged, handle, ensure_ascii=False, indent=2)
    return {
        "config_path": PRIVATE_SYNC_CONFIG_PATH,
        "repo": "%s/%s" % (merged["owner"], merged["repo"]),
        "token_prefix": token[:16],
    }


def _run_private_uploader():
    if not os.path.exists(PRIVATE_UPLOAD_SCRIPT_PATH):
        return {
            "ok": False,
            "ran": False,
            "error": "Missing upload_data_to_private_github.py",
        }

    result = {
        "ok": False,
        "ran": True,
        "script_path": PRIVATE_UPLOAD_SCRIPT_PATH,
    }
    try:
        runpy.run_path(PRIVATE_UPLOAD_SCRIPT_PATH, run_name="__main__")
    except SystemExit as exc:
        code = exc.code if isinstance(exc.code, int) else 0
        result["exit_code"] = code
        if code not in (0, None):
            result["error"] = "Uploader exited with code %s" % code
    except Exception as exc:
        result["error"] = "%s" % exc

    status_payload = _read_existing_json(PRIVATE_UPLOAD_STATUS_PATH)
    if status_payload:
        result["status"] = status_payload
        result["ok"] = bool(status_payload.get("ok"))
    else:
        result["ok"] = "error" not in result
    return result


def _update_one_file(item):
    url = "%s/%s" % (REPO_RAW_ROOT, item["remote_name"])
    target_path = os.path.join(SCRIPT_DIR, item["local_name"])
    source_text = _download_text(url)
    if "404: Not Found" in source_text and len(source_text.strip()) <= 20:
        raise RuntimeError("GitHub returned 404 for %s" % item["remote_name"])
    if "import " not in source_text and "def " not in source_text:
        raise RuntimeError("Downloaded content for %s does not look like Python code." % item["remote_name"])
    _write_text(target_path, source_text)
    return {
        "label": item["label"],
        "remote_name": item["remote_name"],
        "local_name": item["local_name"],
        "target_path": target_path,
        "bytes": len(source_text.encode("utf-8")),
    }


def main():
    started = time.perf_counter()
    results = []
    for item in FILE_MAP:
        results.append(_update_one_file(item))
    private_sync_bootstrap = _bootstrap_private_sync_config()
    private_upload_result = _run_private_uploader()

    payload = {
        "ok": bool(private_upload_result.get("ok")),
        "timestamp": _timestamp(),
        "script_build": SCRIPT_BUILD,
        "script_dir": SCRIPT_DIR,
        "files": results,
        "private_sync_bootstrap": private_sync_bootstrap,
        "private_upload": private_upload_result,
        "elapsed_seconds": round(time.perf_counter() - started, 3),
    }
    _write_status(payload)

    print("[updater] Updated %d file(s) in %s" % (len(results), SCRIPT_DIR))
    for result in results:
        print(
            "[updater] %s -> %s (%d bytes)"
            % (result["remote_name"], result["local_name"], result["bytes"])
        )
    if private_upload_result.get("ok"):
        upload_status = private_upload_result.get("status") or {}
        print(
            "[updater] private upload ok | uploaded=%s | at=%s"
            % (
                len(upload_status.get("results") or []),
                upload_status.get("timestamp") or "",
            )
        )
    else:
        print("[updater] private upload failed: %s" % (private_upload_result.get("error") or "unknown"))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        payload = {
            "ok": False,
            "timestamp": _timestamp(),
            "script_build": SCRIPT_BUILD,
            "script_dir": SCRIPT_DIR,
            "error": "%s" % exc,
        }
        try:
            _write_status(payload)
        except Exception:
            pass
        print("[updater] failed: %s" % exc)
        raise SystemExit(1)
    raise SystemExit(0)
