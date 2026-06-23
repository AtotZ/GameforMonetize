import datetime
# version: 2026-06-23-updater-selfupdate-v1
import json
import os
import time
import urllib.request


SCRIPT_BUILD = "2026-06-23-updater-v2"
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
STATUS_PATH = os.path.join(SCRIPT_DIR, "update_from_github_status.json")

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

    payload = {
        "ok": True,
        "timestamp": _timestamp(),
        "script_build": SCRIPT_BUILD,
        "script_dir": SCRIPT_DIR,
        "files": results,
        "elapsed_seconds": round(time.perf_counter() - started, 3),
    }
    _write_status(payload)

    print("[updater] Updated %d file(s) in %s" % (len(results), SCRIPT_DIR))
    for result in results:
        print(
            "[updater] %s -> %s (%d bytes)"
            % (result["remote_name"], result["local_name"], result["bytes"])
        )


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
