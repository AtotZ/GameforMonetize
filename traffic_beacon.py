# version: 2026-06-23-traffic-beacon-db-v1
import datetime
import json
import os
import re
import sys
import time

try:
    import location
except Exception:
    location = None


ROOT_DIR = os.path.expanduser("~/Documents")
LATEST_JSON_PATH = os.path.join(ROOT_DIR, "TrafficBeacon-latest.json")
HISTORY_JSON_PATH = os.path.join(ROOT_DIR, "TrafficBeacon-history.json")
DB_JSON_PATH = os.path.join(ROOT_DIR, "TrafficBeacon-db.json")
ACTIVE_OFFER_JSON_PATH = os.path.join(ROOT_DIR, "active_offer.json")
ROUTE_DB_JSON_PATH = os.path.join(ROOT_DIR, "TrafficRoute-db.json")
MAX_HISTORY_ITEMS = 2000
ACTIVE_OFFER_MAX_AGE_SECONDS = 6 * 60 * 60

UK_POSTCODE_RE = re.compile(
    r"\b([A-Z]{1,2}\d[A-Z\d]?)\s*([0-9][A-Z]{2})\b",
    re.IGNORECASE,
)


def _timestamp():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


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


def _load_json_dict(path):
    try:
        with open(path, "r", encoding="utf-8") as handle:
            payload = json.load(handle)
        if isinstance(payload, dict):
            return payload
    except Exception:
        pass
    return {}


def _append_history(entry):
    history = _load_history()
    history.append(entry)
    if len(history) > MAX_HISTORY_ITEMS:
        history = history[-MAX_HISTORY_ITEMS:]
    _write_json(HISTORY_JSON_PATH, history)
    return history


def _parse_outcode_family(outcode):
    match = re.match(r"^([A-Z]{1,2})(\d{1,2})([A-Z]?)$", ("%s" % (outcode or "")).upper())
    if not match:
        return "", None, ""
    return match.group(1), int(match.group(2)), match.group(3)


def _empty_counter():
    return {
        "traffic_count": 0,
        "no_traffic_count": 0,
        "net_score": 0,
        "last_seen": "",
    }


def _bump_counter(bucket, status, timestamp):
    if status == "traffic":
        bucket["traffic_count"] = int(bucket.get("traffic_count") or 0) + 1
    else:
        bucket["no_traffic_count"] = int(bucket.get("no_traffic_count") or 0) + 1
    bucket["net_score"] = int(bucket.get("traffic_count") or 0) - int(bucket.get("no_traffic_count") or 0)
    bucket["last_seen"] = timestamp or bucket.get("last_seen") or ""


def _build_beacon_db(history):
    db = {
        "updated_at": _timestamp(),
        "total_entries": len(history),
        "outcodes": {},
        "sectors": {},
        "families": {},
    }

    for entry in history:
        status = ("%s" % (entry.get("status") or "")).strip().lower()
        if status not in ("traffic", "no_traffic"):
            continue
        timestamp = entry.get("timestamp") or ""
        outcode = ("%s" % (entry.get("outcode") or "")).upper()
        sector = ("%s" % (entry.get("sector") or "")).upper()
        family_letters, district_number, district_suffix = _parse_outcode_family(outcode)

        if outcode:
            outcode_bucket = db["outcodes"].setdefault(
                outcode,
                {
                    "outcode": outcode,
                    "family_letters": family_letters,
                    "district_number": district_number,
                    "district_suffix": district_suffix,
                    "sector_hits": {},
                    **_empty_counter()
                },
            )
            _bump_counter(outcode_bucket, status, timestamp)
            if sector:
                outcode_bucket["sector_hits"][sector] = int(outcode_bucket["sector_hits"].get(sector) or 0) + 1

        if sector:
            sector_bucket = db["sectors"].setdefault(
                sector,
                {
                    "sector": sector,
                    "outcode": outcode,
                    **_empty_counter()
                },
            )
            _bump_counter(sector_bucket, status, timestamp)

        if family_letters and district_number is not None:
            family_bucket = db["families"].setdefault(
                family_letters,
                {
                    "family_letters": family_letters,
                    "districts": {},
                    **_empty_counter()
                },
            )
            _bump_counter(family_bucket, status, timestamp)
            district_key = str(district_number)
            district_bucket = family_bucket["districts"].setdefault(
                district_key,
                {
                    "district_number": district_number,
                    "outcodes": {},
                    **_empty_counter()
                },
            )
            _bump_counter(district_bucket, status, timestamp)
            if outcode:
                district_bucket["outcodes"][outcode] = int(district_bucket["outcodes"].get(outcode) or 0) + 1

    return db


