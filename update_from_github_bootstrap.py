import datetime
# version: 2026-06-26-updater-bootstrap-force-v1
import hashlib
import os
import re
import time
import urllib.request


SCRIPT_BUILD = "2026-06-26-updater-bootstrap-v1"
REPO_RAW_ROOT = "https://raw.githubusercontent.com/AtotZ/GameforMonetize/main"
DOWNLOAD_TIMEOUT_SECONDS = 20


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


def _log(message):
    print("%s" % (message or ""))


def _download_text(url):
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "PythonistaUpdaterBootstrap/1.0",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
        },
    )
    with urllib.request.urlopen(request, timeout=DOWNLOAD_TIMEOUT_SECONDS) as response:
        raw = response.read()
    return raw.decode("utf-8")


def _write_text(path, text):
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)


def _extract_version_from_text(text):
    value = "%s" % (text or "")
    version_match = re.search(r"^\s*#\s*version:\s*(.+?)\s*$", value, re.MULTILINE)
    build_match = re.search(r'^\s*SCRIPT_BUILD\s*=\s*["\'](.+?)["\']\s*$', value, re.MULTILINE)
    return {
        "version_comment": (version_match.group(1).strip() if version_match else ""),
        "script_build": (build_match.group(1).strip() if build_match else ""),
    }


def _sha1_bytes(raw):
    return hashlib.sha1(raw).hexdigest()


def _update_one_file(item):
    cachebuster = int(time.time())
    url = "%s/%s?cb=%s" % (REPO_RAW_ROOT, item["remote_name"], cachebuster)
    source_text = _download_text(url)
    if "404: Not Found" in source_text and len(source_text.strip()) <= 20:
        raise RuntimeError("GitHub returned 404 for %s" % item["remote_name"])
    if "import " not in source_text and "def " not in source_text:
        raise RuntimeError("Downloaded content for %s does not look like Python code." % item["remote_name"])
    target_path = os.path.join(SCRIPT_DIR, item["local_name"])
    _write_text(target_path, source_text)
    version_info = _extract_version_from_text(source_text)
    return {
        "remote_name": item["remote_name"],
        "local_name": item["local_name"],
        "bytes": len(source_text.encode("utf-8")),
        "version_comment": version_info["version_comment"],
        "script_build": version_info["script_build"],
        "content_sha1": _sha1_bytes(source_text.encode("utf-8")),
    }


def main():
    started = time.perf_counter()
    _log("===== bootstrap updater start | %s | %s =====" % (_timestamp(), SCRIPT_BUILD))
    for item in FILE_MAP:
        result = _update_one_file(item)
        _log(
            "[bootstrap] %s -> %s | %d bytes | version=%s | build=%s"
            % (
                result["remote_name"],
                result["local_name"],
                result["bytes"],
                result["version_comment"] or "-",
                result["script_build"] or "-",
            )
        )
    _log("[bootstrap] session end | %.3fs" % (time.perf_counter() - started))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        _log("[bootstrap] failed: %s" % exc)
        raise SystemExit(1)
    raise SystemExit(0)
