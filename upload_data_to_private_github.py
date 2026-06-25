import base64
import datetime
import glob
import hashlib
# version: 2026-06-25-private-data-upload-ledger-v10
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request


SCRIPT_BUILD = "2026-06-25-private-upload-v10"
API_ROOT = "https://api.github.com"
REQUEST_TIMEOUT_SECONDS = 20
MAX_UPLOAD_BYTES = 2 * 1024 * 1024
MAX_CONSOLE_LOG_LINES = 400
TRIMMED_CONSOLE_LOG_LINES = 250
MAX_CONSOLE_LOG_BYTES = 48 * 1024


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
        "label": "route_db",
        "local_rel_path": "TestSubjextData/traffic/TrafficRoute-db.json",
        "remote_rel_path": "traffic/TrafficRoute-db.json",
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
    with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
        raw = response.read()
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
    cached = cache_payload["files"].get(remote_path) or {}
    if (
        cached.get("local_mtime_ns") == int(getattr(stat_result, "st_mtime_ns", 0))
        and int(cached.get("bytes") or 0) == int(stat_result.st_size)
        and ("%s" % (cached.get("content_sha1") or "")).strip()
    ):
        return {
            "label": item.get("label") or remote_rel_path,
            "local_rel_path": local_rel_path,
            "remote_rel_path": remote_path,
            "status": "skipped_unchanged",
            "bytes": int(stat_result.st_size),
            "content_sha1": ("%s" % (cached.get("content_sha1") or "")).strip(),
            "skip_reason": "local_stat_cache",
        }
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
    if (
        cached.get("content_sha1") == content_sha1
        and int(cached.get("bytes") or 0) == len(raw)
    ):
        return {
            "label": item.get("label") or remote_rel_path,
            "local_rel_path": local_rel_path,
            "remote_rel_path": remote_path,
            "status": "skipped_unchanged",
            "bytes": len(raw),
            "content_sha1": content_sha1,
        }
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
    skipped = [item for item in upload_results if item.get("status") == "skipped_unchanged"]
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
        "skipped_unchanged_count": len(skipped),
        "missing_count": len(missing),
        "too_large_count": len(too_large),
        "uploaded_files": uploaded,
        "skipped_unchanged_files": skipped,
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
    _log("[private-upload] session start | %s | %s" % (_timestamp(), SCRIPT_BUILD))
    config = _load_config()
    cache_payload = _load_cache(config)
    invocation_context = _read_invocation_context()
    results = []
    for item in config["files"]:
        results.append(_upload_one(config, item, cache_payload))
    manifest = _build_manifest(results, invocation_context)
    should_upload_manifest = any(item.get("status") != "skipped_unchanged" for item in results)
    if should_upload_manifest:
        _upload_manifest(config, manifest)
    _save_cache(cache_payload)
    status = {
        "ok": True,
        "timestamp": _timestamp(),
        "script_build": SCRIPT_BUILD,
        "invocation_context": invocation_context,
        "repo": "%s/%s" % (config["owner"], config["repo"]),
        "branch": config["branch"],
        "remote_root": config["remote_root"],
        "bootstrap": config.get("bootstrap"),
        "manifest_uploaded": should_upload_manifest,
        "results": results,
        "elapsed_seconds": round(time.perf_counter() - started, 3),
    }
    _write_json(STATUS_PATH, status)
    _log(
        "[private-upload] uploaded=%d skipped=%d missing=%d too_large=%d repo=%s/%s"
        % (
            len([item for item in results if item.get("status") == "uploaded"]),
            len([item for item in results if item.get("status") == "skipped_unchanged"]),
            len([item for item in results if item.get("status") == "missing_local"]),
            len([item for item in results if item.get("status") == "too_large"]),
            config["owner"],
            config["repo"],
        )
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
