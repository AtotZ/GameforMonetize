import base64
import datetime
import glob
import hashlib
# version: 2026-06-27-private-data-upload-line-grid-v17
import json
import os
import re
import socket
import time
import urllib.error
import urllib.parse
import urllib.request

try:
    from objc_util import ObjCClass
except Exception:
    ObjCClass = None


SCRIPT_BUILD = "2026-06-27-private-upload-line-grid-v17"
API_ROOT = "https://api.github.com"
REQUEST_TIMEOUT_SECONDS = 8
REQUEST_RETRY_ATTEMPTS = 2
REQUEST_RETRY_SLEEP_SECONDS = 0.75
MAX_UPLOAD_BYTES = 2 * 1024 * 1024
MAX_CONSOLE_LOG_LINES = 400
TRIMMED_CONSOLE_LOG_LINES = 250
MAX_CONSOLE_LOG_BYTES = 48 * 1024
POWER_LITE_BATTERY_MAX_PCT = 18
FORCE_FULL_UPLOAD_BACKLOG_COUNT = 12
FORCE_FULL_UPLOAD_BACKLOG_DAYS = 2
FORCE_FULL_UPLOAD_CONSECUTIVE_RUNS = 3
POWER_LITE_ALLOWED_LABELS = {
    "active_offer",
    "offer_latest_debug",
    "traffic_latest",
    "traffic_db",
    "traffic_line_grid",
    "route_db",
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
ROOT_DIR = os.path.expanduser("~/Documents")
DATA_ROOT_DIR = os.path.join(ROOT_DIR, "TestSubjextData")
CONFIG_PATH = os.path.join(SCRIPT_DIR, "github_private_sync_config.json")
EXAMPLE_CONFIG_PATH = os.path.join(SCRIPT_DIR, "github_private_sync_config.example.json")
STATUS_PATH = os.path.join(SCRIPT_DIR, "github_private_upload_status.json")
CACHE_PATH = os.path.join(SCRIPT_DIR, "github_private_upload_cache.json")
CONSOLE_LOG_PATH = os.path.join(SCRIPT_DIR, "pythonista_console.log")
TOKEN_FILE_CANDIDATES = [
    os.path.join(SCRIPT_DIR, "github_private_sync_token.txt"),
    os.path.join(SCRIPT_DIR, "Secrets.txt"),
]

DEFAULT_FILE_SPECS = [
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
        "label": "saved_trip_ledger",
        "local_rel_path": "TestSubjextData/logs/TripLog-OnisAI-PostcodeIsolation.jsonl",
        "remote_rel_path": "logs/TripLog-OnisAI-PostcodeIsolation.jsonl",
    },
    {
        "label": "saved_trip_log",
        "local_rel_path": "TestSubjextData/logs/TripLog-OnisAI-PostcodeIsolation.txt",
        "remote_rel_path": "logs/TripLog-OnisAI-PostcodeIsolation.txt",
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
        "label": "traffic_line_grid",
        "local_rel_path": "TestSubjextData/traffic/TrafficBeacon-line-grid.json",
        "remote_rel_path": "traffic/TrafficBeacon-line-grid.json",
    },
    {
        "label": "route_db",
        "local_rel_path": "TestSubjextData/traffic/TrafficRoute-db.json",
        "remote_rel_path": "traffic/TrafficRoute-db.json",
    },
    {
        "label": "route_point_db",
        "local_rel_path": "TestSubjextData/traffic/TrafficBeacon-route-points.json",
        "remote_rel_path": "traffic/TrafficBeacon-route-points.json",
    },
]

EXAMPLE_CONFIG = {
    "owner": "AtotZ",
    "repo": "YOUR_PRIVATE_DATA_REPO",
    "branch": "main",
    "token": "github_pat_your_fine_grained_token_here",
    "remote_root": "pythonista-data",
    "commit_message_prefix": "Pythonista data sync",
    "commit_user_name": "",
    "commit_user_email": "",
    "files": DEFAULT_FILE_SPECS,
}


