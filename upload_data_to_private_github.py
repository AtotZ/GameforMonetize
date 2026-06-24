import base64
import datetime
# version: 2026-06-24-private-data-upload-chain-breadcrumb-v3
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request


SCRIPT_BUILD = "2026-06-24-private-upload-v3"
API_ROOT = "https://api.github.com"
REQUEST_TIMEOUT_SECONDS = 20
MAX_UPLOAD_BYTES = 2 * 1024 * 1024


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


def _read_first_line(path):
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as handle:
            return ("%s" % (handle.readline() or "")).strip()
    except Exception:
        return ""


def _normalize_rel_path(value):
    return ("%s" % (value or "")).replace("\\", "/").strip().strip("/")


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
        files = DEFAULT_FILE_SPECS
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


def _upload_one(config, item):
    local_rel_path = _normalize_rel_path(item.get("local_rel_path") or "")
    remote_rel_path = _normalize_rel_path(item.get("remote_rel_path") or "")
    if not local_rel_path or not remote_rel_path:
        raise RuntimeError("Every file entry must include local_rel_path and remote_rel_path.")
    local_path = os.path.join(ROOT_DIR, *local_rel_path.split("/"))
    if not os.path.exists(local_path):
        return {
            "label": item.get("label") or remote_rel_path,
            "local_rel_path": local_rel_path,
            "remote_rel_path": remote_rel_path,
            "status": "missing_local",
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
    remote_path = remote_rel_path
    if config["remote_root"]:
        remote_path = "%s/%s" % (config["remote_root"], remote_rel_path)
    sha = _get_remote_sha(config, remote_path)
    body = {
        "message": "%s | %s | %s" % (
            config["commit_message_prefix"],
            item.get("label") or remote_rel_path,
            _timestamp(),
        ),
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
    payload = _api_request(url, config["token"], method="PUT", body=body)
    commit = payload.get("commit") or {}
    content = payload.get("content") or {}
    return {
        "label": item.get("label") or remote_rel_path,
        "local_rel_path": local_rel_path,
        "remote_rel_path": remote_path,
        "status": "uploaded",
        "bytes": len(raw),
        "sha": ("%s" % (content.get("sha") or "")).strip(),
        "commit_sha": ("%s" % (commit.get("sha") or "")).strip(),
    }


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
    config = _load_config()
    invocation_context = _read_invocation_context()
    results = []
    for item in config["files"]:
        results.append(_upload_one(config, item))
    manifest = _build_manifest(results, invocation_context)
    _upload_manifest(config, manifest)
    status = {
        "ok": True,
        "timestamp": _timestamp(),
        "script_build": SCRIPT_BUILD,
        "invocation_context": invocation_context,
        "repo": "%s/%s" % (config["owner"], config["repo"]),
        "branch": config["branch"],
        "remote_root": config["remote_root"],
        "bootstrap": config.get("bootstrap"),
        "results": results,
        "elapsed_seconds": round(time.perf_counter() - started, 3),
    }
    _write_json(STATUS_PATH, status)
    print(
        "[private-upload] uploaded=%d missing=%d too_large=%d repo=%s/%s"
        % (
            len([item for item in results if item.get("status") == "uploaded"]),
            len([item for item in results if item.get("status") == "missing_local"]),
            len([item for item in results if item.get("status") == "too_large"]),
            config["owner"],
            config["repo"],
        )
    )


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
        print("[private-upload] failed: %s" % exc)
        raise SystemExit(1)
    raise SystemExit(0)
