import datetime
import hashlib
import json
import os
import re
import time
import webbrowser

import photos
from objc_util import CGRect, ObjCClass, ObjCInstance

try:
    from onisai_offer_parser import parse_ocr_text
except ModuleNotFoundError:
    POUND = "\u00a3"
    EURO = "\u20ac"
    STAR = "\u2605"

    CURRENCY_CLASS = "[" + re.escape(POUND + "$" + EURO) + "]"
    CURRENCY_AMOUNT_RE = re.compile(
        CURRENCY_CLASS + r"\s*([0-9]{1,5}(?:[.,][0-9]{1,2})?)"
    )
    HOLIDAY_TOTAL_RE = re.compile(
        CURRENCY_CLASS
        + r"\s*([0-9]+(?:[.,][0-9]{1,2})?)\s*\+\s*est\.?\s*holiday\s+pay\s+of\s*"
        + CURRENCY_CLASS
        + r"\s*([0-9]+(?:[.,][0-9]{1,2})?)",
        re.IGNORECASE,
    )
    GENERIC_DURATION_RE = re.compile(
        r"(?:(\d+)\s*hr\s*)?(\d+(?:[.,]\d+)?)\s*mins?\b",
        re.IGNORECASE,
    )
    GENERIC_DISTANCE_RE = re.compile(
        r"(\d+(?:[.,]\d+)?)\s*(?:mi|miles?|ml)\b",
        re.IGNORECASE,
    )
    STAR_RATING_RE = re.compile(r"[*" + STAR + r"]\s*([0-9][0-9.]{0,4})")
    STAR_SUFFIX_RATING_RE = re.compile(r"([345][0-9]{0,2})\s*[*" + STAR + r"]")
    CONTEXTUAL_RATING_RE = re.compile(
        r"(?:[*" + STAR + r"%]\s*|rating[:\s]*)([0-9][0-9.]{0,4})",
        re.IGNORECASE,
    )
    DECIMAL_RATING_RE = re.compile(r"\b([45]\.\d{1,2})\b")
    COMPACT_RATING_RE = re.compile(r"\b([345][0-9]{2})\b")
    SPACED_COMPACT_RATING_RE = re.compile(r"\b([345])\s*([0-9])\s*([0-9])\b")
    TIME_TOKEN_PATTERN = r"(?:\d+[ \t]*hr(?:[ \t]*\d+(?:[.,]\d+)?[ \t]*mins?)?|\d+(?:[.,]\d+)?[ \t]*mins?)"
    DISTANCE_TOKEN_PATTERN = r"(?:mi|miles?|ml)"
    MIN_MI_RE = re.compile(
        r"(%s(?:[ \t]*\d+(?:[.,]\d+)?[ \t]*sec(?:onds?)?)?)[^\n\r]{0,30}?(?:\([ \t]*)?(\d+(?:[.,]\d+)?)\s*%s\b"
        % (TIME_TOKEN_PATTERN, DISTANCE_TOKEN_PATTERN),
        re.IGNORECASE,
    )
    MIN_MI_LINE_RE = re.compile(
        r"(%s(?:[ \t]*\d+(?:[.,]\d+)?[ \t]*sec(?:onds?)?)?)[^\n\r]{0,30}?(?:\([ \t]*)?(\d+(?:[.,]\d+)?)\s*%s\b"
        % (TIME_TOKEN_PATTERN, DISTANCE_TOKEN_PATTERN),
        re.IGNORECASE,
    )
    MIN_TIME_ONLY_RE = re.compile(
        r"(%s(?:[ \t]*\d+(?:[.,]\d+)?[ \t]*sec(?:onds?)?)?)" % TIME_TOKEN_PATTERN,
        re.IGNORECASE,
    )
    MI_ONLY_RE = re.compile(r"(\d+(?:[.,]\d+)?)\s*%s\b" % DISTANCE_TOKEN_PATTERN, re.IGNORECASE)
    UK_PC_RE = re.compile(r"\b([A-Z]{1,2}\d{1,2}[A-Z]?)\s*([0-9][A-Z]{2})\b", re.IGNORECASE)
    UK_PC_TERMINAL_RE = re.compile(
        r"\b([A-Z]{1,2}[0-9IZ]{1,2}[A-Z]?)\s*([0-9OIZ][A-Z]{2})\b",
        re.IGNORECASE,
    )
    COUNTRY_TOKENS = [" GB", " UK", ",GB", ",UK", ", Gb", ", Uk"]
    VALID_OUTWARD_RE = re.compile(r"^[A-Z]{1,2}\d[A-Z\d]?$")
    VALID_INWARD_RE = re.compile(r"^\d[A-Z]{2}$")
    SECTION_MARKERS_RE = re.compile(
        r"^(Pickup:|Trip:|Price|Star Rating|Vehicle Type|Uber Price|Distance:|Trip Time Estimate|Pickup Distance|Pickup Estimate|STATUS|FLAGGED|Traffic Level|EST\.? HOLIDAY PAY)",
        re.IGNORECASE,
    )
    SURGE_KEYWORD_RE = re.compile(r"\b(boost|surge|bonus|quest|promo(?:tion)?|peak)\b", re.IGNORECASE)
    RESERVED_TRIP_RE = re.compile(
        r"\b(reserve(?:d|ation)?|scheduled|pre[\s-]?book(?:ed|ing)?)\b",
        re.IGNORECASE,
    )
    OVERLAY_STOPWORDS = [
        "confirm",
        "towards your destination",
        "long trip",
        "exclusive",
        "fast charger",
        "holiday pay",
        "holiday entitlement",
        "route",
        "match",
        "multiple stop",
        "accept",
    ]
    VEHICLE_TYPE_PATTERNS = [
        ("Business Comfort Electric", re.compile(r"\bbusiness\s*comfort\s*electric\b", re.IGNORECASE)),
        ("Business Comfort", re.compile(r"\bbusiness\s*comfort\b", re.IGNORECASE)),
        ("Comfort Electric", re.compile(r"\bcomfort\s*electric\b", re.IGNORECASE)),
        ("Uber Comfort", re.compile(r"\buber\s*comfort\b", re.IGNORECASE)),
        ("UberX", re.compile(r"\buber\s*x\b", re.IGNORECASE)),
        ("UberXL", re.compile(r"\buber\s*xl\b|\buberxl\b", re.IGNORECASE)),
        ("Comfort", re.compile(r"\bcomfort\b", re.IGNORECASE)),
        ("Electric", re.compile(r"\belectric\b", re.IGNORECASE)),
        ("Uber Exec", re.compile(r"\buber\s*exec\b|\bexec\b", re.IGNORECASE)),
        ("Uber Green", re.compile(r"\buber\s*green\b|\bgreen\b", re.IGNORECASE)),
        ("Uber Pet", re.compile(r"\buber\s*pet\b|\bpet\b", re.IGNORECASE)),
        ("Uber Assist", re.compile(r"\buber\s*assist\b|\bassist\b", re.IGNORECASE)),
    ]

    def _fix_postcode_digit_confusions(token):
        return ("%s" % (token or "")).replace("I", "1").replace("O", "0").replace("Z", "2")

    def _fix_postcode_lead_digit_confusion(token):
        value = ("%s" % (token or "")).upper()
        if not value:
            return ""
        return value[0].replace("I", "1").replace("O", "0").replace("Z", "2")

    def _normalize_postcode_inward_token(token):
        value = re.sub(r"[^A-Z0-9]", "", ("%s" % (token or "")).upper())
        if len(value) != 3:
            return ""
        fixed = "%s%s" % (_fix_postcode_lead_digit_confusion(value[0]), value[1:])
        return fixed if VALID_INWARD_RE.match(fixed) else ""

    def _normalize_postcode_outward_token(token):
        raw = re.sub(r"[^A-Z0-9]", "", ("%s" % (token or "")).upper())
        if not raw:
            return ""
        fixed = _fix_postcode_digit_confusions(raw)
        if VALID_OUTWARD_RE.match(fixed):
            return fixed
        l_fixed = fixed.replace("L", "1")
        return l_fixed if VALID_OUTWARD_RE.match(l_fixed) else ""

    def _fix_postcode_ocr(text):
        if not text:
            return text
        transliterated = text.replace("\u0417", "3").replace("\u0415", "E").replace("\u041d", "H")

        def replace(match):
            outward = _normalize_postcode_outward_token(match.group(1))
            inward = _normalize_postcode_inward_token(match.group(2))
            if outward and inward:
                return "%s %s" % (outward, inward)
            return match.group(0)

        return re.sub(
            r"\b([A-Z]{1,2}[A-Z\dIOZ]{1,2})\s+([IOZ\d][A-Z]{2})\b",
            replace,
            transliterated,
            flags=re.IGNORECASE,
        )

    def _normalize_offer_text(input_text):
        text = "%s" % (input_text or "")
        text = text.replace("\u00c2\u00a3", POUND)
        text = text.replace("\u2018", "'").replace("\u2019", "'")
        text = text.replace("\u201c", '"').replace("\u201d", '"')
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        text = re.sub(
            r"(^|\n)(\s*)[fFeElL](?=\s*\d{1,3}(?:[.,]\d{1,2})?\s*(?:$|\n))",
            lambda match: "%s%s%s" % (match.group(1), match.group(2), POUND),
            text,
        )
        text = re.sub(
            r"(^|\n)(\s*[<\u2039]?\s*)[I|l](?=\s*mins?\b)",
            lambda match: "%s%s1" % (match.group(1), match.group(2)),
            text,
        )
        text = re.sub(
            r"\b([0-9I|l]{1,3})(?=\s*mins?\b)",
            lambda match: match.group(1).replace("I", "1").replace("|", "1").replace("l", "1"),
            text,
        )
        return text.strip()

    def _parse_money(raw):
        if not raw:
            return 0.0
        try:
            return float(raw.replace(",", "."))
        except Exception:
            return 0.0

    def _parse_hr_min_token(text):
        hr = re.search(r"(\d+)\s*hr", text, re.IGNORECASE)
        mi = re.search(r"(\d+(?:[.,]\d+)?)\s*mins?", text, re.IGNORECASE)
        sec = re.search(r"(\d+(?:[.,]\d+)?)\s*sec(?:onds?)?", text, re.IGNORECASE)
        hours = int(hr.group(1)) if hr else 0
        mins = float(mi.group(1).replace(",", ".")) if mi else 0.0
        secs = float(sec.group(1).replace(",", ".")) if sec else 0.0
        return round(hours * 60 + mins + secs / 60.0, 4)

    def _extract_holiday_pay_total(text):
        match = HOLIDAY_TOTAL_RE.search(text or "")
        if not match:
            return None
        base = _parse_money(match.group(1))
        holiday = _parse_money(match.group(2))
        if base <= 0 or holiday <= 0:
            return None
        return round(base + holiday, 2)

    def _extract_currency_candidates(text):
        candidates = []
        lines = ("%s" % (text or "")).split("\n")
        standalone_re = re.compile(r"^\s*" + CURRENCY_CLASS + r"\s*[0-9]{1,5}(?:[.,][0-9]{1,2})?\s*$")
        for line_index, line in enumerate(lines):
            line_is_standalone = bool(standalone_re.match(line))
            for match in CURRENCY_AMOUNT_RE.finditer(line):
                raw = match.group(1) or ""
                value = _parse_money(raw)
                if value > 0:
                    candidates.append(
                        {
                            "value": value,
                            "raw": raw,
                            "has_decimal": bool(re.search(r"[.,]", raw)),
                            "line": line.strip(),
                            "line_index": line_index,
                            "line_is_standalone_currency": line_is_standalone,
                        }
                    )
        return candidates

    def _select_price(text):
        holiday_total = _extract_holiday_pay_total(text)
        candidates = _extract_currency_candidates(text)
        if holiday_total and holiday_total > 0:
            for candidate in candidates:
                if candidate["has_decimal"] and abs(candidate["value"] - holiday_total) <= 0.06:
                    return {
                        "price": round(candidate["value"], 2),
                        "source": "holiday_total_matched",
                        "holiday_total": holiday_total,
                        "candidates": candidates,
                    }
            for candidate in candidates:
                if (
                    not candidate["has_decimal"]
                    and 100 <= candidate["value"] <= 9999
                    and abs(candidate["value"] / 100.0 - holiday_total) <= 0.06
                ):
                    return {
                        "price": round(candidate["value"] / 100.0, 2),
                        "source": "holiday_total_cent_fix",
                        "holiday_total": holiday_total,
                        "candidates": candidates,
                    }
            return {
                "price": holiday_total,
                "source": "holiday_total_sum",
                "holiday_total": holiday_total,
                "candidates": candidates,
            }
        decimal_candidates = [
            candidate
            for candidate in candidates
            if candidate["has_decimal"] and 2 <= candidate["value"] <= 300
        ]
        standalone_decimal = [
            candidate for candidate in decimal_candidates if candidate["line_is_standalone_currency"]
        ]
        if standalone_decimal:
            best = max(standalone_decimal, key=lambda candidate: candidate["value"])
            return {
                "price": round(best["value"], 2),
                "source": "standalone_decimal_currency",
                "holiday_total": None,
                "candidates": candidates,
            }
        standalone_whole = [
            candidate
            for candidate in candidates
            if candidate["line_is_standalone_currency"]
            and not candidate["has_decimal"]
            and 2 <= candidate["value"] <= 300
        ]
        if standalone_whole:
            best = max(standalone_whole, key=lambda candidate: candidate["value"])
            return {
                "price": round(best["value"], 2),
                "source": "standalone_whole_currency",
                "holiday_total": None,
                "candidates": candidates,
            }
        if decimal_candidates:
            best = max(decimal_candidates, key=lambda candidate: candidate["value"])
            return {
                "price": round(best["value"], 2),
                "source": "max_decimal_currency",
                "holiday_total": None,
                "candidates": candidates,
            }
        cent_candidates = []
        for candidate in candidates:
            if not candidate["has_decimal"] and 200 <= candidate["value"] <= 9999:
                scaled = candidate["value"] / 100.0
                if 2 <= scaled <= 300:
                    cent_candidates.append(scaled)
        if cent_candidates:
            return {
                "price": round(max(cent_candidates), 2),
                "source": "cent_scaled_currency",
                "holiday_total": None,
                "candidates": candidates,
            }
        return {
            "price": 0.0,
            "source": "none",
            "holiday_total": holiday_total,
            "candidates": candidates,
        }

    def _normalize_rating_token(token):
        cleaned = re.sub(r"[^\d.]", "", "%s" % (token or ""))
        if not cleaned:
            return 0.0
        if "." in cleaned:
            value = float(cleaned)
            return round(value, 2) if 3 <= value <= 5 else 0.0
        if not re.match(r"^\d+$", cleaned):
            return 0.0
        if len(cleaned) == 3 and cleaned[0] in "345":
            value = float("%s.%s" % (cleaned[0], cleaned[1:]))
            return round(value, 2) if 3 <= value <= 5 else 0.0
        if len(cleaned) == 2 and cleaned[0] in "345":
            value = float("%s.%s" % (cleaned[0], cleaned[1]))
            return round(value, 2) if 3 <= value <= 5 else 0.0
        if len(cleaned) == 1 and cleaned[0] in "45":
            return float(cleaned)
        return 0.0

    def _extract_rating(text):
        lines = ("%s" % (text or "")).split("\n")
        star_marker_re = re.compile(r"[*" + STAR + r"]")
        for line in lines:
            contextual_match = CONTEXTUAL_RATING_RE.search(line)
            if contextual_match:
                rating = _normalize_rating_token(contextual_match.group(1))
                if rating > 0:
                    return {"value": rating, "source": "contextual_match", "token": contextual_match.group(1), "line": line}
            star_match = STAR_RATING_RE.search(line)
            if star_match:
                rating = _normalize_rating_token(star_match.group(1))
                if rating > 0:
                    return {"value": rating, "source": "star_match", "token": star_match.group(1), "line": line}
            star_suffix_match = STAR_SUFFIX_RATING_RE.search(line)
            if star_suffix_match:
                rating = _normalize_rating_token(star_suffix_match.group(1))
                if rating > 0:
                    return {"value": rating, "source": "star_suffix_match", "token": star_suffix_match.group(1), "line": line}
            if POUND in line:
                continue
            decimal_match = DECIMAL_RATING_RE.search(line)
            if decimal_match:
                rating = _normalize_rating_token(decimal_match.group(1))
                if rating > 0:
                    return {"value": rating, "source": "decimal_fallback", "token": decimal_match.group(1), "line": line}
        for line in lines:
            if POUND in line:
                continue
            has_distance_terms = bool(
                re.search(r"\bmins?\b", line, re.IGNORECASE) or re.search(r"\bmi\b", line, re.IGNORECASE)
            )
            has_star_marker = bool(star_marker_re.search(line))
            if (not has_distance_terms) or has_star_marker:
                compact_match = COMPACT_RATING_RE.search(line)
                if compact_match:
                    rating = _normalize_rating_token(compact_match.group(1))
                    if rating > 0:
                        return {"value": rating, "source": "compact_numeric", "token": compact_match.group(1), "line": line}
                spaced_compact = SPACED_COMPACT_RATING_RE.search(line)
                if spaced_compact:
                    token = "%s%s%s" % (
                        spaced_compact.group(1),
                        spaced_compact.group(2),
                        spaced_compact.group(3),
                    )
                    rating = _normalize_rating_token(token)
                    if rating > 0:
                        return {"value": rating, "source": "compact_numeric", "token": token, "line": line}
        return {"value": 0.0, "source": "none", "token": "", "line": ""}

    def _extract_min_miles_pairs(text):
        pairs = []
        seen = set()
        for match in MIN_MI_RE.finditer(text or ""):
            raw_time = (match.group(1) or "").strip()
            raw_miles = (match.group(2) or "").strip()
            minutes = _parse_hr_min_token(raw_time)
            miles = _parse_money(raw_miles)
            signature = "%0.4f|%0.4f|%s" % (minutes, miles, raw_time.lower())
            if signature in seen:
                continue
            seen.add(signature)
            pairs.append({"raw_time": raw_time, "raw_miles": raw_miles, "min": minutes, "miles": miles})
        lines = [line.strip() for line in ("%s" % (text or "")).split("\n") if line.strip()]
        for index, line in enumerate(lines):
            time_match = MIN_TIME_ONLY_RE.search(line)
            if not time_match or MI_ONLY_RE.search(line):
                continue
            for next_index in range(index + 1, min(index + 3, len(lines))):
                miles_match = MI_ONLY_RE.search(lines[next_index])
                if not miles_match:
                    continue
                raw_time = (time_match.group(1) or "").strip()
                raw_miles = (miles_match.group(1) or "").strip()
                minutes = _parse_hr_min_token(raw_time)
                miles = _parse_money(raw_miles)
                signature = "%0.4f|%0.4f|%s" % (minutes, miles, raw_time.lower())
                if signature in seen:
                    continue
                seen.add(signature)
                pairs.append({"raw_time": raw_time, "raw_miles": raw_miles, "min": minutes, "miles": miles})
                break
        return pairs

    def _extract_duration_distance_fallbacks(text):
        durations = []
        distances = []
        for raw_line in ("%s" % (text or "")).split("\n"):
            line = raw_line.strip()
            if not line:
                continue
            lowered = line.lower()
            if "fast charger" in lowered:
                continue
            for match in GENERIC_DURATION_RE.finditer(line):
                hours = int(match.group(1)) if match.group(1) else 0
                minutes = _parse_money(match.group(2) or "0")
                total_minutes = round(hours * 60 + minutes, 4)
                if total_minutes > 0:
                    durations.append(total_minutes)
            for match in GENERIC_DISTANCE_RE.finditer(line):
                miles = _parse_money(match.group(1) or "0")
                if miles > 0:
                    distances.append(miles)
        return durations, distances

    def _detect_vehicle_type(text, lines):
        normalized = "%s" % (text or "")
        for label, pattern in VEHICLE_TYPE_PATTERNS:
            if pattern.search(normalized):
                return {"value": label, "source": "pattern_match", "token": label}
        for raw_line in lines:
            line = ("%s" % (raw_line or "")).strip()
            if not line:
                continue
            if not re.search(r"\b(uber|comfort|electric|business|exec|green|pet|assist)\b", line, re.IGNORECASE):
                continue
            for label, pattern in VEHICLE_TYPE_PATTERNS:
                if pattern.search(line):
                    return {"value": label, "source": "line_match", "token": line}
        return {"value": "", "source": "none", "token": ""}

    def _detect_surge_info(text, lines):
        amount_re = re.compile(CURRENCY_CLASS + r"\s*[0-9]+(?:[.,][0-9]{1,2})?")
        percent_re = re.compile(r"\b[0-9]+(?:[.,][0-9]+)?\s*%\b")
        for raw_line in lines:
            line = ("%s" % (raw_line or "")).strip()
            if not line:
                continue
            keyword_match = SURGE_KEYWORD_RE.search(line)
            if not keyword_match:
                continue
            amount_match = amount_re.search(line)
            percent_match = percent_re.search(line)
            suffix = ""
            if amount_match:
                suffix = re.sub(r"\s+", "", amount_match.group(0))
            elif percent_match:
                suffix = re.sub(r"\s+", "", percent_match.group(0))
            keyword = (keyword_match.group(1) or "").strip()
            normalized_keyword = keyword[:1].upper() + keyword[1:].lower() if keyword else "Surge"
            return {
                "value": "%s %s" % (normalized_keyword, suffix) if suffix else normalized_keyword,
                "source": "line_match",
                "token": line,
            }
        keyword_match = SURGE_KEYWORD_RE.search("%s" % (text or ""))
        if keyword_match:
            keyword = (keyword_match.group(1) or "").strip()
            normalized_keyword = keyword[:1].upper() + keyword[1:].lower() if keyword else "Surge"
            return {"value": normalized_keyword, "source": "text_match", "token": keyword}
        return {"value": "N/A", "source": "none", "token": ""}

    def _detect_reserved_trip(text):
        matched = bool(RESERVED_TRIP_RE.search("%s" % (text or "")))
        return {"value": matched, "source": "pattern_match" if matched else "none"}

    def _truncate_at_terminal(raw_line):
        if not raw_line:
            return ""
        line = _fix_postcode_ocr(raw_line.strip())
        postcode = UK_PC_RE.search(line) or UK_PC_TERMINAL_RE.search(line)
        if postcode:
            return line[: postcode.end()].strip().rstrip(" ,.;-")
        for token in COUNTRY_TOKENS:
            index = line.find(token)
            if index != -1:
                return line[: index + len(token)].strip().rstrip(" ,.;-")
        return line

    def _contains_overlay_stopword(value):
        lowered = ("%s" % (value or "")).lower()
        return any(word in lowered for word in OVERLAY_STOPWORDS)

    def _trim_at_first_overlay_stopword(value):
        line = "%s" % (value or "")
        lowered = line.lower()
        cut_at = len(line)
        for word in OVERLAY_STOPWORDS:
            index = lowered.find(word)
            if index != -1 and index < cut_at:
                cut_at = index
        return line[:cut_at].strip()

    def _clean_address_line(raw_line):
        line = _truncate_at_terminal(raw_line)
        line = _trim_at_first_overlay_stopword(line)
        line = re.sub(r"\b<\s*1\s*mi\s*from\s*fast\s*charger.*$", "", line, flags=re.IGNORECASE)
        line = re.sub(r"\b\d+\s*\*?\s*(?:a\s*)?mi\s*from\s*fast\s*charger.*$", "", line, flags=re.IGNORECASE)
        line = re.sub(r"\bfast\s*charger.*$", "", line, flags=re.IGNORECASE)
        line = re.sub(r"\blong\s*trip.*$", "", line, flags=re.IGNORECASE)
        line = re.sub(r"^[^A-Za-z0-9]+", "", line)
        line = re.sub(r"^[xXfF]\s+(?=[A-Z0-9])", "", line)
        line = re.sub(r"^[|lI]\s+", "", line)
        line = re.sub(r"\bPI\b", "Pl", line)
        line = re.sub(r"\bWIG\b", "W1G", line)
        return line.rstrip(" ,.;-")

    def _is_likely_address_line(line):
        if not line or len(line) < 4:
            return False
        if SECTION_MARKERS_RE.search(line):
            return False
        if MIN_MI_LINE_RE.search(line):
            return False
        if _contains_overlay_stopword(line):
            return False
        return len(re.findall(r"[A-Za-z]", line)) >= 3

    def _min_mi_line_indexes(lines):
        indexes = []
        seen = set()
        for index, line in enumerate(lines):
            if MIN_MI_LINE_RE.search(line):
                seen.add(index)
                indexes.append(index)
                continue
            time_match = MIN_TIME_ONLY_RE.search(line)
            if not time_match or MI_ONLY_RE.search(line):
                continue
            for next_index in range(index + 1, min(index + 3, len(lines))):
                if MI_ONLY_RE.search(lines[next_index]):
                    if index not in seen:
                        seen.add(index)
                        indexes.append(index)
                    break
        return indexes

    def _normalize_postcode_continuation_token(raw_line):
        token = re.sub(r"[^A-Z0-9]", "", ("%s" % (raw_line or "")).upper())
        if len(token) < 2 or len(token) > 4:
            return ""
        return token if re.match(r"^[A-Z0-9]+$", token) else ""

    def _stitch_partial_uk_postcode(base_address, continuation_raw):
        base = ("%s" % (base_address or "")).strip()
        if not base or UK_PC_RE.search(base):
            return ""
        token = _normalize_postcode_continuation_token(continuation_raw)
        if not token:
            return ""
        suffix_match = re.match(
            r"^(.*?)([A-Z]{1,2}[A-Z0-9IOZ]{1,3})(?:\s*([O0IZ]))?\s*$",
            base,
            re.IGNORECASE,
        )
        if not suffix_match:
            return ""
        prefix = suffix_match.group(1) or ""
        outward = _normalize_postcode_outward_token(suffix_match.group(2) or "")
        trailing_char = _fix_postcode_lead_digit_confusion(suffix_match.group(3) or "")
        inward = ""
        if not outward:
            return ""
        if trailing_char:
            if re.match(r"^[A-Z]{2}$", token):
                inward = "%s%s" % (trailing_char, token)
            elif re.match(r"^[0-9OIZ][A-Z]{2}$", token):
                inward = "%s%s" % (_fix_postcode_lead_digit_confusion(token[0]), token[1:])
        elif re.match(r"^[0-9OIZ][A-Z]{2}$", token):
            inward = "%s%s" % (_fix_postcode_lead_digit_confusion(token[0]), token[1:])
        if not inward:
            return ""
        postcode = ("%s %s" % (outward, inward)).upper()
        if not UK_PC_RE.search(postcode):
            return ""
        return re.sub(r"\s+", " ", ("%s%s" % (prefix, postcode)).strip())

    def _collect_address_after_index(lines, start_index, max_lines=5):
        parts = []
        for index in range(start_index + 1, len(lines)):
            source = lines[index].strip()
            if not source:
                break
            if not _is_likely_address_line(source):
                if parts:
                    stitched = _stitch_partial_uk_postcode(parts[-1], source)
                    if stitched:
                        parts[-1] = stitched
                    break
                continue
            cleaned = _fix_postcode_ocr(_clean_address_line(source))
            if not cleaned or len(cleaned) < 4:
                continue
            parts.append(cleaned)
            if len(parts) >= max_lines:
                break
            if UK_PC_RE.search(cleaned) or any(token.strip() in cleaned for token in COUNTRY_TOKENS):
                break
        return re.sub(r"\s+", " ", " ".join(parts)).strip()

    def _build_parse_error(parsed):
        missing = []
        if not (parsed.get("price", 0) > 0):
            missing.append("price")
        if not (parsed.get("trip_min", 0) > 0):
            missing.append("trip_min")
        if not (parsed.get("trip_miles", 0) > 0):
            missing.append("trip_miles")
        if not (parsed.get("pickup_min", 0) >= 0):
            missing.append("pickup_min")
        if not (parsed.get("pickup_miles", 0) >= 0):
            missing.append("pickup_miles")
        if parsed.get("trip_min", 0) > 600:
            missing.append("trip_min_range")
        if parsed.get("trip_miles", 0) > 1000:
            missing.append("trip_miles_range")
        return None if not missing else "parse_incomplete:%s" % ",".join(missing)

    def parse_ocr_text(ocr_text):
        text = _normalize_offer_text(ocr_text)
        lines = text.split("\n")
        price_info = _select_price(text)
        rating_info = _extract_rating(text)
        pairs = _extract_min_miles_pairs(text)
        durations, distances = _extract_duration_distance_fallbacks(text)
        vehicle_type_info = _detect_vehicle_type(text, lines)
        surge_info = _detect_surge_info(text, lines)
        reserved_info = _detect_reserved_trip(text)
        pickup_pair = pairs[0] if len(pairs) >= 1 else {"min": 0.0, "miles": 0.0}
        trip_pair = pairs[1] if len(pairs) >= 2 else {"min": 0.0, "miles": 0.0}
        if pickup_pair["min"] <= 0 and len(durations) >= 1:
            pickup_pair["min"] = durations[0]
        if pickup_pair["miles"] <= 0 and len(distances) >= 1:
            pickup_pair["miles"] = distances[0]
        if trip_pair["min"] <= 0 and len(durations) >= 2:
            trip_pair["min"] = durations[1]
        if trip_pair["miles"] <= 0 and len(distances) >= 2:
            trip_pair["miles"] = distances[1]
        line_indexes = _min_mi_line_indexes(lines)
        pickup_address = "Unknown"
        dropoff_address = "Unknown"
        if len(line_indexes) >= 1 and line_indexes[0] >= 0:
            pickup_address = _collect_address_after_index(lines, line_indexes[0], 3) or "Unknown"
        if len(line_indexes) >= 2 and line_indexes[1] >= 0:
            dropoff_address = _collect_address_after_index(lines, line_indexes[1], 3) or "Unknown"
        parsed = {
            "price": price_info["price"],
            "rating": rating_info["value"],
            "trip_min": trip_pair["min"],
            "trip_miles": trip_pair["miles"],
            "pickup_min": pickup_pair["min"],
            "pickup_miles": pickup_pair["miles"],
            "pickup_address": pickup_address,
            "dropoff_address": dropoff_address,
            "vehicle_type": vehicle_type_info["value"] or "",
            "surge_text": surge_info["value"] or "N/A",
            "is_reserved": reserved_info["value"] is True,
        }
        parse_error = _build_parse_error(parsed)
        return {
            "valid": not parse_error,
            "parseError": parse_error,
            "parsed": parsed,
            "debug": {
                "price_source": price_info["source"],
                "holiday_total": price_info["holiday_total"],
                "currency_candidates": price_info["candidates"],
                "min_mile_pairs_found": len(pairs),
                "duration_fallback_count": len(durations),
                "distance_fallback_count": len(distances),
                "min_mile_line_indexes": line_indexes,
                "rating_source": rating_info["source"],
                "rating_token": rating_info["token"],
                "rating_line": rating_info["line"],
                "vehicle_type_source": vehicle_type_info["source"],
                "vehicle_type_token": vehicle_type_info["token"],
                "surge_source": surge_info["source"],
                "surge_token": surge_info["token"],
                "reserved_source": reserved_info["source"],
            },
        }