def _timestamp():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _power_snapshot():
    snapshot = {
        "available": False,
        "battery_level_pct": None,
        "battery_state": "",
        "battery_state_code": None,
        "low_power_mode": None,
        "thermal_state": "",
        "thermal_state_code": None,
    }
    if ObjCClass is None:
        return snapshot
    try:
        UIDevice = ObjCClass("UIDevice")
        NSProcessInfo = ObjCClass("NSProcessInfo")
        device = UIDevice.currentDevice()
        previous_monitoring = bool(device.isBatteryMonitoringEnabled())
        if not previous_monitoring:
            device.setBatteryMonitoringEnabled_(True)
        try:
            level = float(device.batteryLevel())
            state_code = int(device.batteryState())
            process = NSProcessInfo.processInfo()
            low_power_mode = bool(process.isLowPowerModeEnabled())
            thermal_code = int(process.thermalState())
        finally:
            if not previous_monitoring:
                device.setBatteryMonitoringEnabled_(False)
        snapshot["available"] = True
        snapshot["battery_level_pct"] = int(round(level * 100.0)) if level >= 0 else None
        snapshot["battery_state_code"] = state_code
        snapshot["battery_state"] = {
            0: "unknown",
            1: "unplugged",
            2: "charging",
            3: "full",
        }.get(state_code, "unknown")
        snapshot["low_power_mode"] = low_power_mode
        snapshot["thermal_state_code"] = thermal_code
        snapshot["thermal_state"] = {
            0: "nominal",
            1: "fair",
            2: "serious",
            3: "critical",
        }.get(thermal_code, "unknown")
    except Exception:
        return snapshot
    return snapshot


def _should_use_power_lite_mode(snapshot):
    if not isinstance(snapshot, dict) or not snapshot.get("available"):
        return False
    if snapshot.get("thermal_state") in ("serious", "critical"):
        return True
    if snapshot.get("low_power_mode") is True:
        return True
    battery_level_pct = snapshot.get("battery_level_pct")
    battery_state = ("%s" % (snapshot.get("battery_state") or "")).lower()
    return (
        isinstance(battery_level_pct, int)
        and battery_level_pct <= POWER_LITE_BATTERY_MAX_PCT
        and battery_state not in ("charging", "full")
    )


def _apply_power_lite_filter(file_specs):
    kept = []
    deferred = []
    for item in file_specs or []:
        label = ("%s" % (item.get("label") or "")).strip()
        if label in POWER_LITE_ALLOWED_LABELS:
            kept.append(item)
        else:
            deferred.append(dict(item or {}))
    return kept, deferred


def _safe_int(value, default=0):
    try:
        return int(value)
    except Exception:
        return default


def _deferred_signature(item):
    local_rel_path = _normalize_rel_path(item.get("local_rel_path") or "")
    local_rel_glob = _normalize_rel_path(item.get("local_rel_glob") or "")
    remote_rel_path = _normalize_rel_path(item.get("remote_rel_path") or "")
    remote_rel_dir = _normalize_rel_path(item.get("remote_rel_dir") or "")
    return local_rel_path or local_rel_glob or remote_rel_path or remote_rel_dir or ("%s" % (item.get("label") or "")).strip()


def _deferred_day_key(item):
    probe = " ".join(
        [
            "%s" % (item.get("local_rel_path") or ""),
            "%s" % (item.get("local_rel_glob") or ""),
            "%s" % (item.get("remote_rel_path") or ""),
            "%s" % (item.get("remote_rel_dir") or ""),
        ]
    )
    match = re.search(r"\b(20\d{2}-\d{2}-\d{2})\b", probe)
    return match.group(1) if match else ""


