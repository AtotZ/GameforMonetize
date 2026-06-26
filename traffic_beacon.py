# version: 2026-06-26-traffic-beacon-notify-v12
import datetime
import glob
import json
import math
import os
import re
import sys
import time

try:
    import location
except Exception:
    location = None

try:
    from objc_util import ObjCClass
except Exception:
    ObjCClass = None


ROOT_DIR = os.path.expanduser("~/Documents")
DATA_ROOT_DIR = os.path.join(ROOT_DIR, "TestSubjextData")
TRAFFIC_DATA_DIR = os.path.join(DATA_ROOT_DIR, "traffic")
OFFERS_DATA_DIR = os.path.join(DATA_ROOT_DIR, "offers")
HISTORY_DATA_DIR = os.path.join(TRAFFIC_DATA_DIR, "history")
LATEST_JSON_PATH = os.path.join(TRAFFIC_DATA_DIR, "TrafficBeacon-latest.json")
DB_JSON_PATH = os.path.join(TRAFFIC_DATA_DIR, "TrafficBeacon-db.json")
ACTIVE_OFFER_JSON_PATH = os.path.join(OFFERS_DATA_DIR, "active_offer.json")
ROUTE_DB_JSON_PATH = os.path.join(TRAFFIC_DATA_DIR, "TrafficRoute-db.json")
MAX_HISTORY_ITEMS = 2000
ACTIVE_OFFER_MAX_AGE_SECONDS = 6 * 60 * 60
CONFIDENCE_MEDIUM_MIN_SAMPLES = 3
CONFIDENCE_HIGH_MIN_SAMPLES = 8
TRAFFIC_FINE_BUCKET_MINUTES = 15
CORRIDOR_CELL_SIZE_METERS = 200.0

UK_POSTCODE_RE = re.compile(
    r"\b([A-Z]{1,2}\d[A-Z\d]?)\s*([0-9][A-Z]{2})\b",
    re.IGNORECASE,
)
UK_OUTCODE_RE = re.compile(
    r"\b([A-Z]{1,2}\d{1,2}[A-Z]?)\b",
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
        return {"postcode": "", "outcode": "", "sector": "", "precision": "none", "source": ""}
    outcode = _normalize_postcode_token(match.group(1))
    inward = _normalize_postcode_token(match.group(2))
    postcode = ("%s %s" % (outcode, inward)).strip()
    sector = ("%s %s" % (outcode, inward[:1])).strip() if inward else outcode
    return {
        "postcode": postcode,
        "outcode": outcode,
        "sector": sector,
        "precision": "full",
        "source": "full_postcode",
    }


def _extract_outcode_only(text):
    value = ("%s" % (text or "")).upper()
    match = UK_OUTCODE_RE.search(value)
    if not match:
        return ""
    return _normalize_postcode_token(match.group(1))


def _daily_history_path(day_text=""):
    day = ("%s" % (day_text or "")).strip() or datetime.datetime.now().strftime("%Y-%m-%d")
    return os.path.join(HISTORY_DATA_DIR, "%s-TrafficBeacon-history.jsonl" % day)


def _history_paths():
    pattern = os.path.join(HISTORY_DATA_DIR, "*-TrafficBeacon-history.jsonl")
    return sorted([path for path in glob.glob(pattern) if os.path.isfile(path)])


def _load_history():
    history = []
    for path in _history_paths():
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as handle:
                for raw_line in handle:
                    raw_line = raw_line.strip()
                    if not raw_line:
                        continue
                    try:
                        history.append(json.loads(raw_line))
                    except Exception:
                        continue
        except Exception:
            continue
    if len(history) > MAX_HISTORY_ITEMS:
        history = history[-MAX_HISTORY_ITEMS:]
    return history


def _write_json(path, payload):
    directory = os.path.dirname(path)
    if directory and not os.path.exists(directory):
        os.makedirs(directory)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)


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
        identifier = "TrafficBeaconNotif-%d" % int(time.time() * 1000)
        request = UNNotificationRequest.requestWithIdentifier_content_trigger_(identifier, content, trigger)
        center.addNotificationRequest_withCompletionHandler_(request, None)
        return True
    except Exception:
        return False