t_global_start = time.perf_counter()
print("[T0] Entered Pythonista at %s" % time.strftime("%H:%M:%S"))


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
STATE_PATH = os.path.join(SCRIPT_DIR, ".uber_triplogger_onisai_local_state.json")
ROOT_DIR = os.path.expanduser("~/Documents")
TEXT_LOG_PATH = os.path.join(ROOT_DIR, "TripLog-OnisAI-Local.txt")
LEDGER_PATH = os.path.join(ROOT_DIR, "TripLog-OnisAI-Local.jsonl")
LATEST_JSON_PATH = os.path.join(ROOT_DIR, "TripLog-OnisAI-Local-latest.json")

GOOD_HOURLY_MIN = 28.0
BAD_HOURLY_MAX = 22.0
OVERHEAD_MINUTES = 2
DEFAULT_SHIFT_LIMIT_MINUTES = 10 * 60
DEFAULT_DAILY_TARGET_GBP = 300.0
LOW_RATING_DECLINE_THRESHOLD = 4.5
CCZ_BONUS_GBP = 2.0
RSP1_ALIAS_LABEL = "RSP1"
PRICE_PER_KWH = 17.83 / 44.57
CAR_MILES_PER_KWH = 4.0
COST_PER_MILE = PRICE_PER_KWH / CAR_MILES_PER_KWH
MAX_OCR_RETRIES = 3
RECENT_ASSET_SCAN_LIMIT = 8