def _merge_deferred_backlog(previous_entries, deferred_items, timestamp_text):
    merged = {}
    if isinstance(previous_entries, dict):
        for signature, entry in previous_entries.items():
            if not isinstance(entry, dict):
                continue
            merged["%s" % signature] = {
                "label": "%s" % (entry.get("label") or ""),
                "signature": "%s" % (entry.get("signature") or signature),
                "day_key": "%s" % (entry.get("day_key") or ""),
                "local_rel_path": _normalize_rel_path(entry.get("local_rel_path") or ""),
                "remote_rel_path": _normalize_rel_path(entry.get("remote_rel_path") or ""),
                "first_deferred_at": "%s" % (entry.get("first_deferred_at") or timestamp_text),
                "last_deferred_at": "%s" % (entry.get("last_deferred_at") or timestamp_text),
            }
    for item in deferred_items or []:
        signature = _deferred_signature(item)
        if not signature:
            continue
        existing = merged.get(signature) or {}
        merged[signature] = {
            "label": ("%s" % (item.get("label") or "")).strip() or signature,
            "signature": signature,
            "day_key": _deferred_day_key(item),
            "local_rel_path": _normalize_rel_path(item.get("local_rel_path") or item.get("local_rel_glob") or ""),
            "remote_rel_path": _normalize_rel_path(item.get("remote_rel_path") or item.get("remote_rel_dir") or ""),
            "first_deferred_at": "%s" % (existing.get("first_deferred_at") or timestamp_text),
            "last_deferred_at": timestamp_text,
        }
    return merged


def _deferred_backlog_summary(entries):
    if not isinstance(entries, dict):
        return {"count": 0, "day_keys": [], "day_count": 0}
    day_keys = sorted(
        {
            ("%s" % ((entry or {}).get("day_key") or "")).strip()
            for entry in entries.values()
            if ("%s" % ((entry or {}).get("day_key") or "")).strip()
        }
    )
    return {
        "count": len(entries),
        "day_keys": day_keys,
        "day_count": len(day_keys),
    }


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


def _send_local_notification(title, body):
    if ObjCClass is None:
        return False
    try:
        UNUserNotificationCenter = ObjCClass("UNUserNotificationCenter")
        UNMutableNotificationContent = ObjCClass("UNMutableNotificationContent")
        UNNotificationRequest = ObjCClass("UNNotificationRequest")
        UNTimeIntervalNotificationTrigger = ObjCClass("UNTimeIntervalNotificationTrigger")
        UNNotificationSound = ObjCClass("UNNotificationSound")
        center = UNUserNotificationCenter.currentNotificationCenter()
        content = UNMutableNotificationContent.alloc().init()
        content.setTitle_("%s" % (title or "Pythonista"))
        content.setBody_("%s" % (body or ""))
        content.setSound_(UNNotificationSound.defaultSound())
        trigger = UNTimeIntervalNotificationTrigger.triggerWithTimeInterval_repeats_(0.2, False)
        identifier = "PrivateUploadNotif-%d" % int(time.time() * 1000)
        request = UNNotificationRequest.requestWithIdentifier_content_trigger_(identifier, content, trigger)
        center.addNotificationRequest_withCompletionHandler_(request, None)
        return True
    except Exception:
        return False


def _read_invocation_context():
    invoked_by = ("%s" % (os.environ.get("PYTHONISTA_UPDATE_CHAIN") or "")).strip()
    invoked_by_build = ("%s" % (os.environ.get("PYTHONISTA_UPDATE_CHAIN_BUILD") or "")).strip()
    invoked_started_at = ("%s" % (os.environ.get("PYTHONISTA_UPDATE_CHAIN_STARTED_AT") or "")).strip()
    return {
        "invoked_by": invoked_by or "direct",
        "invoked_by_build": invoked_by_build,
        "invoked_started_at": invoked_started_at,
        "update_chain_ok": bool(invoked_by),
    }


def _ensure_example_config():
    if os.path.exists(EXAMPLE_CONFIG_PATH):
        return
    with open(EXAMPLE_CONFIG_PATH, "w", encoding="utf-8") as handle:
        json.dump(EXAMPLE_CONFIG, handle, ensure_ascii=False, indent=2)


def _read_json(path):
    try:
        with open(path, "r", encoding="utf-8") as handle:
            payload = json.load(handle)
        if isinstance(payload, dict):
            return payload
    except Exception:
        pass
    return {}


def _write_json(path, payload):
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)


