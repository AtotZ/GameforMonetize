import datetime
import hashlib
# version: 2026-06-24-updater-daily-history-bootstrap-v16
import json
import os
import re
import runpy
import sys
import time
import urllib.request


SCRIPT_BUILD = "2026-06-24-updater-v16"
REPO_RAW_ROOT = "https://raw.githubusercontent.com/AtotZ/GameforMonetize/main"
MANIFEST_REMOTE_NAME = "pythonista_update_manifest.json"
DOWNLOAD_TIMEOUT_SECONDS = 20
MAX_CONSOLE_LOG_LINES = 400
TRIMMED_CONSOLE_LOG_LINES = 250
MAX_CONSOLE_LOG_BYTES = 48 * 1024
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
            "local_rel_glob": "TestSubjextData/offers/history/*-active_offer_history.jsonl",
            "remote_rel_dir": "offers/history",
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
            "local_rel_glob": "TestSubjextData/traffic/history/*-TrafficBeacon-history.jsonl",
            "remote_rel_dir": "traffic/history",
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
CONSOLE_LOG_PATH = os.path.join(SCRIPT_DIR, "pythonista_console.log")

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


def _append_console_log(message):
    try:
        line = "%s\n" % message
        with open(CONSOLE_LOG_PATH, "a", encoding="utf-8") as handle:
            handle.write(line)
        if os.path.exists(CONSOLE_LOG_PATH) and os.path.getsize(CONSOLE_LOG_PATH) < MAX_CONSOLE_LOG_BYTES:
            return
        with open(CONSOLE_LOG_PATH, "r", encoding="utf-8", errors="ignore") as handle:
            lines = handle.readlines()
        if len(lines) > MAX_CONSOLE_LOG_LINES:
            with open(CONSOLE_LOG_PATH, "w", encoding="utf-8") as handle:
                handle.writelines(lines[-TRIMMED_CONSOLE_LOG_LINES:])
    except Exception:
        pass


def _log(message):
    text = "%s" % (message or "")
    print(text)
    _append_console_log(text)


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


def _sha1_bytes(raw):
    return hashlib.sha1(raw).hexdigest()


def _extract_version_from_text(text):
    value = "%s" % (text or "")
    version_match = re.search(r"^\s*#\s*version:\s*(.+?)\s*$", value, re.MULTILINE)
    build_match = re.search(r'^\s*SCRIPT_BUILD\s*=\s*["\'](.+?)["\']\s*$', value, re.MULTILINE)
    return {
        "version_comment": (version_match.group(1).strip() if version_match else ""),
        "script_build": (build_match.group(1).strip() if build_match else ""),
    }


def _read_local_version(path):
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return _extract_version_from_text(handle.read())
    except Exception:
        return {
            "version_comment": "",
            "script_build": "",
        }


def _read_local_file_sha1(path):
    try:
        with open(path, "rb") as handle:
            return _sha1_bytes(handle.read())
    except Exception:
        return ""


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


def _download_manifest():
    url = "%s/%s" % (REPO_RAW_ROOT, MANIFEST_REMOTE_NAME)
    try:
        payload = json.loads(_download_text(url))
    except Exception:
        return {}
    files = payload.get("files")
    if not isinstance(files, dict):
        return {}
    return payload


