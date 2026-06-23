import datetime
import json
import os
import re
import time

try:
    import location
except Exception:
    location = None


ROOT_DIR = os.path.expanduser("~/Documents")
LATEST_JSON_PATH = os.path.join(ROOT_DIR, "TrafficBeacon-latest.json")
HISTORY_JSON_PATH = os.path.join(ROOT_DIR, "TrafficBeacon-history.json")
MAX_HISTORY_ITEMS = 2000

UK_POSTCODE_RE = re.compile(
    r"\b([A-Z]{1,2}\d[A-Z\d]?)\s*([0-9][A-Z]{2})\b",
    re.IGNORECASE,
)


def _safe_float(value, default=0.0):
    try:
        return float(value)
    except Exception:
        return default


def _normalize_postcode_token(token):
    return re.sub(r"[^A-Z0-9]", "", ("%s" % (token or "")).upper())


def _extract_postcode_parts(text):
    value = ("%s" % (text or "")).upper()
    match = UK_POSTCODE_RE.search(value)
    if not match:
        return {"postcode": "", "outcode": "", "sector": ""}
    outcode = _normalize_postcode_token(match.group(1))
    inward = _normalize_postcode_token(match.group(2))
    postcode = ("%s %s" % (outcode, inward)).strip()
    sector = ("%s %s" % (outcode, inward[:1])).strip() if inward else outcode
    return {"postcode": postcode, "outcode": outcode, "sector": sector}


def _load_history():
    try:
        with open(HISTORY_JSON_PATH, "r", encoding="utf-8") as handle:
            payload = json.load(handle)
        if isinstance(payload, list):
            return payload
    except Exception:
        pass
    return []


def _write_json(path, payload):
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)


def _append_history(entry):
    history = _load_history()
    history.append(entry)
    if len(history) > MAX_HISTORY_ITEMS:
        history = history[-MAX_HISTORY_ITEMS:]
    _write_json(HISTORY_JSON_PATH, history)


def _get_location_snapshot():
    if location is None:
        raise RuntimeError("Pythonista location module is unavailable.")

    location.start_updates()
    deadline = time.time() + 3.0
    best = None
    try:
        while time.time() < deadline:
            current = location.get_location()
            if current:
                best = current
                accuracy = _safe_float(current.get("horizontal_accuracy"), 9999.0)
                if accuracy > 0 and accuracy <= 80:
                    break
            time.sleep(0.15)
    finally:
        location.stop_updates()

    if not best:
        raise RuntimeError("No GPS fix was available.")
    return best


def _reverse_geocode(latitude, longitude):
    if location is None:
        return {}
    try:
        placemarks = location.reverse_geocode({"latitude": latitude, "longitude": longitude}) or []
        if placemarks:
            return placemarks[0] or {}
    except Exception:
        pass
    return {}


def _coerce_address_text(placemark):
    ordered_keys = ["Name", "Thoroughfare", "SubThoroughfare", "City", "State", "ZIP", "Country"]
    parts = []
    for key in ordered_keys:
        value = ("%s" % (placemark.get(key) or "")).strip()
        if value and value not in parts:
            parts.append(value)
    return ", ".join(parts)


def _build_beacon_payload(status):
    snapshot = _get_location_snapshot()
    latitude = _safe_float(snapshot.get("latitude"))
    longitude = _safe_float(snapshot.get("longitude"))
    placemark = _reverse_geocode(latitude, longitude)
    address_text = _coerce_address_text(placemark)
    postcode_bits = _extract_postcode_parts("%s %s" % (placemark.get("ZIP") or "", address_text))
    now = datetime.datetime.now()
    return {
        "status": status,
        "timestamp": now.strftime("%Y-%m-%d %H:%M:%S"),
        "epoch": int(time.time()),
        "weekday": now.strftime("%A"),
        "weekpart": "weekend" if now.weekday() >= 5 else "weekday",
        "hour": now.hour,
        "minute": now.minute,
        "lat": round(latitude, 6),
        "lon": round(longitude, 6),
        "horizontal_accuracy": round(_safe_float(snapshot.get("horizontal_accuracy")), 2),
        "speed_mps": round(_safe_float(snapshot.get("speed")), 2),
        "course_deg": round(_safe_float(snapshot.get("course")), 2),
        "address": address_text,
        "postcode": postcode_bits["postcode"],
        "outcode": postcode_bits["outcode"],
        "sector": postcode_bits["sector"],
        "placemark": {
            "name": placemark.get("Name") or "",
            "street": placemark.get("Thoroughfare") or "",
            "street_number": placemark.get("SubThoroughfare") or "",
            "city": placemark.get("City") or "",
            "state": placemark.get("State") or "",
            "zip": placemark.get("ZIP") or "",
            "country": placemark.get("Country") or "",
        },
    }


def main():
    started = time.perf_counter()
    payload = _build_beacon_payload("traffic")
    _write_json(LATEST_JSON_PATH, payload)
    _append_history(payload)
    elapsed = time.perf_counter() - started
    print(
        "[traffic_beacon] saved traffic | %s | %s | %.3fs"
        % (
            payload.get("postcode") or "no_postcode",
            payload.get("timestamp") or "",
            elapsed,
        )
    )


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print("[traffic_beacon] failed: %s" % exc)
        raise SystemExit(1)
    raise SystemExit(0)