def _sha1_bytes(raw):
    return hashlib.sha1(raw).hexdigest()


def _read_first_line(path):
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as handle:
            return ("%s" % (handle.readline() or "")).strip()
    except Exception:
        return ""


def _normalize_rel_path(value):
    return ("%s" % (value or "")).replace("\\", "/").strip().strip("/")


def _copy_file_spec(item):
    return {key: value for key, value in (item or {}).items()}


def _normalize_file_specs(file_specs):
    normalized = []
    seen_labels = set()
    for item in file_specs or []:
        if not isinstance(item, dict):
            continue
        candidate = _copy_file_spec(item)
        local_path = _normalize_rel_path(candidate.get("local_rel_path") or "")
        remote_path = _normalize_rel_path(candidate.get("remote_rel_path") or "")
        if local_path in (
            "TestSubjextData/offers/active_offer_history.jsonl",
            "TestSubjextData/traffic/TrafficBeacon-history.json",
        ):
            continue
        if remote_path in (
            "offers/active_offer_history.jsonl",
            "traffic/TrafficBeacon-history.json",
        ):
            continue
        normalized.append(candidate)
        label = ("%s" % (candidate.get("label") or "")).strip()
        if label:
            seen_labels.add(label)
    for item in DEFAULT_FILE_SPECS:
        label = ("%s" % (item.get("label") or "")).strip()
        if label and label in seen_labels:
            continue
        normalized.append(_copy_file_spec(item))
    return normalized


def _expand_file_specs(file_specs):
    expanded = []
    for item in file_specs or []:
        local_glob = _normalize_rel_path(item.get("local_rel_glob") or "")
        remote_dir = _normalize_rel_path(item.get("remote_rel_dir") or "")
        if local_glob and remote_dir:
            pattern = os.path.join(ROOT_DIR, *local_glob.split("/"))
            for match in sorted([path for path in glob.glob(pattern) if os.path.isfile(path)]):
                rel_local = os.path.relpath(match, ROOT_DIR).replace("\\", "/")
                expanded.append(
                    {
                        "label": ("%s" % (item.get("label") or os.path.basename(match))).strip(),
                        "local_rel_path": rel_local,
                        "remote_rel_path": "%s/%s" % (remote_dir, os.path.basename(match)),
                    }
                )
            continue
        expanded.append(_copy_file_spec(item))
    return expanded


def _read_bootstrap_token():
    for path in TOKEN_FILE_CANDIDATES:
        token = _read_first_line(path)
        if token.startswith("github_pat_") or token.startswith("ghp_"):
            return token, path
    return "", ""


def _maybe_bootstrap_config_from_token():
    if os.path.exists(CONFIG_PATH):
        return None
    token, source_path = _read_bootstrap_token()
    if not token:
        return None
    payload = dict(EXAMPLE_CONFIG)
    payload["repo"] = "UploadData"
    payload["token"] = token
    _write_json(CONFIG_PATH, payload)
    return {
        "config_path": CONFIG_PATH,
        "token_source": source_path,
        "repo": "%s/%s" % (payload["owner"], payload["repo"]),
    }


def _load_config():
    _ensure_example_config()
    bootstrap = _maybe_bootstrap_config_from_token()
    payload = _read_json(CONFIG_PATH)
    if not payload:
        raise RuntimeError(
            "Missing %s. Copy %s to github_private_sync_config.json and fill repo + token."
            % (os.path.basename(CONFIG_PATH), os.path.basename(EXAMPLE_CONFIG_PATH))
        )
    owner = ("%s" % (payload.get("owner") or "")).strip()
    repo = ("%s" % (payload.get("repo") or "")).strip()
    token = ("%s" % (payload.get("token") or "")).strip()
    if not owner or not repo or not token:
        raise RuntimeError("github_private_sync_config.json must include owner, repo, and token.")
    files = payload.get("files")
    if not isinstance(files, list) or not files:
        files = [_copy_file_spec(item) for item in DEFAULT_FILE_SPECS]
    files = _expand_file_specs(_normalize_file_specs(files))
    return {
        "owner": owner,
        "repo": repo,
        "branch": ("%s" % (payload.get("branch") or "main")).strip() or "main",
        "token": token,
        "remote_root": _normalize_rel_path(payload.get("remote_root") or "pythonista-data"),
        "commit_message_prefix": ("%s" % (payload.get("commit_message_prefix") or "Pythonista data sync")).strip(),
        "commit_user_name": ("%s" % (payload.get("commit_user_name") or "")).strip(),
        "commit_user_email": ("%s" % (payload.get("commit_user_email") or "")).strip(),
        "files": files,
        "bootstrap": bootstrap,
    }