def _manifest_entry_for(item, manifest_payload):
    if not manifest_payload:
        return {}
    files = manifest_payload.get("files") or {}
    entry = files.get(item["local_name"])
    return entry if isinstance(entry, dict) else {}


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
    previous_marker = os.environ.get("PYTHONISTA_UPDATE_CHAIN", "")
    previous_build = os.environ.get("PYTHONISTA_UPDATE_CHAIN_BUILD", "")
    previous_started = os.environ.get("PYTHONISTA_UPDATE_CHAIN_STARTED_AT", "")
    os.environ["PYTHONISTA_UPDATE_CHAIN"] = "update_from_github"
    os.environ["PYTHONISTA_UPDATE_CHAIN_BUILD"] = SCRIPT_BUILD
    os.environ["PYTHONISTA_UPDATE_CHAIN_STARTED_AT"] = _timestamp()
    try:
        runpy.run_path(PRIVATE_UPLOAD_SCRIPT_PATH, run_name="__main__")
    except SystemExit as exc:
        code = exc.code if isinstance(exc.code, int) else 0
        result["exit_code"] = code
        if code not in (0, None):
            result["error"] = "Uploader exited with code %s" % code
    except Exception as exc:
        result["error"] = "%s" % exc
    finally:
        if previous_marker:
            os.environ["PYTHONISTA_UPDATE_CHAIN"] = previous_marker
        else:
            os.environ.pop("PYTHONISTA_UPDATE_CHAIN", None)
        if previous_build:
            os.environ["PYTHONISTA_UPDATE_CHAIN_BUILD"] = previous_build
        else:
            os.environ.pop("PYTHONISTA_UPDATE_CHAIN_BUILD", None)
        if previous_started:
            os.environ["PYTHONISTA_UPDATE_CHAIN_STARTED_AT"] = previous_started
        else:
            os.environ.pop("PYTHONISTA_UPDATE_CHAIN_STARTED_AT", None)

    status_payload = _read_existing_json(PRIVATE_UPLOAD_STATUS_PATH)
    if status_payload:
        result["status"] = status_payload
        result["ok"] = bool(status_payload.get("ok"))
    else:
        result["ok"] = "error" not in result
    return result


def _summarize_private_upload(result):
    summary = {
        "ok": bool(result.get("ok")),
        "ran": bool(result.get("ran")),
    }
    status_payload = result.get("status") or {}
    if status_payload:
        upload_results = status_payload.get("results") or []
        summary["script_build"] = status_payload.get("script_build") or ""
        summary["timestamp"] = status_payload.get("timestamp") or ""
        summary["repo"] = status_payload.get("repo") or ""
        summary["uploaded_count"] = len(
            [item for item in upload_results if item.get("status") == "uploaded"]
        )
        summary["skipped_unchanged_count"] = len(
            [item for item in upload_results if item.get("status") == "skipped_unchanged"]
        )
        summary["missing_count"] = len(
            [item for item in upload_results if item.get("status") == "missing_local"]
        )
        summary["too_large_count"] = len(
            [item for item in upload_results if item.get("status") == "too_large"]
        )
        summary["manifest_uploaded"] = bool(status_payload.get("manifest_uploaded"))
    if result.get("error"):
        summary["error"] = result.get("error")
    if "exit_code" in result:
        summary["exit_code"] = result.get("exit_code")
    return summary


def _update_one_file(item, manifest_payload):
    url = "%s/%s" % (REPO_RAW_ROOT, item["remote_name"])
    target_path = os.path.join(SCRIPT_DIR, item["local_name"])
    local_version = _read_local_version(target_path)
    local_sha1 = _read_local_file_sha1(target_path)
    manifest_entry = _manifest_entry_for(item, manifest_payload)
    remote_build = ("%s" % (manifest_entry.get("script_build") or "")).strip()
    remote_version_comment = ("%s" % (manifest_entry.get("version_comment") or "")).strip()
    remote_sha1 = ("%s" % (manifest_entry.get("content_sha1") or "")).strip()
    skip_reason = ""
    if os.path.exists(target_path) and remote_sha1 and local_sha1 == remote_sha1:
        skip_reason = "content_sha1"
    elif (
        os.path.exists(target_path)
        and remote_build
        and local_version["script_build"] == remote_build
        and local_version["script_build"] != ""
    ):
        skip_reason = "script_build"
    elif (
        os.path.exists(target_path)
        and (not remote_build)
        and remote_version_comment
        and local_version["version_comment"] == remote_version_comment
        and local_version["version_comment"] != ""
    ):
        skip_reason = "version_comment"
    if (
        os.path.exists(target_path)
        and skip_reason
    ):
        return {
            "label": item["label"],
            "remote_name": item["remote_name"],
            "local_name": item["local_name"],
            "target_path": target_path,
            "download_url": url,
            "bytes": int(manifest_entry.get("bytes") or 0),
            "version_comment": remote_version_comment or local_version["version_comment"],
            "script_build": remote_build,
            "content_sha1": remote_sha1 or local_sha1,
            "status": "skipped_unchanged",
            "skip_reason": skip_reason,
        }
    source_text = _download_text(url)
    version_info = _extract_version_from_text(source_text)
    if "404: Not Found" in source_text and len(source_text.strip()) <= 20:
        raise RuntimeError("GitHub returned 404 for %s" % item["remote_name"])
    if "import " not in source_text and "def " not in source_text:
        raise RuntimeError("Downloaded content for %s does not look like Python code." % item["remote_name"])
    content_sha1 = _sha1_bytes(source_text.encode("utf-8"))
    _write_text(target_path, source_text)
    return {
        "label": item["label"],
        "remote_name": item["remote_name"],
        "local_name": item["local_name"],
        "target_path": target_path,
        "download_url": url,
        "bytes": len(source_text.encode("utf-8")),
        "version_comment": version_info["version_comment"],
        "script_build": version_info["script_build"],
        "content_sha1": content_sha1,
        "status": "downloaded",
    }