def _compact_address(value, limit=72):
    text = re.sub(r"\s+", " ", "%s" % (value or "")).strip(" ,.;-")
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 3)].rstrip(" ,.;-") + "..."


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
    path = _daily_history_path((entry or {}).get("timestamp", "")[:10])
    directory = os.path.dirname(path)
    if directory and not os.path.exists(directory):
        os.makedirs(directory)
    with open(path, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return path


def _parse_outcode_family(outcode):
    match = re.match(r"^([A-Z]{1,2})(\d{1,2})([A-Z]?)$", ("%s" % (outcode or "")).upper())
    if not match:
        return "", None, ""
    return match.group(1), int(match.group(2)), match.group(3)


def _time_bucket_name_from_timestamp(timestamp):
    dt_obj = _parse_timestamp(timestamp)
    if not dt_obj:
        dt_obj = datetime.datetime.now()
    mins = dt_obj.hour * 60 + dt_obj.minute
    weekday = dt_obj.weekday() < 5
    if weekday:
        if mins < 420:
            return "early_morning"
        if mins < 630:
            return "am_peak"
        if mins < 960:
            return "midday"
        if mins < 1110:
            return "pm_shoulder"
        return "evening"
    if mins < 660:
        return "weekend_early"
    if mins < 1080:
        return "weekend_busy"
    return "weekend_evening"


def _fine_time_bucket_key(dt_obj):
    if not dt_obj:
        dt_obj = datetime.datetime.now()
    minute_floor = (dt_obj.minute // TRAFFIC_FINE_BUCKET_MINUTES) * TRAFFIC_FINE_BUCKET_MINUTES
    prefix = "weekday" if dt_obj.weekday() < 5 else "weekend"
    return "%s-%02d:%02d" % (prefix, dt_obj.hour, minute_floor)


def _confidence_label(samples):
    value = int(samples or 0)
    if value >= CONFIDENCE_HIGH_MIN_SAMPLES:
        return "high"
    if value >= CONFIDENCE_MEDIUM_MIN_SAMPLES:
        return "medium"
    return "low"


def _empty_counter(with_time_buckets=True):
    return {
        "traffic_count": 0,
        "no_traffic_count": 0,
        "net_score": 0,
        "samples": 0,
        "raw_beacon_hits": 0,
        "confidence": "low",
        "last_seen": "",
        "days_seen": {},
        "unique_day_hits": 0,
        "time_buckets": {} if with_time_buckets else None,
        "time_windows_15m": {} if with_time_buckets else None,
    }


def _corridor_lon_step_degrees(latitude):
    cos_lat = math.cos(math.radians(float(latitude or 0.0)))
    if abs(cos_lat) < 0.01:
        cos_lat = 0.01
    return CORRIDOR_CELL_SIZE_METERS / (111320.0 * cos_lat)


def _corridor_cell_key(latitude, longitude):
    lat = _safe_float(latitude, 0.0)
    lon = _safe_float(longitude, 0.0)
    if abs(lat) < 0.000001 and abs(lon) < 0.000001:
        return "", 0.0, 0.0
    lat_step = CORRIDOR_CELL_SIZE_METERS / 111320.0
    lon_step = _corridor_lon_step_degrees(lat)
    lat_center = round(round(lat / lat_step) * lat_step, 5)
    lon_center = round(round(lon / lon_step) * lon_step, 5)
    return "%0.5f,%0.5f" % (lat_center, lon_center), lat_center, lon_center


def _corridor_segment_key(from_cell, to_cell):
    from_key = ("%s" % (from_cell or "")).strip()
    to_key = ("%s" % (to_cell or "")).strip()
    if not from_key or not to_key or from_key == to_key:
        return ""
    return "%s>%s" % (from_key, to_key)


def _refresh_bucket_coverage_metrics(bucket):
    if not isinstance(bucket, dict):
        return
    bucket["raw_beacon_hits"] = int(bucket.get("samples") or 0)
    days_seen = bucket.get("days_seen")
    bucket["unique_day_hits"] = len(days_seen) if isinstance(days_seen, dict) else 0

    sector_hits = bucket.get("sector_hits")
    if isinstance(sector_hits, dict):
        bucket["unique_sector_hits"] = len(sector_hits)

    outcodes = bucket.get("outcodes")
    if isinstance(outcodes, dict):
        bucket["unique_outcode_hits"] = len(outcodes)

    districts = bucket.get("districts")
    if isinstance(districts, dict):
        bucket["unique_district_hits"] = len(districts)

    beacon_outcodes = bucket.get("beacon_outcodes")
    if isinstance(beacon_outcodes, dict):
        bucket["unique_beacon_outcodes"] = len(beacon_outcodes)

    beacon_sectors = bucket.get("beacon_sectors")
    if isinstance(beacon_sectors, dict):
        bucket["unique_beacon_sectors"] = len(beacon_sectors)

    corridor_cells = bucket.get("corridor_cells")
    if isinstance(corridor_cells, dict):
        bucket["corridor_unique_cells"] = len(corridor_cells)

    corridor_segments = bucket.get("corridor_segments")
    if isinstance(corridor_segments, dict):
        bucket["corridor_unique_segments"] = len(corridor_segments)


def _bump_counter(bucket, status, timestamp):
    date_key = ("%s" % (timestamp or ""))[:10]
    if status == "traffic":
        bucket["traffic_count"] = int(bucket.get("traffic_count") or 0) + 1
    else:
        bucket["no_traffic_count"] = int(bucket.get("no_traffic_count") or 0) + 1
    bucket["net_score"] = int(bucket.get("traffic_count") or 0) - int(bucket.get("no_traffic_count") or 0)
    bucket["samples"] = int(bucket.get("samples") or 0) + 1
    bucket["confidence"] = _confidence_label(bucket["samples"])
    bucket["last_seen"] = timestamp or bucket.get("last_seen") or ""
    if date_key:
        bucket.setdefault("days_seen", {})
        bucket["days_seen"][date_key] = int(bucket["days_seen"].get(date_key) or 0) + 1
    _refresh_bucket_coverage_metrics(bucket)
    if isinstance(bucket.get("time_buckets"), dict):
        coarse_bucket = _time_bucket_name_from_timestamp(timestamp)
        leaf = bucket["time_buckets"].setdefault(coarse_bucket, _empty_counter(with_time_buckets=False))
        if status == "traffic":
            leaf["traffic_count"] = int(leaf.get("traffic_count") or 0) + 1
        else:
            leaf["no_traffic_count"] = int(leaf.get("no_traffic_count") or 0) + 1
        leaf["net_score"] = int(leaf.get("traffic_count") or 0) - int(leaf.get("no_traffic_count") or 0)
        leaf["samples"] = int(leaf.get("samples") or 0) + 1
        leaf["confidence"] = _confidence_label(leaf["samples"])
        leaf["last_seen"] = timestamp or leaf.get("last_seen") or ""
        if date_key:
            leaf.setdefault("days_seen", {})
            leaf["days_seen"][date_key] = int(leaf["days_seen"].get(date_key) or 0) + 1
        _refresh_bucket_coverage_metrics(leaf)
    if isinstance(bucket.get("time_windows_15m"), dict):
        dt_obj = _parse_timestamp(timestamp)
        fine_bucket = _fine_time_bucket_key(dt_obj)
        leaf = bucket["time_windows_15m"].setdefault(fine_bucket, _empty_counter(with_time_buckets=False))
        if status == "traffic":
            leaf["traffic_count"] = int(leaf.get("traffic_count") or 0) + 1
        else:
            leaf["no_traffic_count"] = int(leaf.get("no_traffic_count") or 0) + 1
        leaf["net_score"] = int(leaf.get("traffic_count") or 0) - int(leaf.get("no_traffic_count") or 0)
        leaf["samples"] = int(leaf.get("samples") or 0) + 1
        leaf["confidence"] = _confidence_label(leaf["samples"])
        leaf["last_seen"] = timestamp or leaf.get("last_seen") or ""
        if date_key:
            leaf.setdefault("days_seen", {})
            leaf["days_seen"][date_key] = int(leaf["days_seen"].get(date_key) or 0) + 1
        _refresh_bucket_coverage_metrics(leaf)


def _build_beacon_db(history):
    db = {
        "updated_at": _timestamp(),
        "total_entries": len(history),
        "confidence_thresholds": {
            "medium_min_samples": CONFIDENCE_MEDIUM_MIN_SAMPLES,
            "high_min_samples": CONFIDENCE_HIGH_MIN_SAMPLES,
        },
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
            _refresh_bucket_coverage_metrics(outcode_bucket)

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
            _refresh_bucket_coverage_metrics(district_bucket)

    return db


def _refresh_beacon_db_coverage(db):
    if not isinstance(db, dict):
        return db
    for bucket in (db.get("outcodes") or {}).values():
        _refresh_bucket_coverage_metrics(bucket)
    for bucket in (db.get("sectors") or {}).values():
        _refresh_bucket_coverage_metrics(bucket)
    for family_bucket in (db.get("families") or {}).values():
        _refresh_bucket_coverage_metrics(family_bucket)
        for district_bucket in (family_bucket.get("districts") or {}).values():
            _refresh_bucket_coverage_metrics(district_bucket)
    return db


def _empty_beacon_db():
    return {
        "updated_at": _timestamp(),
        "total_entries": 0,
        "confidence_thresholds": {
            "medium_min_samples": CONFIDENCE_MEDIUM_MIN_SAMPLES,
            "high_min_samples": CONFIDENCE_HIGH_MIN_SAMPLES,
        },
        "outcodes": {},
        "sectors": {},
        "families": {},
    }


def _load_or_build_beacon_db():
    payload = _load_json_dict(DB_JSON_PATH)
    if payload.get("outcodes") is not None and payload.get("sectors") is not None and payload.get("families") is not None:
        payload["confidence_thresholds"] = {
            "medium_min_samples": CONFIDENCE_MEDIUM_MIN_SAMPLES,
            "high_min_samples": CONFIDENCE_HIGH_MIN_SAMPLES,
        }
        return _refresh_beacon_db_coverage(payload)
    history = _load_history()
    return _build_beacon_db(history) if history else _empty_beacon_db()


def _update_beacon_db_incremental(db, entry):
    if not isinstance(db, dict):
        db = _empty_beacon_db()
    db["updated_at"] = _timestamp()
    db["confidence_thresholds"] = {
        "medium_min_samples": CONFIDENCE_MEDIUM_MIN_SAMPLES,
        "high_min_samples": CONFIDENCE_HIGH_MIN_SAMPLES,
    }
    db.setdefault("outcodes", {})
    db.setdefault("sectors", {})
    db.setdefault("families", {})
    db["total_entries"] = int(db.get("total_entries") or 0) + 1

    status = ("%s" % (entry.get("status") or "")).strip().lower()
    if status not in ("traffic", "no_traffic"):
        return db
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
        _refresh_bucket_coverage_metrics(outcode_bucket)

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
        _refresh_bucket_coverage_metrics(district_bucket)
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
        "samples": 0,
        "raw_beacon_hits": 0,
        "confidence": "low",
        "last_seen": "",
        "last_offer_timestamp": active_offer.get("timestamp") or "",
        "days_seen": {},
        "unique_day_hits": 0,
        "beacon_outcodes": {},
        "beacon_sectors": {},
        "corridor_cells": {},
        "corridor_segments": {},
        "corridor_unique_cells": 0,
        "corridor_unique_segments": 0,
        "corridor_last_cell": "",
        "corridor_last_offer_timestamp": "",
        "corridor_last_beacon_timestamp": "",
        "time_buckets": {},
        "time_windows_15m": {},
    }


def _touch_route_corridor(bucket, active_offer, beacon_payload, status, beacon_outcode, beacon_sector):
    if not isinstance(bucket, dict):
        return
    cell_key, cell_lat, cell_lon = _corridor_cell_key(
        beacon_payload.get("lat"),
        beacon_payload.get("lon"),
    )
    if not cell_key:
        return

    timestamp = beacon_payload.get("timestamp") or ""
    offer_timestamp = active_offer.get("timestamp") or ""
    corridor_cells = bucket.setdefault("corridor_cells", {})
    corridor_segments = bucket.setdefault("corridor_segments", {})
    cell_entry = corridor_cells.setdefault(
        cell_key,
        {
            "cell": cell_key,
            "lat": cell_lat,
            "lon": cell_lon,
            "hits": 0,
            "traffic_count": 0,
            "no_traffic_count": 0,
            "first_seen": timestamp,
            "last_seen": "",
            "beacon_outcodes": {},
            "beacon_sectors": {},
        },
    )
    cell_entry["hits"] = int(cell_entry.get("hits") or 0) + 1
    if status == "traffic":
        cell_entry["traffic_count"] = int(cell_entry.get("traffic_count") or 0) + 1
    else:
        cell_entry["no_traffic_count"] = int(cell_entry.get("no_traffic_count") or 0) + 1
    cell_entry["last_seen"] = timestamp or cell_entry.get("last_seen") or ""
    if beacon_outcode:
        cell_entry["beacon_outcodes"][beacon_outcode] = int(cell_entry["beacon_outcodes"].get(beacon_outcode) or 0) + 1
    if beacon_sector:
        cell_entry["beacon_sectors"][beacon_sector] = int(cell_entry["beacon_sectors"].get(beacon_sector) or 0) + 1

    previous_offer_timestamp = "%s" % (bucket.get("corridor_last_offer_timestamp") or "")
    previous_cell = "%s" % (bucket.get("corridor_last_cell") or "")
    if offer_timestamp and previous_offer_timestamp == offer_timestamp and previous_cell and previous_cell != cell_key:
        segment_key = _corridor_segment_key(previous_cell, cell_key)
        if segment_key:
            segment_entry = corridor_segments.setdefault(
                segment_key,
                {
                    "segment": segment_key,
                    "from_cell": previous_cell,
                    "to_cell": cell_key,
                    "hits": 0,
                    "traffic_count": 0,
                    "no_traffic_count": 0,
                    "first_seen": timestamp,
                    "last_seen": "",
                },
            )
            segment_entry["hits"] = int(segment_entry.get("hits") or 0) + 1
            if status == "traffic":
                segment_entry["traffic_count"] = int(segment_entry.get("traffic_count") or 0) + 1
            else:
                segment_entry["no_traffic_count"] = int(segment_entry.get("no_traffic_count") or 0) + 1
            segment_entry["last_seen"] = timestamp or segment_entry.get("last_seen") or ""

    bucket["corridor_last_cell"] = cell_key
    bucket["corridor_last_offer_timestamp"] = offer_timestamp
    bucket["corridor_last_beacon_timestamp"] = timestamp
    _refresh_bucket_coverage_metrics(bucket)


def _update_route_db(active_offer, beacon_payload):
    if not active_offer:
        return {}
    route_db = _load_json_dict(ROUTE_DB_JSON_PATH)
    routes = route_db.setdefault("routes", {})
    route_db["updated_at"] = _timestamp()
    route_db["active_offer_max_age_seconds"] = ACTIVE_OFFER_MAX_AGE_SECONDS
    route_db["confidence_thresholds"] = {
        "medium_min_samples": CONFIDENCE_MEDIUM_MIN_SAMPLES,
        "high_min_samples": CONFIDENCE_HIGH_MIN_SAMPLES,
    }
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
    bucket["confidence"] = _confidence_label(bucket["samples"])
    bucket["last_seen"] = beacon_payload.get("timestamp") or bucket.get("last_seen") or ""
    bucket["last_offer_timestamp"] = active_offer.get("timestamp") or bucket.get("last_offer_timestamp") or ""
    date_key = ("%s" % (beacon_payload.get("timestamp") or ""))[:10]
    if date_key:
        bucket.setdefault("days_seen", {})
        bucket["days_seen"][date_key] = int(bucket["days_seen"].get(date_key) or 0) + 1
    dt_obj = _parse_timestamp(beacon_payload.get("timestamp") or "")
    coarse_bucket = _time_bucket_name_from_timestamp(beacon_payload.get("timestamp") or "")
    time_leaf = bucket["time_buckets"].setdefault(coarse_bucket, _empty_counter(with_time_buckets=False))
    if status == "traffic":
        time_leaf["traffic_count"] = int(time_leaf.get("traffic_count") or 0) + 1
    else:
        time_leaf["no_traffic_count"] = int(time_leaf.get("no_traffic_count") or 0) + 1
    time_leaf["net_score"] = int(time_leaf.get("traffic_count") or 0) - int(time_leaf.get("no_traffic_count") or 0)
    time_leaf["samples"] = int(time_leaf.get("samples") or 0) + 1
    time_leaf["confidence"] = _confidence_label(time_leaf["samples"])
    time_leaf["last_seen"] = beacon_payload.get("timestamp") or time_leaf.get("last_seen") or ""
    fine_bucket = _fine_time_bucket_key(dt_obj)
    time_leaf = bucket["time_windows_15m"].setdefault(fine_bucket, _empty_counter(with_time_buckets=False))
    if status == "traffic":
        time_leaf["traffic_count"] = int(time_leaf.get("traffic_count") or 0) + 1
    else:
        time_leaf["no_traffic_count"] = int(time_leaf.get("no_traffic_count") or 0) + 1
    time_leaf["net_score"] = int(time_leaf.get("traffic_count") or 0) - int(time_leaf.get("no_traffic_count") or 0)
    time_leaf["samples"] = int(time_leaf.get("samples") or 0) + 1
    time_leaf["confidence"] = _confidence_label(time_leaf["samples"])
    time_leaf["last_seen"] = beacon_payload.get("timestamp") or time_leaf.get("last_seen") or ""
    if beacon_outcode:
        bucket["beacon_outcodes"][beacon_outcode] = int(bucket["beacon_outcodes"].get(beacon_outcode) or 0) + 1
    if beacon_sector:
        bucket["beacon_sectors"][beacon_sector] = int(bucket["beacon_sectors"].get(beacon_sector) or 0) + 1
    _touch_route_corridor(bucket, active_offer, beacon_payload, status, beacon_outcode, beacon_sector)
    _refresh_bucket_coverage_metrics(bucket)
    route_db["total_routes"] = len(routes)
    _write_json(ROUTE_DB_JSON_PATH, route_db)
    return {
        "route_key": route_key,
        "samples": bucket["samples"],
        "net_score": bucket["net_score"],
        "raw_beacon_hits": bucket.get("raw_beacon_hits") or 0,
        "unique_day_hits": bucket.get("unique_day_hits") or 0,
        "unique_beacon_outcodes": bucket.get("unique_beacon_outcodes") or 0,
        "unique_beacon_sectors": bucket.get("unique_beacon_sectors") or 0,
        "corridor_unique_cells": bucket.get("corridor_unique_cells") or 0,
        "corridor_unique_segments": bucket.get("corridor_unique_segments") or 0,
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
    raw_zip = ("%s" % (placemark.get("ZIP") or "")).strip()
    postcode_bits = _extract_postcode_parts("%s %s" % (raw_zip, address_text))
    if not postcode_bits.get("outcode"):
        zip_outcode = _extract_outcode_only(raw_zip)
        if zip_outcode:
            postcode_bits = {
                "postcode": "",
                "outcode": zip_outcode,
                "sector": "",
                "precision": "outcode_only",
                "source": "zip_outcode",
            }
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
        "postcode_precision": postcode_bits.get("precision") or "none",
        "postcode_source": postcode_bits.get("source") or "",
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
    beacon_db = _update_beacon_db_incremental(_load_or_build_beacon_db(), payload)
    _write_json(DB_JSON_PATH, beacon_db)
    active_offer = _load_active_offer()
    route_stats = _update_route_db(active_offer, payload) if active_offer else {}
    elapsed = time.perf_counter() - started
    print(
        "[traffic_beacon] saved traffic | %s | %s | db=%s | route=%s | %.3fs"
        % (
            payload.get("postcode") or payload.get("outcode") or "no_postcode",
            payload.get("timestamp") or "",
            beacon_db.get("total_entries") or 0,
            route_stats.get("route_key") or "none",
            elapsed,
        )
    )
    _send_local_notification(
        "Beacon saved %s" % (payload.get("postcode") or payload.get("outcode") or "no_postcode"),
        _compact_address(payload.get("address") or payload.get("placemark", {}).get("name") or "Address unavailable"),
    )


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print("[traffic_beacon] failed: %s" % exc)
        _send_local_notification("Beacon failed", "%s" % exc)
        raise SystemExit(1)
    raise SystemExit(0)