def _repo_signature(config):
    return "%s/%s@%s|%s" % (
        config["owner"],
        config["repo"],
        config["branch"],
        config["remote_root"],
    )


def _load_cache(config):
    payload = _read_json(CACHE_PATH)
    repo_signature = _repo_signature(config)
    if payload.get("repo_signature") != repo_signature:
        return {
            "repo_signature": repo_signature,
            "files": {},
        }
    files = payload.get("files")
    if not isinstance(files, dict):
        files = {}
    return {
        "repo_signature": repo_signature,
        "files": files,
    }


def _save_cache(cache_payload):
    _write_json(CACHE_PATH, cache_payload)


def _api_request(url, token, method="GET", body=None):
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": "Bearer %s" % token,
        "X-GitHub-Api-Version": "2026-03-10",
        "User-Agent": "PythonistaPrivateUploader/1.0",
    }
    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    raw = b""
    last_error = None
    for attempt in range(1, REQUEST_RETRY_ATTEMPTS + 1):
        try:
            with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
                raw = response.read()
            last_error = None
            break
        except Exception as exc:
            last_error = exc
            is_timeout = isinstance(exc, socket.timeout) or isinstance(exc, TimeoutError)
            if not is_timeout and isinstance(exc, urllib.error.URLError):
                reason = getattr(exc, "reason", None)
                is_timeout = isinstance(reason, socket.timeout) or isinstance(reason, TimeoutError) or ("timed out" in ("%s" % reason).lower())
            if not is_timeout and "timed out" in ("%s" % exc).lower():
                is_timeout = True
            if (not is_timeout) or attempt >= REQUEST_RETRY_ATTEMPTS:
                raise
            time.sleep(REQUEST_RETRY_SLEEP_SECONDS)
    if last_error is not None:
        raise last_error
    if not raw:
        return {}
    return json.loads(raw.decode("utf-8"))


def _get_remote_sha(config, remote_path):
    encoded_path = urllib.parse.quote(remote_path, safe="/")
    url = "%s/repos/%s/%s/contents/%s?ref=%s" % (
        API_ROOT,
        urllib.parse.quote(config["owner"], safe=""),
        urllib.parse.quote(config["repo"], safe=""),
        encoded_path,
        urllib.parse.quote(config["branch"], safe=""),
    )
    try:
        payload = _api_request(url, config["token"])
        return ("%s" % (payload.get("sha") or "")).strip()
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return ""
        raise


def _put_file_contents(config, remote_path, raw, message, sha=""):
    body = {
        "message": message,
        "content": base64.b64encode(raw).decode("ascii"),
        "branch": config["branch"],
    }
    if sha:
        body["sha"] = sha
    if config["commit_user_name"] and config["commit_user_email"]:
        body["committer"] = {
            "name": config["commit_user_name"],
            "email": config["commit_user_email"],
        }
    encoded_path = urllib.parse.quote(remote_path, safe="/")
    url = "%s/repos/%s/%s/contents/%s" % (
        API_ROOT,
        urllib.parse.quote(config["owner"], safe=""),
        urllib.parse.quote(config["repo"], safe=""),
        encoded_path,
    )
    return _api_request(url, config["token"], method="PUT", body=body)