def _parse_timestamp(value):
    try:
        return datetime.datetime.strptime("%s" % (value or ""), "%Y-%m-%d %H:%M:%S")
    except Exception:
        return None


def _load_active_offer():
    payload = _load_json_dict(ACTIVE_OFFER_JSON_PATH)
    if not payload:
        return {}
    offer_ts = _parse_timestamp(payload.get("timestamp"))
    if not offer_ts:
        return {}
    age_seconds = abs((datetime.datetime.now() - offer_ts).total_seconds())
    if age_seconds > ACTIVE_OFFER_MAX_AGE_SECONDS:
        return {}
    return payload


def _route_key(active_offer):
    pickup = ("%s" % (active_offer.get("pickup_outcode") or "UNK")).upper()
    dropoff = ("%s" % (active_offer.get("dropoff_outcode") or "UNK")).upper()
    return "%s->%s" % (pickup, dropoff)


def _route_bucket(active_offer):
    return {
        "pickup_outcode": ("%s" % (active_offer.get("pickup_outcode") or "")).upper(),
        "dropoff_outcode": ("%s" % (active_offer.get("dropoff_outcode") or "")).upper(),
        "pickup_sector": ("%s" % (active_offer.get("pickup_sector") or "")).upper(),
        "dropoff_sector": ("%s" % (active_offer.get("dropoff_sector") or "")).upper(),
        "pickup_postcode": ("%s" % (active_offer.get("pickup_postcode") or "")).upper(),
        "dropoff_postcode": ("%s" % (active_offer.get("dropoff_postcode") or "")).upper(),
        "traffic_count": 0,
        "no_traffic_count": 0,
        "net_score": 0,
        "last_seen": "",
        "last_offer_timestamp": active_offer.get("timestamp") or "",
        "samples": 0,
        "beacon_outcodes": {},
        "beacon_sectors": {},
    }


def _update_route_db(active_offer, beacon_payload):
    if not active_offer:
        return {}
    route_db = _load_json_dict(ROUTE_DB_JSON_PATH)
    routes = route_db.setdefault("routes", {})
    route_db["updated_at"] = _timestamp()
    route_db["active_offer_max_age_seconds"] = ACTIVE_OFFER_MAX_AGE_SECONDS
    route_key = _route_key(active_offer)
    bucket = routes.setdefault(route_key, _route_bucket(active_offer))

    status = ("%s" % (beacon_payload.get("status") or "")).strip().lower()
    beacon_outcode = ("%s" % (beacon_payload.get("outcode") or "")).upper()
    beacon_sector = ("%s" % (beacon_payload.get("sector") or "")).upper()
    if status == "traffic":
        bucket["traffic_count"] = int(bucket.get("traffic_count") or 0) + 1
    else:
        bucket["no_traffic_count"] = int(bucket.get("no_traffic_count") or 0) + 1
    bucket["net_score"] = int(bucket.get("traffic_count") or 0) - int(bucket.get("no_traffic_count") or 0)
    bucket["samples"] = int(bucket.get("samples") or 0) + 1
    bucket["last_seen"] = beacon_payload.get("timestamp") or bucket.get("last_seen") or ""
    bucket["last_offer_timestamp"] = active_offer.get("timestamp") or bucket.get("last_offer_timestamp") or ""
    if beacon_outcode:
        bucket["beacon_outcodes"][beacon_outcode] = int(bucket["beacon_outcodes"].get(beacon_outcode) or 0) + 1
    if beacon_sector:
        bucket["beacon_sectors"][beacon_sector] = int(bucket["beacon_sectors"].get(beacon_sector) or 0) + 1
    route_db["total_routes"] = len(routes)
    _write_json(ROUTE_DB_JSON_PATH, route_db)
    return {
        "route_key": route_key,
        "samples": bucket["samples"],
        "net_score": bucket["net_score"],
    }


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
    history = _append_history(payload)
    beacon_db = _build_beacon_db(history)
    _write_json(DB_JSON_PATH, beacon_db)
    active_offer = _load_active_offer()
    route_stats = _update_route_db(active_offer, payload) if active_offer else {}
    elapsed = time.perf_counter() - started
    print(
        "[traffic_beacon] saved traffic | %s | %s | db=%s | route=%s | %.3fs"
        % (
            payload.get("postcode") or "no_postcode",
            payload.get("timestamp") or "",
            beacon_db.get("total_entries") or 0,
            route_stats.get("route_key") or "none",
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