CCZ_OUTCODE_RE = re.compile(r"^(?:EC[1-4][A-Z]?|WC[12][A-Z]?|W1[A-Z]?|SW1[A-Z]?|SE1[A-Z]?)$", re.IGNORECASE)
CCZ_FULL_POSTCODE_RE = re.compile(r"\b(?:EC[1-4][A-Z]?|WC[12][A-Z]?|W1[A-Z]?|SW1[A-Z]?|SE1[A-Z]?)\s*[0-9][A-Z]{2}\b", re.IGNORECASE)
CCZ_INWARD_O_FIX_RE = re.compile(r"\b((?:EC[1-4][A-Z]?|WC[12][A-Z]?|W1[A-Z]?|SW1[A-Z]?|SE1[A-Z]?))\s*O([A-Z]{2})\b", re.IGNORECASE)

VNImageRequestHandler = ObjCClass("VNImageRequestHandler")
VNRecognizeTextRequest = ObjCClass("VNRecognizeTextRequest")


def _load_state():
    try:
        with open(STATE_PATH, "r", encoding="utf-8") as handle:
            return json.load(handle)
    except Exception:
        return {}


def _save_state(payload):
    try:
        with open(STATE_PATH, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
    except Exception:
        pass


def _write_json(path, payload):
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)