def _upload_one(config, item, cache_payload):
    local_rel_path = _normalize_rel_path(item.get("local_rel_path") or "")
    remote_rel_path = _normalize_rel_path(item.get("remote_rel_path") or "")
    if not local_rel_path or not remote_rel_path:
        raise RuntimeError("Every file entry must include local_rel_path and remote_rel_path.")
    local_path = os.path.join(ROOT_DIR, *local_rel_path.split("/"))
    remote_path = remote_rel_path
    if config["remote_root"]:
        remote_path = "%s/%s" % (config["remote_root"], remote_rel_path)
    if not os.path.exists(local_path):
        return {
            "label": item.get("label") or remote_rel_path,
            "local_rel_path": local_rel_path,
            "remote_rel_path": remote_path,
            "status": "missing_local",
        }
    stat_result = os.stat(local_path)
    raw = open(local_path, "rb").read()
    if len(raw) > MAX_UPLOAD_BYTES:
        return {
            "label": item.get("label") or remote_rel_path,
            "local_rel_path": local_rel_path,
            "remote_rel_path": remote_rel_path,
            "status": "too_large",
            "bytes": len(raw),
        }
    content_sha1 = _sha1_bytes(raw)
    cached = cache_payload["files"].get(remote_path) or {}
    message = "%s | %s | %s" % (
        config["commit_message_prefix"],
        item.get("label") or remote_rel_path,
        _timestamp(),
    )
    sha = ("%s" % (cached.get("remote_sha") or "")).strip()
    try:
        payload = _put_file_contents(config, remote_path, raw, message, sha=sha)
    except urllib.error.HTTPError as exc:
        if exc.code not in (409, 422):
            raise
        sha = _get_remote_sha(config, remote_path)
        payload = _put_file_contents(config, remote_path, raw, message, sha=sha)
    commit = payload.get("commit") or {}
    content = payload.get("content") or {}
    remote_sha = ("%s" % (content.get("sha") or "")).strip()
    result = {
        "label": item.get("label") or remote_rel_path,
        "local_rel_path": local_rel_path,
        "remote_rel_path": remote_path,
        "status": "uploaded",
        "bytes": len(raw),
        "content_sha1": content_sha1,
        "sha": remote_sha,
        "commit_sha": ("%s" % (commit.get("sha") or "")).strip(),
    }
    cache_payload["files"][remote_path] = {
        "content_sha1": content_sha1,
        "bytes": len(raw),
        "remote_sha": remote_sha,
        "local_mtime_ns": int(getattr(stat_result, "st_mtime_ns", 0)),
        "last_uploaded_at": _timestamp(),
        "label": item.get("label") or remote_rel_path,
    }
    return result


def _build_manifest(upload_results, invocation_context):
    uploaded = [item for item in upload_results if item.get("status") == "uploaded"]
    missing = [item for item in upload_results if item.get("status") == "missing_local"]
    too_large = [item for item in upload_results if item.get("status") == "too_large"]
    return {
        "updated_at": _timestamp(),
        "script_build": SCRIPT_BUILD,
        "invoked_by": invocation_context.get("invoked_by") or "direct",
        "invoked_by_build": invocation_context.get("invoked_by_build") or "",
        "invoked_started_at": invocation_context.get("invoked_started_at") or "",
        "update_chain_ok": bool(invocation_context.get("update_chain_ok")),
        "uploaded_count": len(uploaded),
        "missing_count": len(missing),
        "too_large_count": len(too_large),
        "uploaded_files": uploaded,
        "missing_files": missing,
        "too_large_files": too_large,
    }


def _upload_manifest(config, manifest):
    raw = json.dumps(manifest, ensure_ascii=False, indent=2).encode("utf-8")
    remote_path = "sync_manifest.json"
    if config["remote_root"]:
        remote_path = "%s/%s" % (config["remote_root"], remote_path)
    sha = _get_remote_sha(config, remote_path)
    body = {
        "message": "%s | sync_manifest | %s" % (config["commit_message_prefix"], _timestamp()),
        "content": base64.b64encode(raw).decode("ascii"),
        "branch": config["branch"],
    }
    if sha:
        body["sha"] = sha
    if config["commit_user_name"] and config["commit_user_email"]:
        body["committer"] = {
            "name": config["commit_user_name"],
            "email": config["commit_user_email"],
        }
    url = "%s/repos/%s/%s/contents/%s" % (
        API_ROOT,
        urllib.parse.quote(config["owner"], safe=""),
        urllib.parse.quote(config["repo"], safe=""),
        urllib.parse.quote(remote_path, safe="/"),
    )
    _api_request(url, config["token"], method="PUT", body=body)