def main():
    started = time.perf_counter()
    _log("===== updater session start | %s | %s =====" % (_timestamp(), SCRIPT_BUILD))
    manifest_payload = _download_manifest()
    results = []
    for item in FILE_MAP:
        results.append(_update_one_file(item, manifest_payload))
    private_sync_bootstrap = _bootstrap_private_sync_config()
    downloaded_count = len([item for item in results if item.get("status") == "downloaded"])
    skipped_due_to_code_update = downloaded_count > 0
    if skipped_due_to_code_update:
        private_upload_result = {
            "ok": True,
            "ran": False,
            "skipped_due_to_code_update": True,
            "downloaded_count": downloaded_count,
            "error": "",
        }
    else:
        private_upload_result = _run_private_uploader()

    payload = {
        "ok": bool(private_upload_result.get("ok")),
        "timestamp": _timestamp(),
        "script_build": SCRIPT_BUILD,
        "script_dir": SCRIPT_DIR,
        "manifest_used": bool(manifest_payload),
        "manifest_build": ("%s" % (manifest_payload.get("manifest_build") or "")).strip() if manifest_payload else "",
        "files": results,
        "files_summary": {
            result["local_name"]: {
                "bytes": result["bytes"],
                "version_comment": result["version_comment"],
                "script_build": result["script_build"],
                "content_sha1": result.get("content_sha1") or "",
                "status": result.get("status") or "",
                "skip_reason": result.get("skip_reason") or "",
            }
            for result in results
        },
        "private_sync_bootstrap": private_sync_bootstrap,
        "private_upload": private_upload_result,
        "private_upload_summary": _summarize_private_upload(private_upload_result),
        "elapsed_seconds": round(time.perf_counter() - started, 3),
    }
    _write_status(payload)

    _log("[updater] Checked %d file(s) in %s" % (len(results), SCRIPT_DIR))
    for result in results:
        _log(
            "[updater] %s -> %s | %s | %d bytes"
            % (
                result["remote_name"],
                result["local_name"],
                result.get("status") or "unknown",
                result["bytes"],
            )
        )
    if private_upload_result.get("skipped_due_to_code_update"):
        _log(
            "[updater] private upload deferred | code_updated=%s"
            % private_upload_result.get("downloaded_count", 0)
        )
    elif private_upload_result.get("ok"):
        upload_summary = _summarize_private_upload(private_upload_result)
        _log(
            "[updater] private upload ok | uploaded=%s skipped=%s missing=%s too_large=%s | at=%s"
            % (
                upload_summary.get("uploaded_count", 0),
                upload_summary.get("skipped_unchanged_count", 0),
                upload_summary.get("missing_count", 0),
                upload_summary.get("too_large_count", 0),
                upload_summary.get("timestamp") or "",
            )
        )
    else:
        _log("[updater] private upload failed: %s" % (private_upload_result.get("error") or "unknown"))
    _log("[updater] session end | %.3fs" % (time.perf_counter() - started))


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
        _log("[updater] failed: %s" % exc)
        raise SystemExit(1)
    raise SystemExit(0)