def _append_jsonl(path, payload):
    with open(path, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def _send_push_notification(title, body):
    try:
        webbrowser.open("uberdriver://")
    except Exception as exc:
        print("Warning: could not open Uber via URL scheme: %s" % exc)

    UNUserNotificationCenter = ObjCClass("UNUserNotificationCenter")
    UNMutableNotificationContent = ObjCClass("UNMutableNotificationContent")
    UNNotificationRequest = ObjCClass("UNNotificationRequest")
    UNTimeIntervalNotificationTrigger = ObjCClass("UNTimeIntervalNotificationTrigger")
    UNNotificationSound = ObjCClass("UNNotificationSound")

    center = UNUserNotificationCenter.currentNotificationCenter()
    content = UNMutableNotificationContent.alloc().init()
    content.setTitle_(title)
    content.setBody_(body)
    content.setSound_(UNNotificationSound.defaultSound())

    trigger = UNTimeIntervalNotificationTrigger.triggerWithTimeInterval_repeats_(0.5, False)
    request = UNNotificationRequest.requestWithIdentifier_content_trigger_(
        "TripLoggerLocalNotif", content, trigger
    )
    center.addNotificationRequest_withCompletionHandler_(request, None)


def _recent_assets(limit=RECENT_ASSET_SCAN_LIMIT):
    assets = photos.get_assets(media_type="image")
    if not assets:
        return []
    try:
        return list(assets[-limit:])
    except Exception:
        tail = assets[-limit:]
        return list(tail) if tail else []


def _latest_asset():
    assets = _recent_assets(1)
    return assets[0] if assets else None


def _created_str(dt_obj):
    try:
        return dt_obj.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return ""


def _is_same_as_previous(asset, state):
    if not asset:
        return False
    prev_asset_id = state.get("last_asset_id")
    prev_created = state.get("last_created")
    asset_id = getattr(asset, "local_id", None)
    created = getattr(asset, "creation_date", None)
    created_s = _created_str(created) if created else ""
    same_id = asset_id and prev_asset_id and asset_id == prev_asset_id
    same_time = created_s and prev_created and created_s == prev_created
    return same_id or same_time


def _wait_for_fresh_latest_asset(state, poll_interval_s=0.08, timeout_s=3.0):
    time.sleep(0.15)
    start_wait = time.perf_counter()
    attempt = 0

    while True:
        attempt += 1
        if (time.perf_counter() - start_wait) > timeout_s:
            print("[guard] Photo guard timed out waiting for a new image asset.")
            return None

        asset = _latest_asset()
        if asset is None:
            time.sleep(poll_interval_s)
            continue

        created = getattr(asset, "creation_date", None)
        created_s = _created_str(created) if created else ""
        asset_id = getattr(asset, "local_id", None)

        if not _is_same_as_previous(asset, state):
            print(
                "[guard] Fresh asset detected on attempt %d | id=%s | created=%s"
                % (attempt, asset_id, created_s),
                flush=True,
            )
            return asset

        time.sleep(poll_interval_s)


def _looks_like_offer_text(ocr_text):
    text = "%s" % (ocr_text or "")
    lowered = text.lower()
    has_price = bool(re.search(r"(?:£|\$|\€)\s*\d", text))
    has_rating = bool(re.search(r"\b[345]\.\d{1,2}\b", text))
    has_minutes = len(re.findall(r"\b\d+(?:[.,]\d+)?\s*mins?\b", lowered)) >= 2
    has_miles = len(re.findall(r"\b\d+(?:[.,]\d+)?\s*(?:mi|miles?|ml)\b", lowered)) >= 2
    has_offer_keywords = any(
        token in lowered for token in ["holiday entitlement", "holiday pay", "exclusive", "confirm", "comfort", "uberx", "electric"]
    )
    return (has_price and has_minutes and has_miles) or (has_price and has_rating and has_offer_keywords)


def _offer_text_score(ocr_text):
    text = "%s" % (ocr_text or "")
    lowered = text.lower()
    score = 0
    if re.search(r"(?:£|\$|\€)\s*\d", text):
        score += 5
    score += min(4, len(re.findall(r"\b\d+(?:[.,]\d+)?\s*mins?\b", lowered)))
    score += min(4, len(re.findall(r"\b\d+(?:[.,]\d+)?\s*(?:mi|miles?|ml)\b", lowered)))
    if re.search(r"\b[345]\.\d{1,2}\b", text):
        score += 2
    for token in ["holiday entitlement", "holiday pay", "exclusive", "confirm", "comfort", "uberx", "electric"]:
        if token in lowered:
            score += 1
    if _looks_like_navigation_map(text):
        score -= 4
    return score


def _select_best_recent_offer_asset(state, limit=RECENT_ASSET_SCAN_LIMIT):
    candidates = _recent_assets(limit)
    candidates.reverse()
    best = None
    best_score = None
    best_bundle = None

    for asset in candidates:
        if _is_same_as_previous(asset, state):
            continue
        try:
            ui_image = asset.get_ui_image()
            objc_image = ObjCInstance(ui_image)
            cgimage = objc_image.CGImage()
            ocr_bundle = _run_offer_focused_ocr(cgimage)
            score = _offer_text_score(ocr_bundle["combined_text"])
        except Exception:
            continue

        if best is None or score > best_score:
            best = asset
            best_score = score
            best_bundle = ocr_bundle

        if _looks_like_offer_text(ocr_bundle["combined_text"]):
            return asset, ocr_bundle, score

    return best, best_bundle, best_score


def _run_ocr_from_cgimage(cgimage, region_of_interest=None):
    start_time = time.perf_counter()
    handler = VNImageRequestHandler.alloc().initWithCGImage_options_(cgimage, None)
    request = VNRecognizeTextRequest.alloc().init()
    request.setRecognitionLevel_(0)
    if region_of_interest is not None:
        try:
            request.setRegionOfInterest_(region_of_interest)
        except Exception:
            pass
    handler.performRequests_error_([request], None)
    ocr_time = time.perf_counter() - start_time

    lines = []
    for result in request.results():
        lines.append("* %s" % result.text())
    return "\n".join(lines), ocr_time


def _run_offer_focused_ocr(cgimage):
    full_text, full_time = _run_ocr_from_cgimage(cgimage)
    focused_region = CGRect((0.0, 0.0), (1.0, 0.62))
    lower_text, lower_time = _run_ocr_from_cgimage(cgimage, focused_region)
    combined_parts = []
    if lower_text.strip():
        combined_parts.append(lower_text.strip())
    if full_text.strip():
        combined_parts.append(full_text.strip())
    combined_text = "\n".join(combined_parts).strip()
    return {
        "full_text": full_text,
        "lower_text": lower_text,
        "combined_text": combined_text or full_text,
        "full_time": full_time,
        "lower_time": lower_time,
        "total_time": full_time + lower_time,
    }


def _looks_like_navigation_map(ocr_text):
    map_keywords = [
        "Dropping off",
        "Dropping",
        "LIMIT",
        "Speedometer",
        "Arriving",
        "towards your destination",
    ]
    return any(keyword in ocr_text for keyword in map_keywords)


def _contextual_pickup_status(pickup_miles, pickup_min, trip_miles, trip_min):
    if trip_miles >= 10 or trip_min >= 25:
        band = "long"
    elif trip_miles >= 5 or trip_min >= 10:
        band = "medium"
    else:
        band = "short"

    if band == "short":
        if pickup_miles <= 1.0 and pickup_min <= 5:
            return "CLOSE"
        if pickup_miles <= 1.5 or pickup_min <= 8:
            return "\u26a0\ufe0f SLIGHTLY FAR"
        return "\u274c TOO FAR"

    if band == "medium":
        if pickup_miles <= 1.5 and pickup_min <= 8:
            return "CLOSE"
        if pickup_miles <= 2.0 or pickup_min <= 10:
            return "\u26a0\ufe0f SLIGHTLY FAR"
        return "\u274c TOO FAR"

    if pickup_miles <= 2.5 and pickup_min <= 10:
        return "CLOSE"
    if pickup_miles <= 3.5 or pickup_min <= 14:
        return "\u26a0\ufe0f SLIGHTLY FAR"
    return "\u274c TOO FAR"


def _normalize_ccz_text(value):
    return ("%s" % (value or "")).upper().replace("I", "1").replace("O", "0")


def _address_looks_ccz(address_input):
    normalized = _normalize_ccz_text(address_input)
    normalized = CCZ_INWARD_O_FIX_RE.sub(r"\1 0\2", normalized)
    return bool(CCZ_FULL_POSTCODE_RE.search(normalized))


def _trip_ccz_detail(parsed):
    pickup_in_ccz = _address_looks_ccz(parsed.get("pickup_address") or "")
    dropoff_in_ccz = _address_looks_ccz(parsed.get("dropoff_address") or "")
    return {
        "touches": pickup_in_ccz or dropoff_in_ccz,
        "pickup_in_ccz": pickup_in_ccz,
        "dropoff_in_ccz": dropoff_in_ccz,
    }


def _derive_offer_metrics(parsed):
    ccz_info = _trip_ccz_detail(parsed)
    is_ccz = ccz_info["touches"]
    raw_price = float(parsed.get("price") or 0.0)
    price = raw_price + (CCZ_BONUS_GBP if is_ccz else 0.0)
    trip_min = float(parsed.get("trip_min") or 0.0)
    trip_miles = float(parsed.get("trip_miles") or 0.0)
    pickup_min = float(parsed.get("pickup_min") or 0.0)
    pickup_miles = float(parsed.get("pickup_miles") or 0.0)
    total_minutes = trip_min + pickup_min
    total_minutes_with_overhead = total_minutes + OVERHEAD_MINUTES
    total_miles = trip_miles + pickup_miles

    per_min_card = price / trip_min if trip_min else 0.0
    per_min_including_pickup = price / total_minutes if total_minutes else 0.0
    per_min_adj = price / total_minutes_with_overhead if total_minutes_with_overhead else 0.0
    per_mile_card = price / trip_miles if trip_miles else 0.0
    per_mile_including_pickup = price / total_miles if total_miles else 0.0
    hourly_nominal = per_min_card * 60 if per_min_card else 0.0
    hourly_adj = (price / max(trip_min + OVERHEAD_MINUTES, 1)) * 60.0 if trip_min else 0.0
    fuel_cost_pickup = pickup_miles * COST_PER_MILE
    fuel_cost_trip = trip_miles * COST_PER_MILE
    total_fuel_cost = fuel_cost_pickup + fuel_cost_trip

    if hourly_adj >= GOOD_HOURLY_MIN:
        pay_status = "GOOD"
    elif hourly_adj < BAD_HOURLY_MAX:
        pay_status = "BAD"
    else:
        pay_status = "LOW"

    return {
        "pickup_status": _contextual_pickup_status(pickup_miles, pickup_min, trip_miles, trip_min),
        "per_mile": round(per_mile_card, 2),
        "per_min": round(per_min_card, 2),
        "per_min_card": round(per_min_card, 2),
        "per_min_including_pickup": round(per_min_including_pickup, 2),
        "per_min_adj": round(per_min_adj, 2),
        "per_mile_card": round(per_mile_card, 2),
        "per_mile_adj": round(per_mile_including_pickup, 2),
        "per_mile_including_pickup": round(per_mile_including_pickup, 2),
        "hourly_nominal": round(hourly_nominal, 2),
        "hourly_adj": round(hourly_adj, 2),
        "pay_status": pay_status,
        "fuel_cost_pickup": round(fuel_cost_pickup, 2),
        "fuel_cost_trip": round(fuel_cost_trip, 2),
        "total_fuel_cost": round(total_fuel_cost, 2),
        "total_minutes": round(total_minutes, 2),
        "total_minutes_with_overhead": round(total_minutes_with_overhead, 2),
        "total_miles": round(total_miles, 2),
        "fare_for_metrics": round(price, 2),
        "ccz_bonus_applied": is_ccz,
        "ccz_pickup": ccz_info["pickup_in_ccz"],
        "ccz_dropoff": ccz_info["dropoff_in_ccz"],
        "pickup_discounted": False,
    }


def _read_ledger_records(path):
    records = []
    if not os.path.exists(path):
        return records
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as handle:
            for raw_line in handle:
                raw_line = raw_line.strip()
                if not raw_line:
                    continue
                try:
                    records.append(json.loads(raw_line))
                except Exception:
                    continue
    except Exception:
        return []
    return records


def _today_totals_from_ledger(path, today_date):
    records = _read_ledger_records(path)
    today_records = [record for record in records if (record.get("date") or "") == today_date]
    return {
        "trip_count": len(today_records),
        "total_price": round(sum(float(record.get("price") or 0.0) for record in today_records), 2),
        "drive_minutes": int(
            round(
                sum(
                    float(record.get("trip_min") or 0.0) + float(record.get("pickup_min") or 0.0)
                    for record in today_records
                )
            )
        ),
    }


def _today_summary_total_from_triplog(today_date):
    try:
        expected_name = "TripLog-%s-SUMMARY.txt" % today_date
        path = os.path.join(ROOT_DIR, expected_name)
        if not os.path.exists(path):
            return None
        with open(path, "r", encoding="utf-8", errors="ignore") as handle:
            text = handle.read()
        headers = list(re.finditer(r"^==== .+?====\s*$", text, re.MULTILINE))
        scope = text[headers[-1].end():] if headers else text
        prices = re.findall(r"💰\s*Uber Price:\s*£\s*([\d.]+)", scope)
        return round(sum(float(price) for price in prices), 2)
    except Exception:
        return None


def _today_summary_drive_minutes_from_triplog(today_date):
    try:
        expected_name = "TripLog-%s-SUMMARY.txt" % today_date
        path = os.path.join(ROOT_DIR, expected_name)
        if not os.path.exists(path):
            return None
        with open(path, "r", encoding="utf-8", errors="ignore") as handle:
            text = handle.read()
        headers = list(re.finditer(r"^==== .+?====\s*$", text, re.MULTILINE))
        scope = text[headers[-1].end():] if headers else text
        total_seconds = 0
        for match in re.finditer(r"^\s*Trip\s+\d+\s+Runtime:\s*(\d+):(\d+):(\d+)\b", scope, re.MULTILINE):
            hours, minutes, seconds = map(int, match.groups())
            total_seconds += hours * 3600 + minutes * 60 + seconds
        pickup_minutes = sum(
            int(match.group(1))
            for match in re.finditer(r"^⏱\s*Pickup Estimate:\s*(\d+)\s*min\b", scope, re.MULTILINE)
        )
        return int(round(total_seconds / 60.0)) + pickup_minutes
    except Exception:
        return None


def _fmt_hm(total_minutes):
    return "%dh %dm" % (total_minutes // 60, total_minutes % 60)


def _format_signed_pounds_per_minute(value):
    amount = abs(float(value or 0.0))
    sign = "+" if value >= 0 else "-"
    return "%s\u00a3%.2f/min" % (sign, amount)


def _compact_ocr_preview(text, limit=120):
    preview = re.sub(r"\s+", " ", "%s" % (text or "")).strip()
    if len(preview) <= limit:
        return preview
    return preview[: max(0, limit - 3)] + "..."


def _is_reliable_rating_source(debug):
    source = ("%s" % (debug.get("rating_source") or "")).strip().lower()
    if source in ("contextual_match", "star_match"):
        return True
    if source == "compact_numeric":
        line = "%s" % (debug.get("rating_line") or "")
        return bool(
            re.search(r"[<>*★]", line)
            or re.search(r"\b(?:rating|driver)\b", line, re.IGNORECASE)
            or re.match(r"^[A-Za-z]{1,4}\s*[345]\d{1,2}\s*[<>]?\s*$", line)
        )
    if source == "decimal_fallback":
        line = ("%s" % (debug.get("rating_line") or "")).strip()
        return bool(re.match(r"^\d\.\d{1,2}$", line))
    return False


def _low_rating_decision(parsed, debug):
    rating = float(parsed.get("rating") or 0.0)
    parse_error = ("%s" % (parsed.get("parse_error") or "")).lower()
    ocr_failed = parse_error.startswith("ocr_error") or parse_error == "ocr_no_text"
    rating_reliable = _is_reliable_rating_source(debug)
    is_low = rating > 0 and rating < LOW_RATING_DECLINE_THRESHOLD
    return {
        "rating": rating,
        "rating_reliable": rating_reliable,
        "should_decline_low_rating": is_low and rating_reliable and not ocr_failed,
    }


def _build_local_target_insight(today_total_gbp, drive_minutes, offer_per_min_adj_gbp):
    daily_target = float(DEFAULT_DAILY_TARGET_GBP)
    shift_limit_minutes = int(DEFAULT_SHIFT_LIMIT_MINUTES)
    if daily_target <= 0 or shift_limit_minutes <= 0:
        return None

    completed_fare = round(float(today_total_gbp or 0.0), 2)
    uber_burned_minutes = max(0, min(int(round(float(drive_minutes or 0.0))), shift_limit_minutes))
    baseline_target_per_min = round(daily_target / float(shift_limit_minutes), 2)
    remaining_target = round(daily_target - completed_fare, 2)
    uber_remaining_minutes = max(0, shift_limit_minutes - uber_burned_minutes)
    hourly_target_gbp = round(daily_target / max(1.0, shift_limit_minutes / 60.0), 2)
    required_per_min = 0.0
    if remaining_target > 0 and uber_remaining_minutes > 0:
        required_per_min = round(remaining_target / float(uber_remaining_minutes), 2)
    required_delta_per_min = round(required_per_min - baseline_target_per_min, 2)
    driver_pressure_factor = round(required_per_min / baseline_target_per_min, 2) if baseline_target_per_min > 0 else 1.0
    expected_by_now_gbp = round(baseline_target_per_min * uber_burned_minutes, 2)
    pace_balance_gbp = round(completed_fare - expected_by_now_gbp, 2)
    actual_per_min_gbp = round(completed_fare / float(uber_burned_minutes), 2) if uber_burned_minutes > 0 and completed_fare > 0 else 0.0
    if actual_per_min_gbp > 0:
        forecast_end_gbp = round(completed_fare + actual_per_min_gbp * uber_remaining_minutes, 2)
    else:
        forecast_end_gbp = round(daily_target - baseline_target_per_min * uber_burned_minutes, 2)
    forecast_gap_gbp = round(forecast_end_gbp - daily_target, 2)
    forecast_delta_vs_baseline_per_min = round(actual_per_min_gbp - baseline_target_per_min, 2)
    forecast_projection_per_min_gbp = round(max(0.0, forecast_end_gbp - completed_fare) / float(uber_remaining_minutes), 2) if uber_remaining_minutes > 0 else 0.0
    forecast_projection_per_hour_gbp = round(forecast_projection_per_min_gbp * 60.0, 2)
    if remaining_target <= 0:
        forecast_eta_minutes = 0
    elif actual_per_min_gbp > 0:
        forecast_eta_minutes = max(0, int(round(remaining_target / actual_per_min_gbp)))
    else:
        forecast_eta_minutes = None
    if remaining_target <= 0:
        forecast_target_feasible = True
    elif isinstance(forecast_eta_minutes, int):
        forecast_target_feasible = forecast_eta_minutes <= uber_remaining_minutes
    else:
        forecast_target_feasible = None
    compare_rate = required_per_min if required_per_min > 0 else baseline_target_per_min
    delta_per_min = round(float(offer_per_min_adj_gbp or 0.0) - compare_rate, 2)
    return {
        "enabled": True,
        "settings": {
            "shift_limit_minutes": shift_limit_minutes,
            "daily_target_gbp": round(daily_target, 2),
        },
        "shift_window": {
            "shift_limit_minutes": shift_limit_minutes,
            "shift_elapsed_minutes": uber_burned_minutes,
            "active_runtime_minutes": uber_burned_minutes,
            "driver_used_minutes": uber_burned_minutes,
            "uber_used_minutes": uber_burned_minutes,
            "uber_remaining_minutes": uber_remaining_minutes,
            "driver_remaining_minutes": uber_remaining_minutes,
            "idle_minutes": 0,
            "break_elapsed_minutes": 0,
        },
        "target_progress": {
            "enabled": True,
            "shift_limit_minutes": shift_limit_minutes,
            "daily_target_gbp": round(daily_target, 2),
            "hourly_target_gbp": hourly_target_gbp,
            "completed_fare_gbp": completed_fare,
            "remaining_target_gbp": remaining_target,
            "baseline_target_per_min_gbp": baseline_target_per_min,
            "required_per_min_driver_gbp": round(required_per_min, 2),
            "required_per_min_uber_gbp": round(required_per_min, 2),
            "required_delta_per_min_gbp": required_delta_per_min,
            "driver_pressure_factor": driver_pressure_factor,
            "expected_earnings_by_now_gbp": expected_by_now_gbp,
            "pace_balance_gbp": pace_balance_gbp,
            "actual_per_min_gbp": actual_per_min_gbp,
            "required_per_hour_driver_gbp": round(required_per_min * 60.0, 2),
            "required_per_hour_uber_gbp": round(required_per_min * 60.0, 2),
            "remaining_driver_minutes": uber_remaining_minutes,
            "remaining_uber_minutes": uber_remaining_minutes,
            "uber_burned_minutes": uber_burned_minutes,
            "forecast_end_gbp": forecast_end_gbp,
            "forecast_gap_gbp": forecast_gap_gbp,
            "forecast_projection_per_min_gbp": forecast_projection_per_min_gbp,
            "forecast_projection_per_hour_gbp": forecast_projection_per_hour_gbp,
            "forecast_delta_vs_baseline_per_min_gbp": forecast_delta_vs_baseline_per_min,
            "forecast_realized_per_min_gbp": forecast_projection_per_min_gbp,
            "forecast_realized_per_hour_gbp": forecast_projection_per_hour_gbp,
            "forecast_model": "uber_time_actual_pace_local",
            "forecast_uses_elapsed_minutes": uber_burned_minutes,
            "forecast_target_eta_minutes": forecast_eta_minutes,
            "forecast_target_eta_feasible": forecast_target_feasible,
        },
        "daily_target_gbp": round(daily_target, 2),
        "baseline_per_min_gbp": round(baseline_target_per_min, 2),
        "required_per_min_driver_gbp": round(required_per_min, 2),
        "offer_per_min_adj_gbp": round(float(offer_per_min_adj_gbp or 0.0), 2),
        "delta_per_min_gbp": round(delta_per_min, 2),
        "is_above_target": delta_per_min >= 0,
    }


def _build_log_block(now_str, trip_label, ocr_time, parse_result, metrics, ocr_text, target_insight, low_rating_decision):
    parsed = parse_result["parsed"]
    debug = parse_result["debug"]
    target_delta_line = "Target Delta: --"
    if target_insight and target_insight.get("enabled"):
        target_delta_line = "Target Delta: %s" % _format_signed_pounds_per_minute(
            target_insight.get("delta_per_min_gbp") or 0.0
        ).replace("/min", "/m")
    ccz_line = "CCZ Bonus Applied: %s" % ("YES (+£%.2f)" % CCZ_BONUS_GBP if metrics["ccz_bonus_applied"] else "NO")
    decline_line = "Low Rating Decline: %s | Reliable Source: %s" % (
        "YES" if low_rating_decision["should_decline_low_rating"] else "NO",
        "YES" if low_rating_decision["rating_reliable"] else "NO",
    )
    lines = [
        trip_label,
        "==============================",
        now_str,
        "",
        "[OCR Scan Time] %.3f seconds" % ocr_time,
        "",
        ocr_text.strip(),
        "",
        "Pickup: %.2f mi | %.2f min -> %s"
        % (parsed["pickup_miles"], parsed["pickup_min"], metrics["pickup_status"]),
        "Trip: %.2f mi | %.2f min" % (parsed["trip_miles"], parsed["trip_min"]),
        "Pickup Address: %s" % parsed["pickup_address"],
        "Dropoff Address: %s" % parsed["dropoff_address"],
        "Vehicle Type: %s" % (parsed["vehicle_type"] or "Unknown"),
        "Surge: %s" % (parsed["surge_text"] or "N/A"),
        "Reserved: %s" % ("YES" if parsed["is_reserved"] else "NO"),
        "Star Rating: %.2f" % parsed["rating"],
        "Uber Card Price: \u00a3%.2f" % parsed["price"],
        "Derived Fare For Metrics: \u00a3%.2f" % metrics["fare_for_metrics"],
        ccz_line,
        "Real Price: \u00a3%.2f/min | \u00a3%.2f/miles"
        % (metrics["per_min_adj"], metrics["per_mile_including_pickup"]),
        "%s: \u00a3%.2f/min | \u00a3%.2f/miles"
        % (RSP1_ALIAS_LABEL, metrics["per_min_card"], metrics["per_mile_card"]),
        "Effective \u00a3/hour (0m wait): \u00a3%.2f" % metrics["hourly_nominal"],
        "Effective \u00a3/hour (+%dm wait): \u00a3%.2f" % (OVERHEAD_MINUTES, metrics["hourly_adj"]),
        target_delta_line,
        decline_line,
        "Fuel for pickup: \u00a3%.2f" % metrics["fuel_cost_pickup"],
        "Fuel for trip: \u00a3%.2f" % metrics["fuel_cost_trip"],
        "Total fuel cost: \u00a3%.2f" % metrics["total_fuel_cost"],
        "Parser price source: %s" % debug["price_source"],
        "Parser rating source: %s" % debug["rating_source"],
        "Parser min/mi pairs found: %s" % debug["min_mile_pairs_found"],
        "STATUS: %s | %s" % (metrics["pay_status"], metrics["pickup_status"]),
        "==============================",
        "",
    ]
    return "\n".join(lines)


def main():
    state = _load_state()

    fetch_started = time.perf_counter()
    _wait_for_fresh_latest_asset(state, poll_interval_s=0.08, timeout_s=3.0)
    latest_asset, preselected_ocr_bundle, preselected_score = _select_best_recent_offer_asset(state)
    fetch_finished = time.perf_counter()

    if latest_asset is None:
        print("[guard] Aborting. Photo guard timed out (no new photo registered).")
        _send_push_notification(
            "TripLogger Alert",
            "Photo library did not update quickly enough. Try the scan again.",
        )
        raise SystemExit(0)

    ui_image = latest_asset.get_ui_image()
    objc_image = ObjCInstance(ui_image)
    cgimage = objc_image.CGImage()
    convert_finished = time.perf_counter()

    ocr_text = ""
    ocr_time = 0.0
    parse_result = None
    for _attempt in range(1, MAX_OCR_RETRIES + 1):
        ocr_bundle = preselected_ocr_bundle or _run_offer_focused_ocr(cgimage)
        preselected_ocr_bundle = None
        ocr_text = ocr_bundle["combined_text"]
        ocr_time = ocr_bundle["total_time"]
        parse_result = parse_ocr_text(ocr_text)
        if parse_result["valid"]:
            break
        focused_parse_result = parse_ocr_text(ocr_bundle["lower_text"])
        if focused_parse_result["valid"]:
            ocr_text = ocr_bundle["lower_text"]
            parse_result = focused_parse_result
            break
        time.sleep(0.05)

    if not parse_result or not parse_result["valid"]:
        if _looks_like_navigation_map(ocr_text):
            print("[guard] Active navigation map detected. Exiting silently.")
            raise SystemExit(0)

        parse_reason = parse_result["parseError"] if parse_result else "parse_failed"
        ocr_preview = _compact_ocr_preview(ocr_text, 110) or "no OCR text"
        latest_payload = {
            "ok": False,
            "reason": parse_reason,
            "ocr_text": ocr_text,
            "ocr_seconds": round(ocr_time, 4),
            "asset_offer_score": preselected_score,
        }
        _write_json(LATEST_JSON_PATH, latest_payload)
        _send_push_notification(
            "TripLogger Parse Alert",
            "%s | %s" % (parse_reason, ocr_preview),
        )
        raise SystemExit(0)

    print("[Asset fetch time] %.3f seconds" % (fetch_finished - fetch_started))
    print("[Image convert time] %.3f seconds" % (convert_finished - fetch_finished))
    print("[OCR Scan Time] %.3f seconds" % ocr_time)

    ocr_sha1 = hashlib.sha1(ocr_text.encode("utf-8", errors="ignore")).hexdigest()
    previous_ocr_sha1 = state.get("last_ocr_sha1")
    if previous_ocr_sha1 and ocr_sha1 == previous_ocr_sha1:
        print("[guard] Duplicate OCR text detected; skipping write/notify.")
        raise SystemExit(0)

    parsed = dict(parse_result["parsed"] or {})
    parsed["parse_error"] = parse_result.get("parseError")
    debug = parse_result.get("debug") or {}
    metrics = _derive_offer_metrics(parsed)
    low_rating_decision = _low_rating_decision(parsed, debug)

    now = datetime.datetime.now()
    today_date = now.strftime("%Y-%m-%d")
    now_str = now.strftime("%Y-%m-%d %H:%M:%S")

    totals_before_append = _today_totals_from_ledger(LEDGER_PATH, today_date)
    trip_number = totals_before_append["trip_count"] + 1
    trip_label = "TRIP %d" % trip_number
    heading = "==== %s ====\n" % now.strftime("%A, %d %B %Y")

    ledger_record = {
        "date": today_date,
        "timestamp": now_str,
        "trip_number": trip_number,
        "price": parsed["price"],
        "pickup_min": parsed["pickup_min"],
        "pickup_miles": parsed["pickup_miles"],
        "trip_min": parsed["trip_min"],
        "trip_miles": parsed["trip_miles"],
        "rating": parsed["rating"],
        "pickup_address": parsed["pickup_address"],
        "dropoff_address": parsed["dropoff_address"],
        "vehicle_type": parsed["vehicle_type"],
        "surge_text": parsed["surge_text"],
        "is_reserved": parsed["is_reserved"],
        "pickup_status": metrics["pickup_status"],
        "pay_status": metrics["pay_status"],
        "hourly_adj": metrics["hourly_adj"],
        "fare_for_metrics": metrics["fare_for_metrics"],
        "per_min_card": metrics["per_min_card"],
        "per_min_adj": metrics["per_min_adj"],
        "per_mile_card": metrics["per_mile_card"],
        "per_mile_including_pickup": metrics["per_mile_including_pickup"],
        "ccz_bonus_applied": metrics["ccz_bonus_applied"],
        "rating_reliable": low_rating_decision["rating_reliable"],
        "rating_action": "DECLINE_LOW_RATING" if low_rating_decision["should_decline_low_rating"] else "NONE",
        "ocr_sha1": ocr_sha1,
    }
    _append_jsonl(LEDGER_PATH, ledger_record)

    totals_after_append = _today_totals_from_ledger(LEDGER_PATH, today_date)
    summary_total = _today_summary_total_from_triplog(today_date)
    summary_drive_minutes = _today_summary_drive_minutes_from_triplog(today_date)
    target_total_gbp = summary_total if summary_total is not None else totals_after_append["total_price"]
    target_drive_minutes = summary_drive_minutes if summary_drive_minutes is not None else totals_after_append["drive_minutes"]
    left_minutes = max(0, DEFAULT_SHIFT_LIMIT_MINUTES - target_drive_minutes)
    target_insight = _build_local_target_insight(target_total_gbp, target_drive_minutes, metrics["per_min_adj"])

    block = _build_log_block(
        now_str,
        trip_label,
        ocr_time,
        parse_result,
        metrics,
        ocr_text,
        target_insight,
        low_rating_decision,
    )
    if totals_before_append["trip_count"] == 0:
        block = "\n%s%s" % (heading, block)

    with open(TEXT_LOG_PATH, "a", encoding="utf-8") as handle:
        handle.write(block)
        handle.flush()
        os.fsync(handle.fileno())

    latest_payload = {
        "ok": True,
        "timestamp": now_str,
        "selected_asset_id": getattr(latest_asset, "local_id", None),
        "selected_asset_created": _created_str(getattr(latest_asset, "creation_date", None)),
        "ocr_seconds": round(ocr_time, 4),
        "ocr_sha1": ocr_sha1,
        "ocr_text": ocr_text,
        "parse": parse_result,
        "metrics": metrics,
        "ledger_record": ledger_record,
        "today_totals": totals_after_append,
        "target_progress_local": target_insight,
        "low_rating_decision": low_rating_decision,
    }
    _write_json(LATEST_JSON_PATH, latest_payload)

    _save_state(
        {
            "last_asset_id": getattr(latest_asset, "local_id", None),
            "last_created": _created_str(getattr(latest_asset, "creation_date", None)),
            "last_ocr_sha1": ocr_sha1,
        }
    )

    if low_rating_decision["should_decline_low_rating"]:
        title_line = "\u2b50 %.2f | Decline below %.2f" % (
            low_rating_decision["rating"],
            LOW_RATING_DECLINE_THRESHOLD,
        )
        body_text = "\u2b50 %.2f is below %.2f" % (
            low_rating_decision["rating"],
            LOW_RATING_DECLINE_THRESHOLD,
        )
    else:
        target_delta_compact = "\u2014\u2014"
        if target_insight and target_insight.get("enabled"):
            target_delta_compact = _format_signed_pounds_per_minute(
                target_insight.get("delta_per_min_gbp") or 0.0
            ).replace("/min", "/m")
        title_line = "\u2b50 %.2f | \U0001f4b0 \u00a3%.2f | \U0001f3af %s" % (
            parsed["rating"] if parsed["rating"] else 0.0,
            parsed["price"],
            target_delta_compact,
        )
        body_line1 = "Real Price \u00a3%.2f/min | \u00a3%.2f/miles" % (
            metrics["per_min_adj"],
            metrics["per_mile_including_pickup"],
        )
        body_line2 = "%s \u00a3%.2f/min | \u00a3%.2f/miles" % (
            RSP1_ALIAS_LABEL,
            metrics["per_min_card"],
            metrics["per_mile_card"],
        )
        body_text = "%s\n%s" % (body_line1, body_line2)
    _send_push_notification(title_line, body_text)

    t_global_end = time.perf_counter()
    print("[T1] Leaving Pythonista at %s (Exec time: %.3fs)" % (
        time.strftime("%H:%M:%S"),
        t_global_end - t_global_start,
    ))


if __name__ == "__main__":
    main()