def main():
    started = time.perf_counter()
    now_text = _timestamp()
    _log("[private-upload] session start | %s | %s" % (now_text, SCRIPT_BUILD))
    config = _load_config()
    power_snapshot = _power_snapshot()
    previous_status = _read_json(STATUS_PATH)
    cache_payload = _load_cache(config)
    invocation_context = _read_invocation_context()
    file_specs = list(config["files"] or [])
    power_lite_requested = _should_use_power_lite_mode(power_snapshot)
    power_lite_mode = power_lite_requested
    deferred_items = []
    deferred_labels = []
    power_lite_force_reason = ""
    deferred_backlog_entries = {}
    deferred_consecutive_runs = 0
    if power_lite_requested:
        previous_deferred_backlog = {}
        if isinstance(previous_status, dict):
            previous_deferred_backlog = previous_status.get("deferred_backlog_entries") or {}
        previous_consecutive_runs = _safe_int(
            (previous_status or {}).get("deferred_consecutive_runs"),
            0,
        )
        file_specs_power_lite, deferred_items = _apply_power_lite_filter(file_specs)
        projected_backlog_entries = _merge_deferred_backlog(
            previous_deferred_backlog,
            deferred_items,
            now_text,
        )
        projected_backlog_summary = _deferred_backlog_summary(projected_backlog_entries)
        projected_consecutive_runs = previous_consecutive_runs + (1 if deferred_items else 0)
        if projected_backlog_summary["count"] >= FORCE_FULL_UPLOAD_BACKLOG_COUNT:
            power_lite_force_reason = "backlog_count"
        elif projected_backlog_summary["day_count"] >= FORCE_FULL_UPLOAD_BACKLOG_DAYS:
            power_lite_force_reason = "backlog_days"
        elif projected_consecutive_runs >= FORCE_FULL_UPLOAD_CONSECUTIVE_RUNS:
            power_lite_force_reason = "consecutive_runs"
        if power_lite_force_reason:
            power_lite_mode = False
            deferred_items = []
            deferred_labels = []
            _log(
                "[private-upload] power-lite bypass | reason=%s backlog=%d days=%d consecutive=%d"
                % (
                    power_lite_force_reason,
                    projected_backlog_summary["count"],
                    projected_backlog_summary["day_count"],
                    projected_consecutive_runs,
                )
            )
        else:
            file_specs = file_specs_power_lite
            deferred_labels = [
                ("%s" % (item.get("label") or "")).strip() or _deferred_signature(item)
                for item in deferred_items
            ]
            deferred_backlog_entries = projected_backlog_entries
            deferred_consecutive_runs = projected_consecutive_runs
            backlog_summary = _deferred_backlog_summary(deferred_backlog_entries)
            _log(
                "[private-upload] power-lite mode | battery=%s%% state=%s low_power=%s thermal=%s deferred=%d backlog=%d days=%d consecutive=%d"
                % (
                    power_snapshot.get("battery_level_pct"),
                    power_snapshot.get("battery_state") or "unknown",
                    "yes" if power_snapshot.get("low_power_mode") else "no",
                    power_snapshot.get("thermal_state") or "unknown",
                    len(deferred_labels),
                    backlog_summary["count"],
                    backlog_summary["day_count"],
                    deferred_consecutive_runs,
                )
            )
    if not power_lite_mode:
        deferred_backlog_entries = {}
        deferred_consecutive_runs = 0
    results = []
    failed_count = 0
    for item in file_specs:
        try:
            results.append(_upload_one(config, item, cache_payload))
        except Exception as exc:
            failed_count += 1
            results.append(
                {
                    "label": item.get("label") or item.get("remote_rel_path") or "",
                    "local_rel_path": _normalize_rel_path(item.get("local_rel_path") or ""),
                    "remote_rel_path": _normalize_rel_path(item.get("remote_rel_path") or ""),
                    "status": "upload_failed",
                    "error": "%s" % exc,
                }
            )
    for item, label in zip(deferred_items, deferred_labels):
        results.append(
            {
                "label": label,
                "local_rel_path": _normalize_rel_path(item.get("local_rel_path") or item.get("local_rel_glob") or ""),
                "remote_rel_path": _normalize_rel_path(item.get("remote_rel_path") or item.get("remote_rel_dir") or ""),
                "status": "deferred_power_save",
            }
        )
    manifest = _build_manifest(results, invocation_context)
    should_upload_manifest = any(item.get("status") == "uploaded" for item in results)
    manifest_error = ""
    if should_upload_manifest:
        try:
            _upload_manifest(config, manifest)
        except Exception as exc:
            manifest_error = "%s" % exc
            failed_count += 1
    _save_cache(cache_payload)
    status = {
        "ok": failed_count == 0,
        "timestamp": now_text,
        "script_build": SCRIPT_BUILD,
        "invocation_context": invocation_context,
        "repo": "%s/%s" % (config["owner"], config["repo"]),
        "branch": config["branch"],
        "remote_root": config["remote_root"],
        "bootstrap": config.get("bootstrap"),
        "power_snapshot": power_snapshot,
        "power_lite_requested": power_lite_requested,
        "power_lite_mode": power_lite_mode,
        "power_lite_forced_full": bool(power_lite_force_reason),
        "power_lite_force_reason": power_lite_force_reason,
        "deferred_labels": deferred_labels,
        "deferred_backlog_entries": deferred_backlog_entries,
        "deferred_backlog_count": _deferred_backlog_summary(deferred_backlog_entries)["count"],
        "deferred_backlog_day_keys": _deferred_backlog_summary(deferred_backlog_entries)["day_keys"],
        "deferred_backlog_day_count": _deferred_backlog_summary(deferred_backlog_entries)["day_count"],
        "deferred_consecutive_runs": deferred_consecutive_runs,
        "manifest_uploaded": should_upload_manifest,
        "manifest_error": manifest_error,
        "failed_count": failed_count,
        "results": results,
        "elapsed_seconds": round(time.perf_counter() - started, 3),
    }
    _write_json(STATUS_PATH, status)
    _log(
        "[private-upload] uploaded=%d missing=%d too_large=%d failed=%d backlog=%d days=%d repo=%s/%s"
        % (
            len([item for item in results if item.get("status") == "uploaded"]),
            len([item for item in results if item.get("status") == "missing_local"]),
            len([item for item in results if item.get("status") == "too_large"]),
            failed_count,
            status["deferred_backlog_count"],
            status["deferred_backlog_day_count"],
            config["owner"],
            config["repo"],
        )
    )
    if invocation_context.get("invoked_by") != "update_from_github":
        uploaded_count = len([item for item in results if item.get("status") == "uploaded"])
        deferred_count = len([item for item in results if item.get("status") == "deferred_power_save"])
        if failed_count == 0:
            _send_local_notification(
                "Upload done",
                "Sent %d, deferred %d." % (
                    uploaded_count,
                    deferred_count,
                ),
            )
        else:
            _send_local_notification(
                "Upload issue",
                "Sent %d, failed %d, deferred %d." % (
                    uploaded_count,
                    failed_count,
                    deferred_count,
                ),
            )
    _log("[private-upload] session end | %.3fs" % (time.perf_counter() - started))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        status = {
            "ok": False,
            "timestamp": _timestamp(),
            "script_build": SCRIPT_BUILD,
            "error": "%s" % exc,
        }
        try:
            _write_json(STATUS_PATH, status)
        except Exception:
            pass
        _log("[private-upload] failed: %s" % exc)
        raise SystemExit(1)
    raise SystemExit(0)
