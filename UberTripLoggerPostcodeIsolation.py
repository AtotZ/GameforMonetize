import datetime
# version: 2026-06-27-route-line-grid-shadow-v50
import hashlib
import json
import os
import re
import sys
import time
import webbrowser

import photos
from objc_util import CGRect, ObjCClass, ObjCInstance, on_main_thread
try:
    import clipboard
except Exception:
    clipboard = None

# Always use the embedded parser so Pythonista runs from one file only.
if True:
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
    UK_OUTCODE_RE = re.compile(r"\b([A-Z]{1,2}\d[A-Z\d]?)\b", re.IGNORECASE)
    UK_PC_TERMINAL_RE = re.compile(
        r"\b([A-Z]{1,2}[0-9IZ]{1,2}[A-Z]?)\s*([0-9OIZ][A-Z]{2})\b",
        re.IGNORECASE,
    )
    UK_PC_SECTOR_TERMINAL_RE = re.compile(
        r"\b([A-Z]{1,2}[0-9IZ]{1,2}[A-Z]?)\s*([0-9OIZ])\b",
        re.IGNORECASE,
    )
    COUNTRY_TOKENS = [" GB", " UK", ",GB", ",UK", ", Gb", ", Uk"]
    VALID_OUTWARD_RE = re.compile(r"^[A-Z]{1,2}\d[A-Z\d]?$")
    VALID_INWARD_RE = re.compile(r"^\d[A-Z]{2}$")
    POSTCODE_OUTWARD_PATTERNS = ("A9", "A9A", "A99", "AA9", "AA9A", "AA99")
    POSTCODE_OUTWARD_LOOSE_RE = re.compile(r"\b([A-Z]{1,2}[0-9IOZLSQB][A-Z0-9IOZLSQB]?)\b", re.IGNORECASE)
    POSTCODE_FULL_LOOSE_RE = re.compile(
        r"\b([A-Z]{1,2}[0-9IOZLSQB][A-Z0-9IOZLSQB]?)\s*([0-9IOZLSQBG][A-Z]{2,4})\b",
        re.IGNORECASE,
    )
    POSTCODE_SECTOR_LOOSE_RE = re.compile(
        r"\b([A-Z]{1,2}[0-9IOZLSQB][A-Z0-9IOZLSQB]?)\s*([0-9IOZLSQBG])\b",
        re.IGNORECASE,
    )
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
    NOTIFICATION_LINE_PATTERNS = [
        re.compile(r"triplogger\s+parse\s+alert", re.IGNORECASE),
        re.compile(r"parse_incomplete:", re.IGNORECASE),
        re.compile(r"ocr\s+ran,\s+but\s+required\s+trip\s+fields\s+were\s+missing", re.IGNORECASE),
        re.compile(r"\breal\s+price\b.*\/min", re.IGNORECASE),
        re.compile(r"\brsp1\b.*\/min", re.IGNORECASE),
        re.compile(r"[\u2b50\U0001f4b0\U0001f3af*].*\/m\b", re.IGNORECASE),
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

    POSTCODE_CONFUSABLE_TRANSLATIONS = str.maketrans({
        "\u0410": "A",  # Cyrillic A
        "\u0412": "B",  # Cyrillic Ve
        "\u0421": "C",  # Cyrillic Es
        "\u0415": "E",  # Cyrillic Ie
        "\u041d": "H",  # Cyrillic En
        "\u0406": "I",  # Cyrillic Byelorussian/Ukrainian I
        "\u041a": "K",  # Cyrillic Ka
        "\u041c": "M",  # Cyrillic Em
        "\u041e": "O",  # Cyrillic O
        "\u0420": "P",  # Cyrillic Er
        "\u0422": "T",  # Cyrillic Te
        "\u0425": "X",  # Cyrillic Ha
        "\u0423": "Y",  # Cyrillic U
        "\u0430": "A",
        "\u0432": "B",
        "\u0441": "C",
        "\u0435": "E",
        "\u043d": "H",
        "\u0456": "I",
        "\u043a": "K",
        "\u043c": "M",
        "\u043e": "O",
        "\u0440": "P",
        "\u0442": "T",
        "\u0445": "X",
        "\u0443": "Y",
    })

    def _transliterate_postcode_confusables(text):
        return ("%s" % (text or "")).translate(POSTCODE_CONFUSABLE_TRANSLATIONS)

    def _normalize_postcode_letter_char(ch):
        value = ("%s" % (ch or "")).upper()
        if not value:
            return ""
        return (
            value.replace("0", "O")
            .replace("1", "I")
            .replace("2", "Z")
            .replace("5", "S")
            .replace("6", "G")
            .replace("8", "B")
        )[:1]

    def _normalize_postcode_digit_char(ch):
        value = ("%s" % (ch or "")).upper()
        if not value:
            return ""
        return (
            value.replace("I", "1")
            .replace("L", "1")
            .replace("|", "1")
            .replace("O", "0")
            .replace("Q", "0")
            .replace("Z", "2")
            .replace("S", "5")
            .replace("G", "6")
            .replace("B", "8")
        )[:1]

    def _normalize_postcode_inward_token(token):
        value = re.sub(r"[^A-Z0-9]", "", _transliterate_postcode_confusables(token).upper())
        if len(value) < 3:
            return ""
        value = value[:3]
        fixed = "%s%s%s" % (
            _normalize_postcode_digit_char(value[0]),
            _normalize_postcode_letter_char(value[1]),
            _normalize_postcode_letter_char(value[2]),
        )
        return fixed if VALID_INWARD_RE.match(fixed) else ""

    def _apply_outward_pattern(raw, pattern):
        if len(raw) != len(pattern):
            return ""
        chars = []
        for index, marker in enumerate(pattern):
            source = raw[index]
            if marker == "A":
                chars.append(_normalize_postcode_letter_char(source))
            else:
                chars.append(_normalize_postcode_digit_char(source))
        candidate = "".join(chars)
        return candidate if VALID_OUTWARD_RE.match(candidate) else ""

    def _normalize_postcode_outward_token(token):
        raw = re.sub(r"[^A-Z0-9]", "", _transliterate_postcode_confusables(token).upper())
        if not raw:
            return ""
        if len(raw) == 3 and raw[0] == "U" and raw[1] in ("8", "B") and raw[2].isdigit():
            return "UB%s" % raw[2]
        if len(raw) == 4 and raw[-1:] in ("O", "I", "L", "Q", "Z", "S", "B", "G"):
            digit_tail = "%s%s" % (raw[:3], _normalize_postcode_digit_char(raw[3]))
            if VALID_OUTWARD_RE.match(digit_tail):
                return digit_tail
        if VALID_OUTWARD_RE.match(raw) and not any(ch in "IOZLSBQ" for ch in raw):
            return raw
        candidates = []
        for pattern in POSTCODE_OUTWARD_PATTERNS:
            candidate = _apply_outward_pattern(raw, pattern)
            if candidate and candidate not in candidates:
                candidates.append(candidate)
        if candidates:
            if raw[-1:] in ("O", "I", "Z", "Q", "L"):
                digit_tail = [candidate for candidate in candidates if candidate[-1:].isdigit()]
                if digit_tail:
                    return digit_tail[0]
            return candidates[0]
        fixed = _fix_postcode_digit_confusions(raw)
        if VALID_OUTWARD_RE.match(fixed):
            return fixed
        l_fixed = fixed.replace("L", "1")
        return l_fixed if VALID_OUTWARD_RE.match(l_fixed) else ""

    def _extract_full_postcode(text):
        line = _fix_postcode_ocr("%s" % (text or ""))
        candidates = []
        for pattern in (
            UK_PC_RE,
            UK_PC_TERMINAL_RE,
            re.compile(
                r"\b([A-Z]{1,2}[0-9IOZLSQB][A-Z0-9IOZLSQB]?)\s*([0-9IOZLSQBG][A-Z]{2,4})\b",
                re.IGNORECASE,
            ),
        ):
            for match in pattern.finditer(line):
                outward = _normalize_postcode_outward_token(match.group(1))
                inward = _normalize_postcode_inward_token(match.group(2))
                if outward and inward:
                    candidates.append((match.end(), "%s %s" % (outward, inward)))
        if not candidates:
            return ""
        candidates.sort(key=lambda item: (item[0], len(item[1])))
        return candidates[-1][1]

    def _extract_outcode(text):
        full = _extract_full_postcode(text)
        if full:
            return full.split()[0]
        partial_sector = _extract_partial_sector(text)
        if partial_sector:
            return partial_sector.split()[0]
        cleaned = _fix_postcode_ocr("%s" % (text or ""))
        candidates = []
        for match in UK_OUTCODE_RE.finditer(cleaned):
            normalized = _normalize_postcode_outward_token(match.group(1))
            if normalized:
                candidates.append(normalized)
        return candidates[-1] if candidates else ""

    def _extract_partial_sector(text):
        line = _fix_postcode_ocr("%s" % (text or ""))
        match = UK_PC_SECTOR_TERMINAL_RE.search(line)
        if not match:
            return ""
        outward = _normalize_postcode_outward_token(match.group(1))
        inward_digit = _normalize_postcode_digit_char(match.group(2))
        if outward and inward_digit:
            return "%s %s" % (outward, inward_digit)
        return ""

    def _extract_sector(text):
        full = _extract_full_postcode(text)
        if full:
            outward, inward = full.split()
            return "%s %s" % (outward, inward[0])
        partial_sector = _extract_partial_sector(text)
        if partial_sector:
            return partial_sector
        return ""

    def _derive_postcode_fields(text):
        full = _extract_full_postcode(text)
        if full:
            outward, inward = full.split()
            return {
                "postcode": full,
                "outcode": outward,
                "sector": "%s %s" % (outward, inward[0]),
                "quality": "full",
            }
        partial_sector = _extract_partial_sector(text)
        if partial_sector:
            return {
                "postcode": "",
                "outcode": partial_sector.split()[0],
                "sector": partial_sector,
                "quality": "sector",
            }
        outcode = _extract_outcode(text)
        if outcode:
            return {
                "postcode": "",
                "outcode": outcode,
                "sector": "",
                "quality": "outcode",
            }
        return {
            "postcode": "",
            "outcode": "",
            "sector": "",
            "quality": "none",
        }

    def _normalize_address_postcode_text(text):
        value = _transliterate_postcode_confusables(text)
        full = _extract_full_postcode(value)
        if full:
            repaired = POSTCODE_FULL_LOOSE_RE.sub(full, value, count=1)
            return re.sub(r"\s+", " ", repaired).strip()
        partial_sector = _extract_partial_sector(value)
        if partial_sector:
            repaired = POSTCODE_SECTOR_LOOSE_RE.sub(partial_sector, value, count=1)
            return re.sub(r"\s+", " ", repaired).strip()
        outcode = _extract_outcode(value)
        if outcode:
            repaired = POSTCODE_OUTWARD_LOOSE_RE.sub(outcode, value, count=1)
            return re.sub(r"\s+", " ", repaired).strip()
        return re.sub(r"\s+", " ", value).strip()

    def _fix_postcode_ocr(text):
        if not text:
            return text
        transliterated = _transliterate_postcode_confusables(text)
        transliterated = transliterated.replace("\u0417", "3")

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
            r"(^|\n)(\s*[•\-\+\*]?\s*)\?(?=\s*\d{1,3}(?:[.,]\d{1,2})\b)",
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
        lines = []
        for raw_line in text.split("\n"):
            line = raw_line.strip()
            if not line:
                lines.append("")
                continue
            if any(pattern.search(line) for pattern in NOTIFICATION_LINE_PATTERNS):
                continue
            lines.append(raw_line)
        return "\n".join(lines).strip()

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

    def _isolate_offer_block(text):
        lines = [line for line in ("%s" % (text or "")).split("\n")]
        if not lines:
            return ""
        start_index = 0
        for index, raw_line in enumerate(lines):
            line = ("%s" % (raw_line or "")).strip()
            if not line:
                continue
            if any(pattern.search(line) for _, pattern in VEHICLE_TYPE_PATTERNS):
                start_index = index
                break
        end_index = len(lines)
        for index in range(start_index, len(lines)):
            line = ("%s" % (lines[index] or "")).strip()
            if re.search(r"\bconfirm\b", line, re.IGNORECASE):
                end_index = index + 1
                break
        isolated = "\n".join(lines[start_index:end_index]).strip()
        return isolated or ("%s" % (text or "")).strip()

    def _truncate_at_terminal(raw_line):
        if not raw_line:
            return ""
        line = _fix_postcode_ocr(raw_line.strip())
        postcode = UK_PC_RE.search(line) or UK_PC_TERMINAL_RE.search(line)
        if postcode:
            return line[: postcode.end()].strip().rstrip(" ,.;-")
        postcode_sector = UK_PC_SECTOR_TERMINAL_RE.search(line)
        if postcode_sector:
            return line[: postcode_sector.end()].strip().rstrip(" ,.;-")
        for token in COUNTRY_TOKENS:
            index = line.find(token)
            if index != -1:
                return line[: index + len(token)].strip().rstrip(" ,.;-")
        return line

    def _append_outcode_if_missing(line, continuation):
        base = ("%s" % (line or "")).strip().rstrip(" ,.;-")
        if not base:
            return ""
        if _extract_full_postcode(base) or _extract_outcode(base):
            return base
        outcode = _extract_outcode(continuation)
        if not outcode:
            return base
        return ("%s, %s" % (base, outcode)).rstrip(" ,.;-")

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

    def _normalize_house_number_ocr(value):
        line = "%s" % (value or "")
        line = re.sub(r"(?<![A-Za-z0-9])([0-9]{1,4})\s*[lI|](?=\s+[A-Z][A-Za-z])", r"\g<1>1", line)
        return line

    def _remove_embedded_duplicate_postcode(value):
        line = re.sub(r"\s+", " ", "%s" % (value or "")).strip()
        full = _extract_full_postcode(line)
        if not full:
            return line
        occurrences = list(re.finditer(re.escape(full), line, re.IGNORECASE))
        if len(occurrences) <= 1:
            return line
        final_match = occurrences[-1]
        leading = line[: final_match.start()].rstrip(" ,.;-")
        leading = re.sub(r"(?<![A-Za-z0-9])%s(?=\s+[A-Za-z])" % re.escape(full), "", leading, count=1, flags=re.IGNORECASE)
        leading = re.sub(r"\s+", " ", leading).strip(" ,.;-")
        return ("%s, %s" % (leading, full)).strip(" ,.;-")

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
        line = _normalize_house_number_ocr(line)
        line = _normalize_address_postcode_text(line)
        line = _remove_embedded_duplicate_postcode(line)
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
            if not parts:
                inline_time_match = MIN_TIME_ONLY_RE.search(source)
                if inline_time_match and inline_time_match.start() > 0:
                    prefix = source[: inline_time_match.start()].strip(" ,.;-")
                    cleaned_prefix = _fix_postcode_ocr(_clean_address_line(prefix))
                    if cleaned_prefix and _is_likely_address_line(cleaned_prefix):
                        parts.append(cleaned_prefix)
                        break
            if not _is_likely_address_line(source):
                if parts:
                    stitched = _stitch_partial_uk_postcode(parts[-1], source)
                    if stitched:
                        parts[-1] = stitched
                    else:
                        parts[-1] = _append_outcode_if_missing(parts[-1], source)
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
        return _normalize_address_postcode_text(re.sub(r"\s+", " ", " ".join(parts)).strip())

    def _normalize_parsed_address_fields(parsed):
        normalized = dict(parsed or {})
        for field_name in ("pickup_address", "dropoff_address"):
            value = normalized.get(field_name) or ""
            value = _normalize_house_number_ocr(value)
            value = _normalize_address_postcode_text(value)
            normalized[field_name] = _remove_embedded_duplicate_postcode(value)
        pickup_postcode = _derive_postcode_fields(normalized.get("pickup_address") or "")
        dropoff_postcode = _derive_postcode_fields(normalized.get("dropoff_address") or "")
        normalized["pickup_postcode"] = pickup_postcode["postcode"]
        normalized["dropoff_postcode"] = dropoff_postcode["postcode"]
        normalized["pickup_outcode"] = pickup_postcode["outcode"]
        normalized["dropoff_outcode"] = dropoff_postcode["outcode"]
        normalized["pickup_sector"] = pickup_postcode["sector"]
        normalized["dropoff_sector"] = dropoff_postcode["sector"]
        normalized["pickup_postcode_quality"] = pickup_postcode["quality"]
        normalized["dropoff_postcode_quality"] = dropoff_postcode["quality"]
        return normalized

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
        text = _isolate_offer_block(_normalize_offer_text(ocr_text))
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
        pickup_postcode = _derive_postcode_fields(pickup_address)
        dropoff_postcode = _derive_postcode_fields(dropoff_address)
        parsed = {
            "price": price_info["price"],
            "rating": rating_info["value"],
            "trip_min": trip_pair["min"],
            "trip_miles": trip_pair["miles"],
            "pickup_min": pickup_pair["min"],
            "pickup_miles": pickup_pair["miles"],
            "pickup_address": pickup_address,
            "dropoff_address": dropoff_address,
            "pickup_postcode": pickup_postcode["postcode"],
            "dropoff_postcode": dropoff_postcode["postcode"],
            "pickup_outcode": pickup_postcode["outcode"],
            "dropoff_outcode": dropoff_postcode["outcode"],
            "pickup_sector": pickup_postcode["sector"],
            "dropoff_sector": dropoff_postcode["sector"],
            "pickup_postcode_quality": pickup_postcode["quality"],
            "dropoff_postcode_quality": dropoff_postcode["quality"],
            "vehicle_type": vehicle_type_info["value"] or "",
            "surge_text": surge_info["value"] or "N/A",
            "is_reserved": reserved_info["value"] is True,
        }
        parsed = _normalize_parsed_address_fields(parsed)
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

SCRIPT_BUILD = "2026-06-27-route-line-grid-shadow-v50"
SCRIPT_BUILD_TAG = SCRIPT_BUILD.rsplit("-", 1)[-1]

t_global_start = time.perf_counter()
RUNTIME_STDOUT_ENABLED = False


def _runtime_print(message):
    if RUNTIME_STDOUT_ENABLED:
        print(message)


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
STATE_PATH = os.path.join(SCRIPT_DIR, ".uber_triplogger_postcode_isolation_state.json")
ROOT_DIR = os.path.expanduser("~/Documents")
DATA_ROOT_DIR = os.path.join(ROOT_DIR, "TestSubjextData")
TRAFFIC_DATA_DIR = os.path.join(DATA_ROOT_DIR, "traffic")
TRAFFIC_HISTORY_DIR = os.path.join(TRAFFIC_DATA_DIR, "history")
OFFERS_DATA_DIR = os.path.join(DATA_ROOT_DIR, "offers")
OFFERS_HISTORY_DIR = os.path.join(OFFERS_DATA_DIR, "history")
LOGS_DATA_DIR = os.path.join(DATA_ROOT_DIR, "logs")
DEBUG_DATA_DIR = os.path.join(DATA_ROOT_DIR, "debug")
TRAFFIC_BEACON_DB_PATH = os.path.join(TRAFFIC_DATA_DIR, "TrafficBeacon-db.json")
TRAFFIC_ROUTE_DB_PATH = os.path.join(TRAFFIC_DATA_DIR, "TrafficRoute-db.json")
TRAFFIC_ROUTE_POINT_DB_PATH = os.path.join(TRAFFIC_DATA_DIR, "TrafficBeacon-route-points.json")
TRAFFIC_LINE_GRID_DB_PATH = os.path.join(TRAFFIC_DATA_DIR, "TrafficBeacon-line-grid.json")
ACTIVE_OFFER_JSON_PATH = os.path.join(OFFERS_DATA_DIR, "active_offer.json")
TEXT_LOG_PATH = os.path.join(LOGS_DATA_DIR, "TripLog-OnisAI-PostcodeIsolation.txt")
LEDGER_PATH = os.path.join(LOGS_DATA_DIR, "TripLog-OnisAI-PostcodeIsolation.jsonl")
LATEST_JSON_PATH = os.path.join(OFFERS_DATA_DIR, "TripLog-OnisAI-PostcodeIsolation-latest.json")
DEBUG_SHORTCUT_DUMP_PATH = os.path.join(DEBUG_DATA_DIR, "TripLog-OnisAI-PostcodeIsolation-shortcut-input.txt")
SHORTCUT_INPUT_PATH = os.path.join(ROOT_DIR, "shortcut_offer_text.txt")
SHORTCUT_INPUT_SCRIPT_DIR_PATH = os.path.join(SCRIPT_DIR, "shortcut_offer_text.txt")
SHORTCUT_INPUT_SCRIPT_DIR_NESTED_PATH = os.path.join(
    SCRIPT_DIR, os.path.basename(os.path.normpath(SCRIPT_DIR)), "shortcut_offer_text.txt"
)
SHORTCUT_INPUT_FALLBACK_PATH = os.path.expanduser("~/shortcut_offer_text.txt")
SHORTCUT_INPUT_WAIT_SECONDS = 4.0
SHORTCUT_INPUT_POLL_SECONDS = 0.10

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
FORCE_WRITE_FSYNC = False
USE_SUMMARY_TARGET_FILES = False

CCZ_OUTCODE_RE = re.compile(r"^(?:EC[1-4][A-Z]?|WC[12][A-Z]?|W1[A-Z]?|SW1[A-Z]?|SE1[A-Z]?)$", re.IGNORECASE)
CCZ_FULL_POSTCODE_RE = re.compile(r"\b(?:EC[1-4][A-Z]?|WC[12][A-Z]?|W1[A-Z]?|SW1[A-Z]?|SE1[A-Z]?)\s*[0-9][A-Z]{2}\b", re.IGNORECASE)
CCZ_INWARD_O_FIX_RE = re.compile(r"\b((?:EC[1-4][A-Z]?|WC[12][A-Z]?|W1[A-Z]?|SW1[A-Z]?|SE1[A-Z]?))\s*O([A-Z]{2})\b", re.IGNORECASE)

VNImageRequestHandler = ObjCClass("VNImageRequestHandler")
VNRecognizeTextRequest = ObjCClass("VNRecognizeTextRequest")

_ROUTE_DB_CACHE = {
    "mtime": None,
    "payload": None,
}

_TRAFFIC_BEACON_DB_CACHE = {
    "mtime": None,
    "payload": None,
}

_ROUTE_POINT_DB_CACHE = {
    "mtime": None,
    "payload": None,
}

_LINE_GRID_DB_CACHE = {
    "mtime": None,
    "payload": None,
}


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


def _normalize_totals_cache(payload):
    source = payload if isinstance(payload, dict) else {}
    return {
        "trip_count": int(source.get("trip_count") or 0),
        "total_price": round(float(source.get("total_price") or 0.0), 2),
        "drive_minutes": int(round(float(source.get("drive_minutes") or 0.0))),
    }


def _get_today_totals_cached(state, ledger_path, today_date):
    cached = state.get("today_totals_cache") or {}
    if ("%s" % (cached.get("date") or "")).strip() == today_date:
        return _normalize_totals_cache(cached)
    return _normalize_totals_cache(_today_totals_from_ledger(ledger_path, today_date))


def _ensure_parent_dir(path):
    directory = os.path.dirname(path)
    if directory and not os.path.exists(directory):
        os.makedirs(directory)


def _write_json(path, payload):
    _ensure_parent_dir(path)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)


def _load_json_dict(path):
    try:
        with open(path, "r", encoding="utf-8") as handle:
            payload = json.load(handle)
        return payload if isinstance(payload, dict) else {}
    except Exception:
        return {}


def _write_text(path, text):
    _ensure_parent_dir(path)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write("%s" % (text or ""))


def _maybe_fsync(handle):
    if not FORCE_WRITE_FSYNC:
        return
    handle.flush()
    os.fsync(handle.fileno())


def _append_jsonl(path, payload):
    _ensure_parent_dir(path)
    with open(path, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False) + "\n")
        _maybe_fsync(handle)


def _append_text(path, text):
    _ensure_parent_dir(path)
    with open(path, "a", encoding="utf-8") as handle:
        handle.write("%s" % (text or ""))
        _maybe_fsync(handle)


def _daily_jsonl_path(base_dir, stem, day_text):
    day = ("%s" % (day_text or "")).strip() or datetime.datetime.now().strftime("%Y-%m-%d")
    return os.path.join(base_dir, "%s-%s.jsonl" % (day, stem))


def _write_active_offer(
    parsed,
    metrics,
    traffic_verdict,
    route_shadow,
    route_line_audit,
    shortcut_source,
    now_str,
    ocr_sha1,
):
    payload = {
        "timestamp": now_str,
        "pickup_address": parsed.get("pickup_address") or "",
        "dropoff_address": parsed.get("dropoff_address") or "",
        "pickup_postcode": parsed.get("pickup_postcode") or "",
        "dropoff_postcode": parsed.get("dropoff_postcode") or "",
        "pickup_outcode": parsed.get("pickup_outcode") or "",
        "dropoff_outcode": parsed.get("dropoff_outcode") or "",
        "pickup_sector": parsed.get("pickup_sector") or "",
        "dropoff_sector": parsed.get("dropoff_sector") or "",
        "pickup_postcode_quality": parsed.get("pickup_postcode_quality") or "",
        "dropoff_postcode_quality": parsed.get("dropoff_postcode_quality") or "",
        "pickup_min": float(parsed.get("pickup_min") or 0.0),
        "pickup_miles": float(parsed.get("pickup_miles") or 0.0),
        "trip_min": float(parsed.get("trip_min") or 0.0),
        "trip_miles": float(parsed.get("trip_miles") or 0.0),
        "price": float(parsed.get("price") or 0.0),
        "rating": float(parsed.get("rating") or 0.0),
        "vehicle_type": parsed.get("vehicle_type") or "",
        "traffic_zone_status": traffic_verdict.get("status") or "",
        "traffic_zone_label": traffic_verdict.get("label") or "",
        "traffic_zone_reason": traffic_verdict.get("reason") or "",
        "traffic_zone_source": traffic_verdict.get("source") or "",
        "per_min_adj": float(metrics.get("per_min_adj") or 0.0),
        "per_mile_including_pickup": float(metrics.get("per_mile_including_pickup") or 0.0),
        "fare_for_metrics": float(metrics.get("fare_for_metrics") or 0.0),
        "hourly_adj": float(metrics.get("hourly_adj") or 0.0),
        "pay_status": metrics.get("pay_status") or "",
        "ccz_bonus_applied": bool(metrics.get("ccz_bonus_applied")),
        "is_reserved": bool(parsed.get("is_reserved")),
        "route_shadow": route_shadow,
        "route_line_audit": route_line_audit,
        "shortcut_source_tag": shortcut_source.get("tag") or "",
        "ocr_sha1": ocr_sha1 or "",
    }
    _write_json(ACTIVE_OFFER_JSON_PATH, payload)
    _append_jsonl(_daily_jsonl_path(OFFERS_HISTORY_DIR, "active_offer_history", now_str[:10]), payload)
    return payload


@on_main_thread
def _open_uber_driver_app():
    try:
        UIApplication = ObjCClass("UIApplication")
        NSURL = ObjCClass("NSURL")
        app = UIApplication.sharedApplication()
        url = NSURL.URLWithString_("uberdriver://")
        if app and url:
            app.openURL_(url)
            return True
    except Exception:
        pass
    return False


def _send_push_notification(title, body):
    if ObjCClass is None:
        return False
    try:
        _open_uber_driver_app()

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
        return True
    except Exception as exc:
        _runtime_print("[notif] failed: %s" % exc)
        return False


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
            _runtime_print("[guard] Photo guard timed out waiting for a new image asset.")
            return None

        asset = _latest_asset()
        if asset is None:
            time.sleep(poll_interval_s)
            continue

        created = getattr(asset, "creation_date", None)
        created_s = _created_str(created) if created else ""
        asset_id = getattr(asset, "local_id", None)

        if not _is_same_as_previous(asset, state):
            _runtime_print(
                "[guard] Fresh asset detected on attempt %d | id=%s | created=%s"
                % (attempt, asset_id, created_s),
            )
            return asset

        time.sleep(poll_interval_s)


def _looks_like_offer_text(ocr_text):
    text = "%s" % (ocr_text or "")
    lowered = text.lower()
    has_price = bool(re.search(r"[£$€]\s*\d", text))
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
    if re.search(r"[£$€]\s*\d", text):
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


GREEN_OUTCODE_PREFIXES = (
    "NW11", "NW8", "NW6", "NW3", "NW2", "NW1",
    "W2", "W1", "WC2", "WC1",
    "SW1", "SW3", "SW7",
)
AMBER_OUTCODE_PREFIXES = ("EC1", "EC2", "EC3", "EC4", "E1", "SE1", "SW1A", "N1")
AVOID_OUTCODE_FAMILIES = ("N", "E")
AVOID_EXACT_EXCEPTIONS = ("N1", "E1")
CENTRAL_EDGE_RULES = [
    {
        "name": "St Paul's",
        "keywords": ["st paul", "st pauls", "ludgate", "cheapside"],
        "outcodes": ["EC4", "EC1A"],
    },
    {
        "name": "City",
        "keywords": [
            "bank",
            "moorgate",
            "monument",
            "mansion house",
            "liverpool street",
            "farringdon",
            "bishopsgate",
            "bevis marks",
            "leadenhall",
            "threadneedle",
            "cornhill",
            "st mary axe",
            "old broad street",
            "finsbury circus",
        ],
        "outcodes": ["EC2", "EC3", "EC4"],
    },
    {
        "name": "London Bridge",
        "keywords": ["london bridge", "borough", "the shard"],
        "outcodes": ["SE1", "EC4R", "EC3V"],
    },
    {
        "name": "Tower Bridge",
        "keywords": ["tower bridge", "tower hill", "aldgate", "tower of london"],
        "outcodes": ["E1", "EC3", "SE1"],
    },
    {
        "name": "Westminster",
        "keywords": ["westminster", "big ben", "parliament", "whitehall", "westminster bridge"],
        "outcodes": ["SW1A", "SW1H", "SW1P"],
    },
]

TRAP_EXACT_RED_MIN = 3
TRAP_NEARBY_RED_MIN = 5
TRAP_EXACT_AMBER_MIN = 1
TRAP_NEARBY_AMBER_MIN = 2
DB_GREEN_EXACT_TIME_MIN_ABS_SCORE = 2
DB_GREEN_MIN_CONFIDENCE = "medium"
CONFIDENCE_RANK = {"low": 1, "medium": 2, "high": 3}
DB_GREEN_FRESH_MAX_DAYS = 7
DB_GREEN_RECENT_MAX_DAYS = 21
DB_GREEN_MEDIUM_MIN_SAMPLES_FRESH = 4
DB_RED_TIME_SCORE_MIN = 2
DB_RED_FRESH_MIN_SAMPLES = 3
DB_FINE_BUCKET_MINUTES = 15
DB_FINE_BUCKET_NEIGHBOR_WEIGHT = 0.6
DB_RED_MIN_DISTINCT_DAYS = 2
ROUTE_LINE_EXACT_METERS = 120.0
ROUTE_LINE_NEAR_METERS = 250.0
ROUTE_LINE_RED_SCORE_MIN = 5.0
ROUTE_LINE_AMBER_SCORE_MIN = 2.5
LINE_GRID_CELL_SIZE_METERS = 180.0
LONDON_GRID_ORIGIN_LAT = 51.5074
LONDON_GRID_ORIGIN_LON = -0.1278


def _load_traffic_beacon_db():
    if not os.path.exists(TRAFFIC_BEACON_DB_PATH):
        return {}
    try:
        mtime = os.path.getmtime(TRAFFIC_BEACON_DB_PATH)
    except Exception:
        return {}
    if _TRAFFIC_BEACON_DB_CACHE.get("mtime") == mtime and isinstance(_TRAFFIC_BEACON_DB_CACHE.get("payload"), dict):
        return _TRAFFIC_BEACON_DB_CACHE.get("payload") or {}
    try:
        with open(TRAFFIC_BEACON_DB_PATH, "r", encoding="utf-8") as handle:
            payload = json.load(handle)
            if isinstance(payload, dict):
                _TRAFFIC_BEACON_DB_CACHE["mtime"] = mtime
                _TRAFFIC_BEACON_DB_CACHE["payload"] = payload
                return payload
    except Exception:
        pass
    return {}


def _load_traffic_route_db():
    if not os.path.exists(TRAFFIC_ROUTE_DB_PATH):
        return {}
    try:
        mtime = os.path.getmtime(TRAFFIC_ROUTE_DB_PATH)
    except Exception:
        return {}
    if _ROUTE_DB_CACHE.get("mtime") == mtime and isinstance(_ROUTE_DB_CACHE.get("payload"), dict):
        return _ROUTE_DB_CACHE.get("payload") or {}
    payload = _load_json_dict(TRAFFIC_ROUTE_DB_PATH)
    _ROUTE_DB_CACHE["mtime"] = mtime
    _ROUTE_DB_CACHE["payload"] = payload
    return payload


def _load_traffic_beacon_points():
    if not os.path.exists(TRAFFIC_ROUTE_POINT_DB_PATH):
        return []
    try:
        mtime = os.path.getmtime(TRAFFIC_ROUTE_POINT_DB_PATH)
    except Exception:
        return []
    if _ROUTE_POINT_DB_CACHE.get("mtime") == mtime and isinstance(_ROUTE_POINT_DB_CACHE.get("payload"), dict):
        payload = _ROUTE_POINT_DB_CACHE.get("payload") or {}
        points = payload.get("points") or []
        return points if isinstance(points, list) else []
    payload = _load_json_dict(TRAFFIC_ROUTE_POINT_DB_PATH)
    _ROUTE_POINT_DB_CACHE["mtime"] = mtime
    _ROUTE_POINT_DB_CACHE["payload"] = payload
    points = payload.get("points") or []
    return points if isinstance(points, list) else []


def _load_traffic_line_grid_db():
    if not os.path.exists(TRAFFIC_LINE_GRID_DB_PATH):
        return {}
    try:
        mtime = os.path.getmtime(TRAFFIC_LINE_GRID_DB_PATH)
    except Exception:
        return {}
    if _LINE_GRID_DB_CACHE.get("mtime") == mtime and isinstance(_LINE_GRID_DB_CACHE.get("payload"), dict):
        return _LINE_GRID_DB_CACHE.get("payload") or {}
    payload = _load_json_dict(TRAFFIC_LINE_GRID_DB_PATH)
    _LINE_GRID_DB_CACHE["mtime"] = mtime
    _LINE_GRID_DB_CACHE["payload"] = payload
    return payload


def _parse_outcode_family(outcode):
    match = re.match(r"^([A-Z]{1,2})(\d{1,2})([A-Z]?)$", ("%s" % (outcode or "")).upper())
    if not match:
        return "", None, ""
    return match.group(1), int(match.group(2)), match.group(3)


def _traffic_bodytrap_counts(outcode, sector, beacon_db):
    normalized_outcode = ("%s" % (outcode or "")).upper()
    normalized_sector = ("%s" % (sector or "")).upper()
    outcodes = beacon_db.get("outcodes") or {}
    sectors = beacon_db.get("sectors") or {}
    families = beacon_db.get("families") or {}

    exact_outcode_bucket = outcodes.get(normalized_outcode) or {}
    exact_sector_bucket = sectors.get(normalized_sector) or {}
    exact_outcode_score = int(exact_outcode_bucket.get("net_score") or 0)
    exact_sector_score = int(exact_sector_bucket.get("net_score") or 0)
    exact_total = max(exact_outcode_score, exact_sector_score)

    family_letters, district_number, district_suffix = _parse_outcode_family(normalized_outcode)
    nearby_total = 0
    nearby_labels = []
    if family_letters and district_number is not None:
        for candidate_outcode, candidate_bucket in outcodes.items():
            candidate_family, candidate_number, candidate_suffix = _parse_outcode_family(candidate_outcode)
            if candidate_family != family_letters or candidate_number is None:
                continue
            if candidate_outcode == normalized_outcode:
                continue
            if abs(candidate_number - district_number) > 2:
                continue
            if district_suffix and candidate_suffix and district_suffix != candidate_suffix:
                continue
            candidate_score = int(candidate_bucket.get("net_score") or 0)
            if candidate_score <= 0:
                continue
            nearby_total += candidate_score
            nearby_labels.append(candidate_outcode)

    family_bucket = families.get(family_letters) or {}
    return {
        "exact_outcode_bucket": exact_outcode_bucket,
        "exact_sector_bucket": exact_sector_bucket,
        "exact_outcode_score": exact_outcode_score,
        "exact_sector_score": exact_sector_score,
        "exact_total": exact_total,
        "nearby_total": nearby_total,
        "nearby_labels": sorted(nearby_labels),
        "family_letters": family_letters,
        "district_number": district_number,
        "family_total": int(family_bucket.get("net_score") or 0),
    }


def _confidence_at_least(value, minimum):
    return CONFIDENCE_RANK.get(("%s" % (value or "")).lower(), 0) >= CONFIDENCE_RANK.get(("%s" % (minimum or "")).lower(), 0)


def _bucket_time_leaf(bucket, time_bucket):
    if not isinstance(bucket, dict):
        return {}
    leaves = bucket.get("time_buckets") or {}
    leaf = leaves.get(time_bucket) or {}
    return leaf if isinstance(leaf, dict) else {}


def _bucket_fine_time_leaf(bucket, bucket_key):
    if not isinstance(bucket, dict):
        return {}
    leaves = bucket.get("time_windows_15m") or {}
    leaf = leaves.get(bucket_key) or {}
    return leaf if isinstance(leaf, dict) else {}


def _leaf_day_keys(leaf):
    if not isinstance(leaf, dict):
        return []
    days_seen = leaf.get("days_seen") or {}
    if isinstance(days_seen, dict) and days_seen:
        return sorted([("%s" % key).strip() for key in days_seen.keys() if ("%s" % key).strip()])
    last_seen = ("%s" % (leaf.get("last_seen") or "")).strip()
    if len(last_seen) >= 10:
        return [last_seen[:10]]
    return []


def _day_key_weekday(day_key):
    text = ("%s" % (day_key or "")).strip()
    if len(text) < 10:
        return None
    try:
        return datetime.datetime.strptime(text[:10], "%Y-%m-%d").weekday()
    except Exception:
        return None


def _leaf_weekday_relevance(leaf, now_dt):
    day_keys = _leaf_day_keys(leaf)
    if not day_keys:
        return {
            "same_weekday_days": 0,
            "same_weekpart_days": 0,
            "multiplier": 0.75,
            "label": "unknown_days",
        }
    target_weekday = int(now_dt.weekday())
    target_is_weekday = target_weekday < 5
    same_weekday_days = 0
    same_weekpart_days = 0
    for day_key in day_keys:
        weekday_value = _day_key_weekday(day_key)
        if weekday_value is None:
            continue
        if weekday_value == target_weekday:
            same_weekday_days += 1
        if (weekday_value < 5) == target_is_weekday:
            same_weekpart_days += 1
    if same_weekday_days >= 2:
        return {
            "same_weekday_days": same_weekday_days,
            "same_weekpart_days": same_weekpart_days,
            "multiplier": 1.0,
            "label": "same_weekday_strong",
        }
    if same_weekday_days == 1:
        return {
            "same_weekday_days": same_weekday_days,
            "same_weekpart_days": same_weekpart_days,
            "multiplier": 0.92,
            "label": "same_weekday_thin",
        }
    if same_weekpart_days >= 3:
        return {
            "same_weekday_days": same_weekday_days,
            "same_weekpart_days": same_weekpart_days,
            "multiplier": 0.78,
            "label": "same_weekpart_only",
        }
    if same_weekpart_days >= 1:
        return {
            "same_weekday_days": same_weekday_days,
            "same_weekpart_days": same_weekpart_days,
            "multiplier": 0.65,
            "label": "same_weekpart_sparse",
        }
    return {
        "same_weekday_days": same_weekday_days,
        "same_weekpart_days": same_weekpart_days,
        "multiplier": 0.45,
        "label": "cross_period_only",
    }


def _leaf_weighted_time_metrics(leaf, now_dt):
    relevance = _leaf_weekday_relevance(leaf, now_dt)
    multiplier = float(relevance.get("multiplier") or 0.0)
    return {
        "score": round(float(leaf.get("net_score") or 0.0) * multiplier, 2),
        "samples": round(float(leaf.get("samples") or 0.0) * multiplier, 2),
        "confidence": leaf.get("confidence") or "low",
        "last_seen": leaf.get("last_seen") or "",
        "distinct_days": len(_leaf_day_keys(leaf)),
        "day_keys": _leaf_day_keys(leaf),
        "same_weekday_days": int(relevance.get("same_weekday_days") or 0),
        "same_weekpart_days": int(relevance.get("same_weekpart_days") or 0),
        "weekday_relevance": relevance.get("label") or "",
        "weekday_multiplier": multiplier,
    }


def _parse_local_timestamp(value):
    text = ("%s" % (value or "")).strip()
    if not text:
        return None
    try:
        return datetime.datetime.strptime(text, "%Y-%m-%d %H:%M:%S")
    except Exception:
        return None


def _days_since_timestamp(value, now_dt):
    parsed = _parse_local_timestamp(value)
    if parsed is None:
        return None
    delta = now_dt - parsed
    return max(0.0, delta.total_seconds() / 86400.0)


def _fine_bucket_start(now_dt):
    minute_floor = (now_dt.minute // DB_FINE_BUCKET_MINUTES) * DB_FINE_BUCKET_MINUTES
    return now_dt.replace(minute=minute_floor, second=0, microsecond=0)


def _fine_bucket_key(dt_obj):
    prefix = "weekday" if dt_obj.weekday() < 5 else "weekend"
    return "%s-%02d:%02d" % (prefix, dt_obj.hour, dt_obj.minute)


def _fine_bucket_neighbor_keys(now_dt):
    start_dt = _fine_bucket_start(now_dt)
    return [
        (_fine_bucket_key(start_dt), 1.0),
        (_fine_bucket_key(start_dt - datetime.timedelta(minutes=DB_FINE_BUCKET_MINUTES)), DB_FINE_BUCKET_NEIGHBOR_WEIGHT),
        (_fine_bucket_key(start_dt + datetime.timedelta(minutes=DB_FINE_BUCKET_MINUTES)), DB_FINE_BUCKET_NEIGHBOR_WEIGHT),
    ]


def _leaf_rank(leaf):
    return CONFIDENCE_RANK.get(("%s" % ((leaf or {}).get("confidence") or "")).lower(), 0)


def _weighted_fine_bucket_metrics(bucket, now_dt):
    weighted_score = 0.0
    weighted_samples = 0.0
    best_confidence = "low"
    best_rank = 0
    latest_seen = ""
    latest_dt = None
    matched = []
    day_keys = set()
    same_weekday_days = 0
    same_weekpart_days = 0
    best_weekday_label = ""
    best_weekday_multiplier = 0.0

    for bucket_key, weight in _fine_bucket_neighbor_keys(now_dt):
        leaf = _bucket_fine_time_leaf(bucket, bucket_key)
        if not leaf:
            continue
        matched.append(bucket_key)
        for day_key in _leaf_day_keys(leaf):
            day_keys.add(day_key)
        relevance = _leaf_weekday_relevance(leaf, now_dt)
        weekday_multiplier = float(relevance.get("multiplier") or 0.0)
        effective_weight = float(weight) * weekday_multiplier
        weighted_score += float(leaf.get("net_score") or 0.0) * effective_weight
        weighted_samples += float(leaf.get("samples") or 0.0) * effective_weight
        same_weekday_days += int(relevance.get("same_weekday_days") or 0)
        same_weekpart_days += int(relevance.get("same_weekpart_days") or 0)
        if weekday_multiplier > best_weekday_multiplier:
            best_weekday_multiplier = weekday_multiplier
            best_weekday_label = relevance.get("label") or ""
        rank = _leaf_rank(leaf)
        if rank > best_rank:
            best_rank = rank
            best_confidence = leaf.get("confidence") or "low"
        seen_text = leaf.get("last_seen") or ""
        seen_dt = _parse_local_timestamp(seen_text)
        if seen_dt and (latest_dt is None or seen_dt > latest_dt):
            latest_dt = seen_dt
            latest_seen = seen_text

    return {
        "score": round(weighted_score, 2),
        "samples": round(weighted_samples, 2),
        "confidence": best_confidence,
        "last_seen": latest_seen,
        "matched_buckets": matched,
        "distinct_days": len(day_keys),
        "day_keys": sorted(day_keys),
        "same_weekday_days": same_weekday_days,
        "same_weekpart_days": same_weekpart_days,
        "weekday_relevance": best_weekday_label,
        "weekday_multiplier": round(best_weekday_multiplier, 2),
    }


def _green_time_bucket_gate(score, samples, confidence, last_seen, now_dt):
    if score > -DB_GREEN_EXACT_TIME_MIN_ABS_SCORE:
        return False, "score_too_weak", None
    age_days = _days_since_timestamp(last_seen, now_dt)
    if age_days is None:
        return False, "missing_last_seen", None
    if age_days <= DB_GREEN_FRESH_MAX_DAYS:
        if _confidence_at_least(confidence, DB_GREEN_MIN_CONFIDENCE) and int(samples or 0) >= DB_GREEN_MEDIUM_MIN_SAMPLES_FRESH:
            return True, "fresh", age_days
        return False, "fresh_but_low_confidence", age_days
    if age_days <= DB_GREEN_RECENT_MAX_DAYS:
        if _confidence_at_least(confidence, "high"):
            return True, "recent_high_confidence", age_days
        return False, "recent_not_high_confidence", age_days
    return False, "stale", age_days


def _positive_time_bucket_gate(score, samples, confidence, last_seen, now_dt, min_score, min_samples_fresh):
    if score < int(min_score or 0):
        return False, "score_too_weak", None
    age_days = _days_since_timestamp(last_seen, now_dt)
    if age_days is None:
        return False, "missing_last_seen", None
    if age_days <= DB_GREEN_FRESH_MAX_DAYS:
        if _confidence_at_least(confidence, DB_GREEN_MIN_CONFIDENCE) and int(samples or 0) >= int(min_samples_fresh or 0):
            return True, "fresh", age_days
        return False, "fresh_but_low_confidence", age_days
    if age_days <= DB_GREEN_RECENT_MAX_DAYS:
        if _confidence_at_least(confidence, "high"):
            return True, "recent_high_confidence", age_days
        return False, "recent_not_high_confidence", age_days
    return False, "stale", age_days


def _route_shadow_status_hint(net_score, samples, time_score, time_samples):
    if int(time_samples or 0) >= 3 and float(time_score or 0.0) >= 3.0:
        return "strong"
    if int(samples or 0) >= 4 and float(net_score or 0.0) >= 4.0:
        return "watch"
    if int(samples or 0) > 0 or int(time_samples or 0) > 0:
        return "weak"
    return "none"


def _opposite_direction_bin(direction):
    direction_order = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
    normalized = ("%s" % (direction or "")).strip().upper()
    if normalized not in direction_order:
        return ""
    index = direction_order.index(normalized)
    return direction_order[(index + 4) % len(direction_order)]


def _counter_direction_hits(counter, primary_direction):
    if not isinstance(counter, dict):
        return {"direction": "", "hits": 0}
    opposite = _opposite_direction_bin(primary_direction)
    if not opposite:
        return {"direction": "", "hits": 0}
    return {
        "direction": opposite,
        "hits": int(counter.get(opposite) or 0),
    }


def _local_xy_meters(lat, lon, origin_lat, origin_lon):
    earth_radius = 6371000.0
    lat_rad = math.radians(float(lat or 0.0))
    origin_lat_rad = math.radians(float(origin_lat or 0.0))
    dlat = lat_rad - origin_lat_rad
    dlon = math.radians(float(lon or 0.0) - float(origin_lon or 0.0))
    x = dlon * math.cos((lat_rad + origin_lat_rad) / 2.0) * earth_radius
    y = dlat * earth_radius
    return x, y


def _distance_point_to_segment_meters(point_lat, point_lon, start_lat, start_lon, end_lat, end_lon):
    origin_lat = float(start_lat or 0.0)
    origin_lon = float(start_lon or 0.0)
    ax, ay = 0.0, 0.0
    bx, by = _local_xy_meters(end_lat, end_lon, origin_lat, origin_lon)
    px, py = _local_xy_meters(point_lat, point_lon, origin_lat, origin_lon)
    abx = bx - ax
    aby = by - ay
    ab_len_sq = abx * abx + aby * aby
    if ab_len_sq <= 0.0001:
        return math.hypot(px - ax, py - ay), 0.0
    t = ((px - ax) * abx + (py - ay) * aby) / ab_len_sq
    t_clamped = max(0.0, min(1.0, t))
    cx = ax + t_clamped * abx
    cy = ay + t_clamped * aby
    return math.hypot(px - cx, py - cy), t_clamped


def _line_grid_xy_meters(latitude, longitude):
    earth_radius = 6371000.0
    lat = _safe_float(latitude, 0.0)
    lon = _safe_float(longitude, 0.0)
    if abs(lat) < 0.000001 and abs(lon) < 0.000001:
        return 0.0, 0.0
    lat_rad = math.radians(lat)
    origin_lat_rad = math.radians(LONDON_GRID_ORIGIN_LAT)
    dlat = lat_rad - origin_lat_rad
    dlon = math.radians(lon - LONDON_GRID_ORIGIN_LON)
    x = dlon * math.cos(origin_lat_rad) * earth_radius
    y = dlat * earth_radius
    return x, y


def _route_line_candidate_grid_keys(pickup_endpoint, dropoff_endpoint, cell_size_m, corridor_radius_m):
    x1, y1 = _line_grid_xy_meters(pickup_endpoint.get("lat"), pickup_endpoint.get("lon"))
    x2, y2 = _line_grid_xy_meters(dropoff_endpoint.get("lat"), dropoff_endpoint.get("lon"))
    route_length_m = math.hypot(x2 - x1, y2 - y1)
    if route_length_m <= 0.0001:
        return [], route_length_m
    sample_step_m = max(40.0, float(cell_size_m or LINE_GRID_CELL_SIZE_METERS) * 0.5)
    steps = max(1, int(math.ceil(route_length_m / sample_step_m)))
    cell_reach = max(1, int(math.ceil(float(corridor_radius_m or 0.0) / max(float(cell_size_m or 1.0), 1.0))))
    keys = set()
    for index in range(steps + 1):
        progress = float(index) / float(steps)
        sample_x = x1 + (x2 - x1) * progress
        sample_y = y1 + (y2 - y1) * progress
        base_x = int(round(sample_x / float(cell_size_m or LINE_GRID_CELL_SIZE_METERS)))
        base_y = int(round(sample_y / float(cell_size_m or LINE_GRID_CELL_SIZE_METERS)))
        for dx in range(-cell_reach, cell_reach + 1):
            for dy in range(-cell_reach, cell_reach + 1):
                ix = base_x + dx
                iy = base_y + dy
                center_x = float(ix) * float(cell_size_m or LINE_GRID_CELL_SIZE_METERS)
                center_y = float(iy) * float(cell_size_m or LINE_GRID_CELL_SIZE_METERS)
                if math.hypot(center_x - sample_x, center_y - sample_y) <= float(corridor_radius_m or 0.0) + float(cell_size_m or LINE_GRID_CELL_SIZE_METERS):
                    keys.add("%s,%s" % (ix, iy))
    return sorted(keys), route_length_m


def _resolve_beacon_centroid(parsed, prefix, beacon_db):
    sector = ("%s" % ((parsed or {}).get("%s_sector" % prefix) or "")).strip().upper()
    outcode = ("%s" % ((parsed or {}).get("%s_outcode" % prefix) or "")).strip().upper()
    sector_bucket = ((beacon_db.get("sectors") or {}).get(sector) or {}) if sector else {}
    outcode_bucket = ((beacon_db.get("outcodes") or {}).get(outcode) or {}) if outcode else {}
    for scope, bucket, key in (
        ("sector", sector_bucket, sector),
        ("outcode", outcode_bucket, outcode),
    ):
        lat = _safe_float(bucket.get("centroid_lat"), 0.0)
        lon = _safe_float(bucket.get("centroid_lon"), 0.0)
        geo_samples = int(bucket.get("geo_samples") or 0)
        if geo_samples > 0 and abs(lat) > 0.000001 and abs(lon) > 0.000001:
            return {
                "resolved": True,
                "scope": scope,
                "key": key,
                "lat": lat,
                "lon": lon,
                "geo_samples": geo_samples,
            }
    return {
        "resolved": False,
        "scope": "",
        "key": sector or outcode,
        "lat": 0.0,
        "lon": 0.0,
        "geo_samples": 0,
    }


def _route_shadow_direction_summary(route_shadow):
    if not isinstance(route_shadow, dict):
        return {"mode": "", "direction": "", "hits": 0, "counter_direction": "", "counter_hits": 0, "summary": ""}

    flow_direction = ("%s" % (route_shadow.get("dominant_flow_direction") or "")).strip().upper()
    flow_hits = int(route_shadow.get("dominant_flow_hits") or 0)
    flow_counter_direction = ("%s" % (route_shadow.get("counter_flow_direction") or "")).strip().upper()
    flow_counter_hits = int(route_shadow.get("counter_flow_hits") or 0)
    if flow_direction and flow_hits > 0:
        summary = "Flow %s x%d" % (flow_direction, flow_hits)
        if flow_counter_direction and flow_counter_hits > 0:
            summary += " | Opp %s x%d" % (flow_counter_direction, flow_counter_hits)
        return {
            "mode": "flow",
            "direction": flow_direction,
            "hits": flow_hits,
            "counter_direction": flow_counter_direction,
            "counter_hits": flow_counter_hits,
            "summary": summary,
        }

    course_direction = ("%s" % (route_shadow.get("dominant_course_direction") or "")).strip().upper()
    course_hits = int(route_shadow.get("dominant_course_hits") or 0)
    course_counter_direction = ("%s" % (route_shadow.get("counter_course_direction") or "")).strip().upper()
    course_counter_hits = int(route_shadow.get("counter_course_hits") or 0)
    if course_direction and course_hits > 0:
        summary = "Course %s x%d" % (course_direction, course_hits)
        if course_counter_direction and course_counter_hits > 0:
            summary += " | Opp %s x%d" % (course_counter_direction, course_counter_hits)
        return {
            "mode": "course",
            "direction": course_direction,
            "hits": course_hits,
            "counter_direction": course_counter_direction,
            "counter_hits": course_counter_hits,
            "summary": summary,
        }

    return {"mode": "", "direction": "", "hits": 0, "counter_direction": "", "counter_hits": 0, "summary": ""}


def _route_line_status_hint(exact_hits, near_hits, time_hits):
    exact = int(exact_hits or 0)
    near = int(near_hits or 0)
    timed = int(time_hits or 0)
    if exact >= 2 or (exact >= 1 and timed >= 1):
        return "strong"
    if exact + near >= 2:
        return "watch"
    if exact + near >= 1:
        return "weak"
    return "none"


def _route_line_hit_weight(beacon_dt, now_dt, distance_m):
    if beacon_dt is None:
        time_weight = 0.45
        bucket_match = False
        adjacent_match = False
    else:
        delta_minutes = abs((now_dt - beacon_dt).total_seconds()) / 60.0
        bucket_match = delta_minutes <= float(DB_FINE_BUCKET_MINUTES)
        adjacent_match = delta_minutes <= float(DB_FINE_BUCKET_MINUTES * 2)
        if bucket_match:
            time_weight = 1.0
        elif adjacent_match:
            time_weight = 0.7
        elif _traffic_time_bucket(beacon_dt) == _traffic_time_bucket(now_dt):
            time_weight = 0.45
        else:
            time_weight = 0.2
    distance_value = float(distance_m or 0.0)
    if distance_value <= ROUTE_LINE_EXACT_METERS:
        distance_weight = 3.0 if bucket_match else 2.0 if adjacent_match else 1.5
    else:
        distance_weight = 2.0 if bucket_match else 1.0 if adjacent_match else 0.6
    return {
        "score": round(distance_weight * time_weight, 2),
        "bucket_match": bucket_match,
        "adjacent_match": adjacent_match,
        "time_weight": round(time_weight, 2),
        "distance_weight": round(distance_weight, 2),
    }


def _route_line_shadow_snapshot(parsed, now_dt=None):
    now_dt = now_dt or datetime.datetime.now()
    payload = {
        "enabled": True,
        "matched": False,
        "source": "beacon_line_shadow",
        "model": "line_grid_v2",
        "time_bucket": _traffic_time_bucket(now_dt),
        "pickup_endpoint": {},
        "dropoff_endpoint": {},
        "route_length_m": 0.0,
        "candidate_cells": 0,
        "matched_cells": 0,
        "cell_size_m": 0.0,
        "exact_hits": 0,
        "near_hits": 0,
        "time_bucket_hits": 0,
        "unique_outcodes": 0,
        "unique_sectors": 0,
        "top_outcodes": [],
        "top_sectors": [],
        "closest_hit_m": 0.0,
        "status_hint": "none",
        "trap_score": 0.0,
        "same_weekday_days": 0,
        "same_weekpart_days": 0,
        "weekday_relevance": "",
        "weekday_multiplier": 0.0,
        "matched_fine_buckets": [],
        "adjacent_fine_buckets": [],
        "strong_time_hits": 0,
    }
    beacon_db = _load_traffic_beacon_db()
    if not beacon_db:
        return payload

    pickup_endpoint = _resolve_beacon_centroid(parsed, "pickup", beacon_db)
    dropoff_endpoint = _resolve_beacon_centroid(parsed, "dropoff", beacon_db)
    payload["pickup_endpoint"] = pickup_endpoint
    payload["dropoff_endpoint"] = dropoff_endpoint
    if not pickup_endpoint.get("resolved") or not dropoff_endpoint.get("resolved"):
        return payload

    line_grid_db = _load_traffic_line_grid_db()
    cells = line_grid_db.get("cells") or {}
    if not isinstance(cells, dict) or not cells:
        return payload
    cell_size_m = float(line_grid_db.get("cell_size_m") or LINE_GRID_CELL_SIZE_METERS)
    payload["cell_size_m"] = round(cell_size_m, 1)
    candidate_keys, route_length_m = _route_line_candidate_grid_keys(
        pickup_endpoint,
        dropoff_endpoint,
        cell_size_m,
        ROUTE_LINE_NEAR_METERS,
    )
    payload["route_length_m"] = round(route_length_m, 1)
    payload["candidate_cells"] = len(candidate_keys)
    if not candidate_keys:
        return payload

    exact_hits = 0
    near_hits = 0
    time_hits = 0
    strong_time_hits = 0
    closest_hit = None
    outcode_counts = {}
    sector_counts = {}
    offer_bucket = payload["time_bucket"]
    offer_fine_keys = _fine_bucket_neighbor_keys(now_dt)
    offer_primary_fine_bucket = offer_fine_keys[0][0] if offer_fine_keys else ""
    offer_neighbor_fine_buckets = {item[0] for item in offer_fine_keys[1:]}
    matched_fine_buckets = set()
    adjacent_fine_buckets = set()
    trap_score = 0.0
    best_same_weekday_days = 0
    best_same_weekpart_days = 0
    best_weekday_relevance = ""
    best_weekday_multiplier = 0.0

    for cell_key in candidate_keys:
        entry = cells.get(cell_key) or {}
        if not isinstance(entry, dict) or not entry:
            continue
        lat = _safe_float(entry.get("center_lat"), 0.0)
        lon = _safe_float(entry.get("center_lon"), 0.0)
        if abs(lat) < 0.000001 and abs(lon) < 0.000001:
            continue
        distance_m, progress = _distance_point_to_segment_meters(
            lat,
            lon,
            pickup_endpoint["lat"],
            pickup_endpoint["lon"],
            dropoff_endpoint["lat"],
            dropoff_endpoint["lon"],
        )
        if distance_m > ROUTE_LINE_NEAR_METERS:
            continue
        weighted = _weighted_fine_bucket_metrics(entry, now_dt)
        if not weighted.get("matched_buckets"):
            coarse_leaf = _bucket_time_leaf(entry, offer_bucket)
            coarse_metrics = _leaf_weighted_time_metrics(coarse_leaf, now_dt) if coarse_leaf else {}
            weighted = {
                "score": float(coarse_metrics.get("score") or 0.0),
                "samples": float(coarse_metrics.get("samples") or 0.0),
                "confidence": coarse_metrics.get("confidence") or "low",
                "last_seen": coarse_metrics.get("last_seen") or "",
                "matched_buckets": [offer_bucket] if coarse_leaf else [],
                "distinct_days": int(coarse_metrics.get("distinct_days") or 0),
                "day_keys": coarse_metrics.get("day_keys") or [],
                "same_weekday_days": int(coarse_metrics.get("same_weekday_days") or 0),
                "same_weekpart_days": int(coarse_metrics.get("same_weekpart_days") or 0),
                "weekday_relevance": coarse_metrics.get("weekday_relevance") or "",
                "weekday_multiplier": float(coarse_metrics.get("weekday_multiplier") or 0.0),
            }
        signal_score = max(0.0, float(weighted.get("score") or 0.0))
        if signal_score <= 0.0 and float(entry.get("net_score") or 0.0) <= 0.0:
            continue
        payload["matched_cells"] = int(payload.get("matched_cells") or 0) + 1
        if distance_m <= ROUTE_LINE_EXACT_METERS:
            exact_hits += 1
        else:
            near_hits += 1
        matched_buckets = weighted.get("matched_buckets") or []
        if matched_buckets:
            time_hits += 1
        if offer_primary_fine_bucket and offer_primary_fine_bucket in matched_buckets:
            matched_fine_buckets.add(offer_primary_fine_bucket)
            strong_time_hits += 1
        for candidate_bucket in matched_buckets:
            if candidate_bucket == offer_primary_fine_bucket:
                continue
            if candidate_bucket in offer_neighbor_fine_buckets:
                adjacent_fine_buckets.add(candidate_bucket)
        same_weekday_days = int(weighted.get("same_weekday_days") or 0)
        same_weekpart_days = int(weighted.get("same_weekpart_days") or 0)
        weekday_multiplier = float(weighted.get("weekday_multiplier") or 0.0)
        if same_weekday_days > best_same_weekday_days:
            best_same_weekday_days = same_weekday_days
        if same_weekpart_days > best_same_weekpart_days:
            best_same_weekpart_days = same_weekpart_days
        if weekday_multiplier > best_weekday_multiplier:
            best_weekday_multiplier = weekday_multiplier
            best_weekday_relevance = weighted.get("weekday_relevance") or ""
        trap_score += signal_score * (1.25 if distance_m <= ROUTE_LINE_EXACT_METERS else 0.75)
        for outcode, hits in (entry.get("beacon_outcodes") or {}).items():
            normalized_outcode = ("%s" % (outcode or "")).strip().upper()
            if normalized_outcode and int(hits or 0) > 0:
                outcode_counts[normalized_outcode] = int(outcode_counts.get(normalized_outcode) or 0) + int(hits or 0)
        for sector, hits in (entry.get("beacon_sectors") or {}).items():
            normalized_sector = ("%s" % (sector or "")).strip().upper()
            if normalized_sector and int(hits or 0) > 0:
                sector_counts[normalized_sector] = int(sector_counts.get(normalized_sector) or 0) + int(hits or 0)
        hit = {
            "distance_m": round(distance_m, 1),
            "progress": round(progress, 3),
            "cell": cell_key,
            "outcode": next(iter(sorted((entry.get("beacon_outcodes") or {}).keys())), ""),
            "sector": next(iter(sorted((entry.get("beacon_sectors") or {}).keys())), ""),
            "timestamp": weighted.get("last_seen") or entry.get("last_seen") or "",
        }
        if closest_hit is None or hit["distance_m"] < closest_hit["distance_m"]:
            closest_hit = hit

    if exact_hits <= 0 and near_hits <= 0:
        return payload

    payload.update(
        {
            "matched": True,
            "exact_hits": exact_hits,
            "near_hits": near_hits,
            "time_bucket_hits": time_hits,
            "strong_time_hits": strong_time_hits,
            "unique_outcodes": len(outcode_counts),
            "unique_sectors": len(sector_counts),
            "top_outcodes": [item[0] for item in sorted(outcode_counts.items(), key=lambda item: (-item[1], item[0]))[:3]],
            "top_sectors": [item[0] for item in sorted(sector_counts.items(), key=lambda item: (-item[1], item[0]))[:3]],
            "closest_hit_m": round(float((closest_hit or {}).get("distance_m") or 0.0), 1),
            "status_hint": _route_line_status_hint(exact_hits, near_hits, time_hits),
            "trap_score": round(trap_score, 2),
            "same_weekday_days": best_same_weekday_days,
            "same_weekpart_days": best_same_weekpart_days,
            "weekday_relevance": best_weekday_relevance,
            "weekday_multiplier": round(best_weekday_multiplier, 2),
            "matched_fine_buckets": sorted(matched_fine_buckets),
            "adjacent_fine_buckets": sorted(adjacent_fine_buckets),
        }
    )
    return payload


def _route_shadow_snapshot(parsed, now_dt=None):
    now_dt = now_dt or datetime.datetime.now()
    pickup_outcode = ("%s" % (parsed.get("pickup_outcode") or "")).upper()
    dropoff_outcode = ("%s" % (parsed.get("dropoff_outcode") or "")).upper()
    route_key = "%s->%s" % (pickup_outcode or "UNK", dropoff_outcode or "UNK")
    payload = {
        "enabled": True,
        "matched": False,
        "source": "route_db_shadow",
        "route_key": route_key,
        "pickup_outcode": pickup_outcode,
        "dropoff_outcode": dropoff_outcode,
        "samples": 0,
        "net_score": 0,
        "confidence": "low",
        "last_seen": "",
        "unique_day_hits": 0,
        "unique_beacon_outcodes": 0,
        "unique_beacon_sectors": 0,
        "dominant_course_direction": "",
        "dominant_course_hits": 0,
        "counter_course_direction": "",
        "counter_course_hits": 0,
        "dominant_flow_direction": "",
        "dominant_flow_hits": 0,
        "counter_flow_direction": "",
        "counter_flow_hits": 0,
        "direction_summary": "",
        "corridor_unique_cells": 0,
        "corridor_unique_segments": 0,
        "time_bucket": _traffic_time_bucket(now_dt),
        "time_bucket_score": 0.0,
        "time_bucket_samples": 0.0,
        "time_bucket_confidence": "low",
        "time_bucket_last_seen": "",
        "time_bucket_distinct_days": 0,
        "time_bucket_day_keys": [],
        "status_hint": "none",
    }
    if not pickup_outcode or not dropoff_outcode:
        return payload

    route_db = _load_traffic_route_db()
    route_bucket = ((route_db.get("routes") or {}).get(route_key) or {})
    if not isinstance(route_bucket, dict) or not route_bucket:
        return payload

    weighted = _weighted_fine_bucket_metrics(route_bucket, now_dt)
    if not weighted.get("matched_buckets"):
        coarse_leaf = _bucket_time_leaf(route_bucket, payload["time_bucket"])
        coarse_metrics = _leaf_weighted_time_metrics(coarse_leaf, now_dt) if coarse_leaf else {}
        weighted = {
            "score": float(coarse_metrics.get("score") or 0.0),
            "samples": float(coarse_metrics.get("samples") or 0.0),
            "confidence": coarse_metrics.get("confidence") or "low",
            "last_seen": coarse_metrics.get("last_seen") or "",
            "matched_buckets": [payload["time_bucket"]] if coarse_leaf else [],
            "distinct_days": int(coarse_metrics.get("distinct_days") or 0),
            "day_keys": coarse_metrics.get("day_keys") or [],
            "same_weekday_days": int(coarse_metrics.get("same_weekday_days") or 0),
            "same_weekpart_days": int(coarse_metrics.get("same_weekpart_days") or 0),
            "weekday_relevance": coarse_metrics.get("weekday_relevance") or "",
            "weekday_multiplier": float(coarse_metrics.get("weekday_multiplier") or 0.0),
        }

    samples = int(route_bucket.get("samples") or 0)
    net_score = int(route_bucket.get("net_score") or 0)
    time_score = float(weighted.get("score") or 0.0)
    time_samples = float(weighted.get("samples") or 0.0)
    flow_counter = _counter_direction_hits(route_bucket.get("flow_direction_bins") or {}, route_bucket.get("dominant_flow_direction") or "")
    course_counter = _counter_direction_hits(route_bucket.get("course_bins") or {}, route_bucket.get("dominant_course_direction") or "")
    payload.update(
        {
            "matched": True,
            "samples": samples,
            "net_score": net_score,
            "confidence": route_bucket.get("confidence") or "low",
            "last_seen": route_bucket.get("last_seen") or "",
            "unique_day_hits": int(route_bucket.get("unique_day_hits") or 0),
            "unique_beacon_outcodes": int(route_bucket.get("unique_beacon_outcodes") or 0),
            "unique_beacon_sectors": int(route_bucket.get("unique_beacon_sectors") or 0),
            "dominant_course_direction": route_bucket.get("dominant_course_direction") or "",
            "dominant_course_hits": int(route_bucket.get("dominant_course_hits") or 0),
            "counter_course_direction": course_counter.get("direction") or "",
            "counter_course_hits": int(course_counter.get("hits") or 0),
            "dominant_flow_direction": route_bucket.get("dominant_flow_direction") or "",
            "dominant_flow_hits": int(route_bucket.get("dominant_flow_hits") or 0),
            "counter_flow_direction": flow_counter.get("direction") or "",
            "counter_flow_hits": int(flow_counter.get("hits") or 0),
            "corridor_unique_cells": int(route_bucket.get("corridor_unique_cells") or 0),
            "corridor_unique_segments": int(route_bucket.get("corridor_unique_segments") or 0),
            "time_bucket_score": round(time_score, 2),
            "time_bucket_samples": round(time_samples, 2),
            "time_bucket_confidence": weighted.get("confidence") or "low",
            "time_bucket_last_seen": weighted.get("last_seen") or "",
            "time_bucket_distinct_days": int(weighted.get("distinct_days") or 0),
            "time_bucket_day_keys": weighted.get("day_keys") or [],
            "time_bucket_same_weekday_days": int(weighted.get("same_weekday_days") or 0),
            "time_bucket_same_weekpart_days": int(weighted.get("same_weekpart_days") or 0),
            "time_bucket_weekday_relevance": weighted.get("weekday_relevance") or "",
            "time_bucket_weekday_multiplier": round(float(weighted.get("weekday_multiplier") or 0.0), 2),
            "status_hint": _route_shadow_status_hint(net_score, samples, time_score, time_samples),
        }
    )
    payload["direction_summary"] = _route_shadow_direction_summary(payload).get("summary") or ""
    return payload


def _traffic_db_verdict(parsed, now_dt=None):
    now_dt = now_dt or datetime.datetime.now()
    current_time_bucket = _traffic_time_bucket(now_dt)
    beacon_db = _load_traffic_beacon_db()
    if not beacon_db:
        return None

    total_entries = int(beacon_db.get("total_entries") or 0)
    if total_entries <= 0:
        return None

    dropoff_outcode = parsed.get("dropoff_outcode") or ""
    dropoff_sector = parsed.get("dropoff_sector") or ""
    dropoff_quality = _postcode_quality(parsed, "dropoff")
    if not dropoff_outcode:
        return None

    counts = _traffic_bodytrap_counts(dropoff_outcode, dropoff_sector, beacon_db)
    exact_total = counts["exact_total"]
    nearby_total = counts["nearby_total"]
    nearby_labels = counts["nearby_labels"]
    label = ("%s traps" % dropoff_outcode).strip()

    outcode_time = _weighted_fine_bucket_metrics(counts["exact_outcode_bucket"], now_dt)
    sector_time = _weighted_fine_bucket_metrics(counts["exact_sector_bucket"], now_dt)
    if not outcode_time["matched_buckets"] and not sector_time["matched_buckets"]:
        outcode_time_leaf = _bucket_time_leaf(counts["exact_outcode_bucket"], current_time_bucket)
        sector_time_leaf = _bucket_time_leaf(counts["exact_sector_bucket"], current_time_bucket)
        outcode_leaf_metrics = _leaf_weighted_time_metrics(outcode_time_leaf, now_dt) if outcode_time_leaf else {}
        sector_leaf_metrics = _leaf_weighted_time_metrics(sector_time_leaf, now_dt) if sector_time_leaf else {}
        outcode_time = {
            "score": float(outcode_leaf_metrics.get("score") or 0.0),
            "samples": float(outcode_leaf_metrics.get("samples") or 0.0),
            "confidence": outcode_leaf_metrics.get("confidence") or "low",
            "last_seen": outcode_leaf_metrics.get("last_seen") or "",
            "matched_buckets": [current_time_bucket] if outcode_time_leaf else [],
            "distinct_days": int(outcode_leaf_metrics.get("distinct_days") or 0),
            "day_keys": outcode_leaf_metrics.get("day_keys") or [],
            "same_weekday_days": int(outcode_leaf_metrics.get("same_weekday_days") or 0),
            "same_weekpart_days": int(outcode_leaf_metrics.get("same_weekpart_days") or 0),
            "weekday_relevance": outcode_leaf_metrics.get("weekday_relevance") or "",
            "weekday_multiplier": float(outcode_leaf_metrics.get("weekday_multiplier") or 0.0),
        }
        sector_time = {
            "score": float(sector_leaf_metrics.get("score") or 0.0),
            "samples": float(sector_leaf_metrics.get("samples") or 0.0),
            "confidence": sector_leaf_metrics.get("confidence") or "low",
            "last_seen": sector_leaf_metrics.get("last_seen") or "",
            "matched_buckets": [current_time_bucket] if sector_time_leaf else [],
            "distinct_days": int(sector_leaf_metrics.get("distinct_days") or 0),
            "day_keys": sector_leaf_metrics.get("day_keys") or [],
            "same_weekday_days": int(sector_leaf_metrics.get("same_weekday_days") or 0),
            "same_weekpart_days": int(sector_leaf_metrics.get("same_weekpart_days") or 0),
            "weekday_relevance": sector_leaf_metrics.get("weekday_relevance") or "",
            "weekday_multiplier": float(sector_leaf_metrics.get("weekday_multiplier") or 0.0),
        }

    outcode_time_score = float(outcode_time["score"])
    sector_time_score = float(sector_time["score"])
    outcode_time_samples = float(outcode_time["samples"])
    sector_time_samples = float(sector_time["samples"])
    outcode_time_confidence = outcode_time["confidence"]
    sector_time_confidence = sector_time["confidence"]
    outcode_time_last_seen = outcode_time["last_seen"]
    sector_time_last_seen = sector_time["last_seen"]

    best_positive_score = max(outcode_time_score, sector_time_score)
    best_positive_samples = sector_time_samples
    best_positive_confidence = sector_time_confidence
    best_positive_last_seen = sector_time_last_seen
    best_positive_match = sector_time["matched_buckets"]
    best_positive_days = int(sector_time.get("distinct_days") or 0)
    best_positive_day_keys = sector_time.get("day_keys") or []
    best_positive_same_weekday_days = int(sector_time.get("same_weekday_days") or 0)
    best_positive_same_weekpart_days = int(sector_time.get("same_weekpart_days") or 0)
    best_positive_weekday_relevance = sector_time.get("weekday_relevance") or ""
    best_positive_weekday_multiplier = float(sector_time.get("weekday_multiplier") or 0.0)
    if outcode_time_score >= sector_time_score:
        best_positive_samples = outcode_time_samples
        best_positive_confidence = outcode_time_confidence
        best_positive_last_seen = outcode_time_last_seen
        best_positive_match = outcode_time["matched_buckets"]
        best_positive_days = int(outcode_time.get("distinct_days") or 0)
        best_positive_day_keys = outcode_time.get("day_keys") or []
        best_positive_same_weekday_days = int(outcode_time.get("same_weekday_days") or 0)
        best_positive_same_weekpart_days = int(outcode_time.get("same_weekpart_days") or 0)
        best_positive_weekday_relevance = outcode_time.get("weekday_relevance") or ""
        best_positive_weekday_multiplier = float(outcode_time.get("weekday_multiplier") or 0.0)

    red_signal_ok, red_gate_reason, red_age_days = _positive_time_bucket_gate(
        best_positive_score,
        best_positive_samples,
        best_positive_confidence,
        best_positive_last_seen,
        now_dt,
        DB_RED_TIME_SCORE_MIN,
        DB_RED_FRESH_MIN_SAMPLES,
    )

    exact_red_candidate = exact_total >= TRAP_EXACT_RED_MIN
    nearby_red_candidate = nearby_total >= TRAP_NEARBY_RED_MIN or (exact_total + nearby_total) >= TRAP_NEARBY_RED_MIN
    red_confirmed = (
        _postcode_quality_rank(dropoff_quality) >= _postcode_quality_rank("sector")
        and
        red_signal_ok
        and best_positive_days >= DB_RED_MIN_DISTINCT_DAYS
        and (exact_red_candidate or nearby_red_candidate)
    )
    if red_confirmed:
        verdict = _traffic_verdict_payload(
            "RED",
            label,
            "dropoff",
            "beacon_db_red_confirmed gate=%s days=%s exact=%s nearby=%s" % (
                red_gate_reason,
                best_positive_days,
                exact_total,
                nearby_total,
            ),
            current_time_bucket,
        )
        verdict["source"] = "beacon_db"
        verdict["exact_total"] = exact_total
        verdict["nearby_total"] = nearby_total
        verdict["nearby_labels"] = nearby_labels
        verdict["db_total_entries"] = total_entries
        verdict["time_bucket_score"] = best_positive_score
        verdict["time_bucket_samples"] = best_positive_samples
        verdict["time_bucket_confidence"] = best_positive_confidence
        verdict["time_bucket_last_seen"] = best_positive_last_seen
        verdict["time_bucket_age_days"] = round(red_age_days or 0.0, 2)
        verdict["time_bucket_gate"] = red_gate_reason
        verdict["time_bucket_matches"] = best_positive_match
        verdict["time_bucket_distinct_days"] = best_positive_days
        verdict["time_bucket_day_keys"] = best_positive_day_keys
        verdict["time_bucket_same_weekday_days"] = best_positive_same_weekday_days
        verdict["time_bucket_same_weekpart_days"] = best_positive_same_weekpart_days
        verdict["time_bucket_weekday_relevance"] = best_positive_weekday_relevance
        verdict["time_bucket_weekday_multiplier"] = round(best_positive_weekday_multiplier, 2)
        return verdict

    if exact_total >= TRAP_EXACT_AMBER_MIN or nearby_total >= TRAP_NEARBY_AMBER_MIN or best_positive_score > 0:
        verdict = _traffic_verdict_payload(
            "AMBER",
            label,
            "dropoff",
            "beacon_db_amber exact=%s nearby=%s days=%s gate=%s" % (
                exact_total,
                nearby_total,
                best_positive_days,
                red_gate_reason,
            ),
            current_time_bucket,
        )
        verdict["source"] = "beacon_db"
        verdict["exact_total"] = exact_total
        verdict["nearby_total"] = nearby_total
        verdict["nearby_labels"] = nearby_labels
        verdict["db_total_entries"] = total_entries
        verdict["time_bucket_score"] = best_positive_score
        verdict["time_bucket_samples"] = best_positive_samples
        verdict["time_bucket_confidence"] = best_positive_confidence
        verdict["time_bucket_last_seen"] = best_positive_last_seen
        verdict["time_bucket_age_days"] = round(red_age_days or 0.0, 2)
        verdict["time_bucket_gate"] = red_gate_reason
        verdict["time_bucket_matches"] = best_positive_match
        verdict["time_bucket_distinct_days"] = best_positive_days
        verdict["time_bucket_day_keys"] = best_positive_day_keys
        verdict["time_bucket_same_weekday_days"] = best_positive_same_weekday_days
        verdict["time_bucket_same_weekpart_days"] = best_positive_same_weekpart_days
        verdict["time_bucket_weekday_relevance"] = best_positive_weekday_relevance
        verdict["time_bucket_weekday_multiplier"] = round(best_positive_weekday_multiplier, 2)
        return verdict

    return None


def _zone_matches_rule(address_text, outcode, rule):
    lowered = ("%s" % (address_text or "")).lower()
    normalized_outcode = ("%s" % (outcode or "")).upper()
    if any(keyword in lowered for keyword in rule.get("keywords", [])):
        return True
    for candidate in rule.get("outcodes", []):
        candidate = ("%s" % (candidate or "")).upper()
        if not candidate:
            continue
        if normalized_outcode == candidate or normalized_outcode.startswith(candidate):
            return True
    return False


def _traffic_time_bucket(now_dt):
    hour = now_dt.hour
    minute = now_dt.minute
    mins = hour * 60 + minute
    weekday = now_dt.weekday() < 5
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


def _traffic_verdict_payload(status, label, scope, reason, time_bucket):
    emoji_map = {
        "GREEN": "\U0001f7e2",
        "AMBER": "\U0001f7e0",
        "NEUTRAL": "\u26aa",
        "RED": "\U0001f534",
    }
    return {
        "emoji": emoji_map.get(status, "\u26aa"),
        "label": label,
        "scope": scope,
        "status": status,
        "reason": reason,
        "time_bucket": time_bucket,
    }


def _route_line_override_verdict(parsed, route_line_shadow, now_dt=None):
    now_dt = now_dt or datetime.datetime.now()
    shadow = route_line_shadow if isinstance(route_line_shadow, dict) else {}
    if not shadow or not shadow.get("matched"):
        return None

    trap_score = float(shadow.get("trap_score") or 0.0)
    exact_hits = int(shadow.get("exact_hits") or 0)
    near_hits = int(shadow.get("near_hits") or 0)
    strong_time_hits = int(shadow.get("strong_time_hits") or 0)
    top_outcodes = shadow.get("top_outcodes") or []
    top_sectors = shadow.get("top_sectors") or []
    label = ""
    if top_outcodes:
        label = "%s route" % top_outcodes[0]
    elif top_sectors:
        label = "%s route" % top_sectors[0]
    else:
        label = "Route trap"

    reason = "route_line score=%.2f exact=%s near=%s time=%s" % (
        trap_score,
        exact_hits,
        near_hits,
        strong_time_hits,
    )
    time_bucket = _traffic_time_bucket(now_dt)

    if trap_score >= ROUTE_LINE_RED_SCORE_MIN or (exact_hits >= 2 and strong_time_hits >= 1):
        verdict = _traffic_verdict_payload("RED", label, "route", reason, time_bucket)
        verdict["source"] = "route_line_shadow"
        verdict["route_line_shadow"] = shadow
        return verdict

    if trap_score >= ROUTE_LINE_AMBER_SCORE_MIN or exact_hits >= 1 or (exact_hits + near_hits) >= 3:
        verdict = _traffic_verdict_payload("AMBER", label, "route", reason, time_bucket)
        verdict["source"] = "route_line_shadow"
        verdict["route_line_shadow"] = shadow
        return verdict

    return None


def _route_line_audit_summary(route_line_shadow, traffic_verdict=None):
    shadow = route_line_shadow if isinstance(route_line_shadow, dict) else {}
    verdict = traffic_verdict if isinstance(traffic_verdict, dict) else {}
    matched_fine_buckets = shadow.get("matched_fine_buckets") or []
    adjacent_fine_buckets = shadow.get("adjacent_fine_buckets") or []
    final_source = ("%s" % (verdict.get("source") or "")).strip().lower()
    final_scope = ("%s" % (verdict.get("scope") or "")).strip().lower()
    return {
        "enabled": bool(shadow.get("enabled")),
        "matched": bool(shadow.get("matched")),
        "trap_score": round(float(shadow.get("trap_score") or 0.0), 2),
        "display_score": int(max(0, round(float(shadow.get("trap_score") or 0.0)))),
        "status_hint": shadow.get("status_hint") or "none",
        "exact_hits": int(shadow.get("exact_hits") or 0),
        "near_hits": int(shadow.get("near_hits") or 0),
        "time_bucket_hits": int(shadow.get("time_bucket_hits") or 0),
        "strong_time_hits": int(shadow.get("strong_time_hits") or 0),
        "unique_outcodes": int(shadow.get("unique_outcodes") or 0),
        "unique_sectors": int(shadow.get("unique_sectors") or 0),
        "top_outcodes": list(shadow.get("top_outcodes") or []),
        "top_sectors": list(shadow.get("top_sectors") or []),
        "closest_hit_m": round(float(shadow.get("closest_hit_m") or 0.0), 1),
        "same_weekday_days": int(shadow.get("same_weekday_days") or 0),
        "same_weekpart_days": int(shadow.get("same_weekpart_days") or 0),
        "weekday_relevance": shadow.get("weekday_relevance") or "",
        "weekday_multiplier": round(float(shadow.get("weekday_multiplier") or 0.0), 2),
        "matched_fine_bucket_count": len(matched_fine_buckets),
        "adjacent_fine_bucket_count": len(adjacent_fine_buckets),
        "final_route_override": final_source == "route_line_shadow" or final_scope == "route",
    }


def _compact_route_score_label(route_line_shadow):
    shadow = route_line_shadow if isinstance(route_line_shadow, dict) else {}
    display_score = int(max(0, round(float(shadow.get("trap_score") or 0.0))))
    return "R%s" % display_score


def _compact_route_beacon_count(route_line_shadow):
    shadow = route_line_shadow if isinstance(route_line_shadow, dict) else {}
    exact_hits = int(shadow.get("exact_hits") or 0)
    near_hits = int(shadow.get("near_hits") or 0)
    return max(0, exact_hits + near_hits)


def _compact_traffic_notification_token(traffic_verdict, route_line_shadow):
    verdict = traffic_verdict if isinstance(traffic_verdict, dict) else {}
    beacon_count = _compact_route_beacon_count(route_line_shadow)
    return "%s B%s" % (
        verdict.get("emoji") or "\u26aa",
        beacon_count,
    )


def _merge_route_line_verdict(base_verdict, route_verdict):
    if not route_verdict:
        return base_verdict
    if not base_verdict:
        return route_verdict
    rank = {"GREEN": 1, "NEUTRAL": 2, "AMBER": 3, "RED": 4}
    base_rank = rank.get(("%s" % (base_verdict.get("status") or "")).upper(), 0)
    route_rank = rank.get(("%s" % (route_verdict.get("status") or "")).upper(), 0)
    return route_verdict if route_rank > base_rank else base_verdict


def _compact_traffic_title_label(parsed, traffic_verdict):
    label = ("%s" % ((traffic_verdict or {}).get("label") or "")).strip()
    scope = ("%s" % ((traffic_verdict or {}).get("scope") or "")).strip().lower()

    pickup_sector = ("%s" % ((parsed or {}).get("pickup_sector") or "")).strip().upper()
    dropoff_sector = ("%s" % ((parsed or {}).get("dropoff_sector") or "")).strip().upper()
    pickup_outcode = ("%s" % ((parsed or {}).get("pickup_outcode") or "")).strip().upper()
    dropoff_outcode = ("%s" % ((parsed or {}).get("dropoff_outcode") or "")).strip().upper()

    if len(label) <= 8:
        return label or "Zone"

    if scope == "dropoff":
        if dropoff_sector:
            return dropoff_sector
        if dropoff_outcode:
            return dropoff_outcode
    if scope == "pickup":
        if pickup_sector:
            return pickup_sector
        if pickup_outcode:
            return pickup_outcode

    if dropoff_outcode:
        return dropoff_outcode
    if pickup_outcode:
        return pickup_outcode

    if not label:
        return "Zone"
    compact = re.sub(r"\s+", " ", label)
    return compact[:8].rstrip(" ,.;-") or "Zone"


def _postcode_quality_rank(value):
    ranks = {
        "none": 0,
        "outcode": 1,
        "sector": 2,
        "full": 3,
    }
    return ranks.get(("%s" % (value or "")).lower(), 0)


def _postcode_quality(parsed, prefix):
    explicit = ("%s" % ((parsed or {}).get("%s_postcode_quality" % prefix) or "")).strip().lower()
    if explicit:
        return explicit
    postcode = ("%s" % ((parsed or {}).get("%s_postcode" % prefix) or "")).strip()
    sector = ("%s" % ((parsed or {}).get("%s_sector" % prefix) or "")).strip()
    outcode = ("%s" % ((parsed or {}).get("%s_outcode" % prefix) or "")).strip()
    if postcode:
        return "full"
    if sector:
        return "sector"
    if outcode:
        return "outcode"
    return "none"


def _is_green_outcode(outcode):
    normalized = ("%s" % (outcode or "")).upper()
    return any(normalized.startswith(prefix) for prefix in GREEN_OUTCODE_PREFIXES)


def _is_amber_outcode(outcode):
    normalized = ("%s" % (outcode or "")).upper()
    return any(normalized.startswith(prefix) for prefix in AMBER_OUTCODE_PREFIXES)


def _is_red_family_outcode(outcode):
    normalized = ("%s" % (outcode or "")).upper()
    if normalized in AVOID_EXACT_EXCEPTIONS:
        return False
    return any(normalized.startswith(prefix) for prefix in AVOID_OUTCODE_FAMILIES)


def _match_central_edge_zone(address_text, outcode):
    for rule in CENTRAL_EDGE_RULES:
        if _zone_matches_rule(address_text, outcode, rule):
            return rule["name"]
    return ""


def _traffic_scope_verdict(scope, address_text, outcode, time_bucket, postcode_quality="none"):
    zone_name = _match_central_edge_zone(address_text, outcode)
    outcode_is_trusted = _postcode_quality_rank(postcode_quality) >= _postcode_quality_rank("sector")

    if scope == "dropoff":
        if outcode_is_trusted and _is_red_family_outcode(outcode):
            verdict = _traffic_verdict_payload("RED", outcode or "Avoid", scope, "north_or_east_pull", time_bucket)
            verdict["source"] = "hardcoded"
            return verdict
        if outcode_is_trusted and _is_amber_outcode(outcode):
            label = zone_name or outcode or "Amber Edge"
            verdict = _traffic_verdict_payload("AMBER", label, scope, "dropoff_risk_priority", time_bucket)
            verdict["source"] = "hardcoded"
            return verdict
        if zone_name:
            if time_bucket in ("pm_shoulder", "weekend_busy", "midday", "am_peak"):
                verdict = _traffic_verdict_payload("RED", zone_name, scope, "central_edge_busy", time_bucket)
                verdict["source"] = "hardcoded"
                return verdict
            verdict = _traffic_verdict_payload("AMBER", zone_name, scope, "central_edge_dropoff_caution", time_bucket)
            verdict["source"] = "hardcoded"
            return verdict
        return None

    if zone_name:
        if time_bucket in ("early_morning", "evening", "weekend_evening"):
            verdict = _traffic_verdict_payload("AMBER", zone_name, scope, "central_edge_caution", time_bucket)
            verdict["source"] = "hardcoded"
            return verdict
        verdict = _traffic_verdict_payload("AMBER", zone_name, scope, "pickup_central_caution", time_bucket)
        verdict["source"] = "hardcoded"
        return verdict

    if outcode_is_trusted and _is_amber_outcode(outcode):
        verdict = _traffic_verdict_payload("AMBER", outcode or "Amber Edge", scope, "amber_edge_caution", time_bucket)
        verdict["source"] = "hardcoded"
        return verdict

    if outcode_is_trusted and _is_red_family_outcode(outcode):
        verdict = _traffic_verdict_payload("AMBER", outcode or "Amber Edge", scope, "pickup_origin_caution", time_bucket)
        verdict["source"] = "hardcoded"
        return verdict

    return None


def _traffic_zone_verdict(parsed, now_dt=None, route_line_shadow=None):
    now_dt = now_dt or datetime.datetime.now()
    time_bucket = _traffic_time_bucket(now_dt)
    dropoff_address = ("%s" % (parsed.get("dropoff_address") or "")).strip()
    dropoff_outcode = ("%s" % (parsed.get("dropoff_outcode") or "")).strip()
    dropoff_quality = _postcode_quality(parsed, "dropoff")
    pickup_address = ("%s" % (parsed.get("pickup_address") or "")).strip()
    pickup_quality = _postcode_quality(parsed, "pickup")
    route_verdict = _route_line_override_verdict(parsed, route_line_shadow, now_dt)
    db_verdict = _traffic_db_verdict(parsed, now_dt)
    if db_verdict:
        return _merge_route_line_verdict(db_verdict, route_verdict)
    dropoff_verdict = _traffic_scope_verdict(
        "dropoff",
        dropoff_address,
        dropoff_outcode,
        time_bucket,
        dropoff_quality,
    )
    if dropoff_verdict:
        return _merge_route_line_verdict(dropoff_verdict, route_verdict)
    if dropoff_address and not dropoff_outcode and dropoff_address != pickup_address:
        verdict = _traffic_verdict_payload("NEUTRAL", "Dropoff ?", "dropoff", "dropoff_text_without_postcode", time_bucket)
        verdict["source"] = "hardcoded"
        return _merge_route_line_verdict(verdict, route_verdict)

    pickup_verdict = _traffic_scope_verdict(
        "pickup",
        pickup_address,
        parsed.get("pickup_outcode") or "",
        time_bucket,
        pickup_quality,
    )
    if pickup_verdict:
        return _merge_route_line_verdict(pickup_verdict, route_verdict)

    verdict = _traffic_verdict_payload("NEUTRAL", "Neutral", "", "no_strong_match", time_bucket)
    verdict["source"] = "hardcoded"
    return _merge_route_line_verdict(verdict, route_verdict)


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


def _totals_after_append(totals_before_append, ledger_record):
    return {
        "trip_count": int(totals_before_append.get("trip_count") or 0) + 1,
        "total_price": round(
            float(totals_before_append.get("total_price") or 0.0)
            + float(ledger_record.get("price") or 0.0),
            2,
        ),
        "drive_minutes": int(
            round(
                float(totals_before_append.get("drive_minutes") or 0.0)
                + float(ledger_record.get("pickup_min") or 0.0)
                + float(ledger_record.get("trip_min") or 0.0)
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
        prices = re.findall(r"ðŸ’°\s*Uber Price:\s*Â£\s*([\d.]+)", scope)
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
            for match in re.finditer(r"^â±\s*Pickup Estimate:\s*(\d+)\s*min\b", scope, re.MULTILINE)
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


def _looks_like_self_notification_capture(text):
    lowered = ("%s" % (text or "")).lower()
    has_own_banner = any(
        token in lowered
        for token in [
            "triplogger parse alert",
            "ocr ran, but required trip fields were missing",
            "real price",
            "rsp1",
            "decline below",
        ]
    )
    has_vehicle = any(
        token in lowered
        for token in [
            "comfort",
            "electric",
            "uberx",
            "uberxl",
            "business comfort",
            "uber exec",
            "green",
            "pet",
            "assist",
        ]
    )
    has_trip_pair = bool(
        re.search(r"\b\d+(?:[.,]\d+)?\s*mins?\s*\(\s*\d+(?:[.,]\d+)?\s*(?:mi|miles?|ml)\s*\)", lowered)
    )
    return has_own_banner and not (has_vehicle and has_trip_pair)


def _read_shortcut_offer_text():
    if clipboard is None:
        return ""
    try:
        raw = clipboard.get()
    except Exception:
        return ""
    text = "%s" % (raw or "")
    text = text.strip()
    if len(text) < 12:
        return ""
    if not re.search("[£$€]\\s*\\d", text):
        return ""
    return text


def _looks_like_direct_text_payload(text):
    value = ("%s" % (text or "")).strip()
    if len(value) < 20:
        return False
    lowered = value.lower()
    return (
        bool(re.search("[£$€]\\s*\\d", value))
        or " mins" in lowered
        or " min " in lowered
        or " mi" in lowered
        or "miles" in lowered
        or "holiday pay" in lowered
        or "holiday entitlement" in lowered
        or "electric" in lowered
        or "comfort" in lowered
        or "uberx" in lowered
        or "match" in lowered
        or "confirm" in lowered
    )


def _consume_shortcut_offer_text_argv():
    plain_text_items = []
    for arg in sys.argv[1:]:
        candidate = "%s" % (arg or "")
        if not candidate.strip():
            continue
        if os.path.exists(candidate):
            continue
        plain_text_items.append(candidate)
    joined_text = "\n".join(plain_text_items).strip()
    if not _looks_like_direct_text_payload(joined_text):
        return None
    return {
        "text": joined_text,
        "path": "",
        "tag": "ARGV",
        "bytes": len(joined_text.encode("utf-8", errors="ignore")),
        "exists": True,
        "looks_like_offer": True,
        "arg_count": len(plain_text_items),
    }


def _is_reliable_rating_source(debug):
    source = ("%s" % (debug.get("rating_source") or "")).strip().lower()
    if source in ("contextual_match", "star_match"):
        return True
    if source == "compact_numeric":
        line = "%s" % (debug.get("rating_line") or "")
        return bool(
            re.search(r"[<>*â˜…]", line)
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
    compare_rate = baseline_target_per_min
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
    traffic_verdict = _traffic_zone_verdict(parsed)
    target_delta_line = "Target Delta: --"
    if target_insight and target_insight.get("enabled"):
        target_delta_line = "Target Delta: %s" % _format_signed_pounds_per_minute(
            target_insight.get("delta_per_min_gbp") or 0.0
        ).replace("/min", "/m")
    ccz_line = "CCZ Bonus Applied: %s" % ("YES (+Â£%.2f)" % CCZ_BONUS_GBP if metrics["ccz_bonus_applied"] else "NO")
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
        "Pickup Postcode: %s | Outcode: %s | Sector: %s"
        % (
            parsed["pickup_postcode"] or "Unknown",
            parsed["pickup_outcode"] or "Unknown",
            parsed["pickup_sector"] or "Unknown",
        ),
        "Dropoff Postcode: %s | Outcode: %s | Sector: %s"
        % (
            parsed["dropoff_postcode"] or "Unknown",
            parsed["dropoff_outcode"] or "Unknown",
            parsed["dropoff_sector"] or "Unknown",
        ),
        "Traffic Zone: %s %s | %s | %s"
        % (
            traffic_verdict["emoji"],
            traffic_verdict["label"],
            traffic_verdict["status"],
            traffic_verdict["reason"],
        ),
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
    global RUNTIME_STDOUT_ENABLED
    state = _load_state()
    shortcut_offer_text, shortcut_input_mode, shortcut_source = _read_shortcut_offer_input()
    RUNTIME_STDOUT_ENABLED = shortcut_input_mode != "argv"
    _runtime_print("[T0] Entered Pythonista at %s | build=%s" % (time.strftime("%H:%M:%S"), SCRIPT_BUILD))
    latest_asset = None
    selected_asset_id = None
    selected_asset_created = None

    fetch_started = time.perf_counter()
    preselected_ocr_bundle = None
    preselected_score = None
    cgimage = None
    fetch_finished = fetch_started
    convert_finished = fetch_started

    if shortcut_offer_text:
        if shortcut_input_mode == "argv":
            _runtime_print(
                "[input] Using Shortcut-extracted text from arguments (%s, %s bytes)."
                % (
                    shortcut_source.get("tag") or "ARGV",
                    shortcut_source.get("bytes") or len(shortcut_offer_text),
                )
            )
        elif shortcut_input_mode == "file":
            _runtime_print(
                "[input] Using Shortcut-extracted text from file (%s, %s bytes)."
                % (
                    shortcut_source.get("tag") or "FILE",
                    shortcut_source.get("bytes") or len(shortcut_offer_text),
                )
            )
        else:
            _runtime_print("[input] Using Shortcut-extracted text from fallback input.")
        try:
            _write_text(DEBUG_SHORTCUT_DUMP_PATH, shortcut_offer_text)
        except Exception:
            pass
        fetch_finished = time.perf_counter()
        convert_finished = fetch_finished
    else:
        _wait_for_fresh_latest_asset(state, poll_interval_s=0.08, timeout_s=3.0)
        latest_asset, preselected_ocr_bundle, preselected_score = _select_best_recent_offer_asset(state)
        fetch_finished = time.perf_counter()

        if latest_asset is None:
            _runtime_print("[guard] Aborting. Photo guard timed out (no new photo registered).")
            _send_push_notification(
                "TripLogger Alert %s" % SCRIPT_BUILD_TAG,
                "No Shortcut text file and no usable new image were available. Try the scan again.",
            )
            raise SystemExit(0)

        ui_image = latest_asset.get_ui_image()
        objc_image = ObjCInstance(ui_image)
        cgimage = objc_image.CGImage()
        convert_finished = time.perf_counter()
        selected_asset_id = getattr(latest_asset, "local_id", None)
        selected_asset_created = _created_str(getattr(latest_asset, "creation_date", None))

    ocr_text = ""
    ocr_time = 0.0
    parse_result = None
    if shortcut_offer_text:
        ocr_text = shortcut_offer_text
        parse_result = parse_ocr_text(ocr_text)
    else:
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
    if parse_result and parse_result["valid"] and shortcut_offer_text:
        _runtime_print("[input] Parsed Shortcut text successfully.")
    elif parse_result and parse_result["valid"]:
        _runtime_print("[input] Parsed selected photo asset successfully.")
    if not shortcut_offer_text:
        selected_asset_id = getattr(latest_asset, "local_id", None) if latest_asset else None
        selected_asset_created = _created_str(getattr(latest_asset, "creation_date", None)) if latest_asset else None

    if not parse_result or not parse_result["valid"]:
        if _looks_like_navigation_map(ocr_text):
            _runtime_print("[guard] Active navigation map detected. Exiting silently.")
            raise SystemExit(0)

        if shortcut_offer_text and _looks_like_self_notification_capture(ocr_text):
            _runtime_print("[guard] Captured TripLogger notification text instead of an offer; exiting silently.")
            latest_payload = {
                "ok": False,
                "reason": "self_notification_capture",
                "ocr_text": ocr_text,
                "ocr_seconds": round(ocr_time, 4),
                "asset_offer_score": preselected_score,
            }
            _write_json(LATEST_JSON_PATH, latest_payload)
            raise SystemExit(0)

        parse_reason = parse_result["parseError"] if parse_result else "parse_failed"
        ocr_preview = _compact_ocr_preview(ocr_text, 110) or "no OCR text"
        latest_payload = {
            "ok": False,
            "reason": parse_reason,
            "ocr_text": ocr_text,
            "ocr_seconds": round(ocr_time, 4),
            "asset_offer_score": preselected_score,
            "shortcut_source": shortcut_source,
        }
        _write_json(LATEST_JSON_PATH, latest_payload)
        shortcut_diag = "SRC %s %sB" % (
            shortcut_source.get("tag") or "PHOTO",
            shortcut_source.get("bytes") or 0,
        )
        if shortcut_source.get("path"):
            shortcut_diag += " | %s" % os.path.basename(shortcut_source.get("path") or "")
        if shortcut_source.get("invalid_reason"):
            shortcut_diag += " | %s" % shortcut_source.get("invalid_reason")
        _send_push_notification(
            "TripLogger Parse Alert %s %s"
            % (SCRIPT_BUILD_TAG, shortcut_source.get("tag") or "PHOTO"),
            "%s | %s | %s" % (shortcut_diag, parse_reason, ocr_preview),
        )
        raise SystemExit(0)

    _runtime_print("[Asset fetch time] %.3f seconds" % (fetch_finished - fetch_started))
    _runtime_print("[Image convert time] %.3f seconds" % (convert_finished - fetch_finished))
    _runtime_print("[OCR Scan Time] %.3f seconds" % ocr_time)

    ocr_sha1 = hashlib.sha1(ocr_text.encode("utf-8", errors="ignore")).hexdigest()
    previous_ocr_sha1 = state.get("last_ocr_sha1")
    if previous_ocr_sha1 and ocr_sha1 == previous_ocr_sha1:
        _runtime_print("[guard] Duplicate OCR text detected; skipping write/notify.")
        raise SystemExit(0)

    parsed = dict(parse_result["parsed"] or {})
    parsed["parse_error"] = parse_result.get("parseError")
    debug = parse_result.get("debug") or {}
    metrics = _derive_offer_metrics(parsed)
    now = datetime.datetime.now()
    traffic_verdict = _traffic_zone_verdict(parsed, now)
    route_shadow = _route_shadow_snapshot(parsed, now)
    low_rating_decision = _low_rating_decision(parsed, debug)

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
        traffic_label_compact = _compact_traffic_title_label(parsed, traffic_verdict)
        traffic_compact = "%s %s" % (traffic_verdict["emoji"], traffic_label_compact)
        title_line = "\u2b50 %.2f | \U0001f4b0 \u00a3%.2f | %s \u00b7 %s" % (
            parsed["rating"] if parsed["rating"] else 0.0,
            parsed["price"],
            traffic_compact,
            shortcut_source.get("tag") or "PHOTO",
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
        body_lines = [body_line1, body_line2]
        route_direction_summary = ("%s" % (route_shadow.get("direction_summary") or "")).strip()
        if route_direction_summary:
            body_lines.append("Route Shadow %s" % route_direction_summary)
        body_text = "\n".join(body_lines)
    _send_push_notification(title_line, body_text)

    route_line_shadow = _route_line_shadow_snapshot(parsed, now)
    traffic_verdict = _traffic_zone_verdict(parsed, now, route_line_shadow)
    route_line_audit = _route_line_audit_summary(route_line_shadow, traffic_verdict)
    today_date = now.strftime("%Y-%m-%d")
    now_str = now.strftime("%Y-%m-%d %H:%M:%S")

    totals_before_append = _get_today_totals_cached(state, LEDGER_PATH, today_date)
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
        "pickup_postcode": parsed["pickup_postcode"],
        "dropoff_postcode": parsed["dropoff_postcode"],
        "pickup_outcode": parsed["pickup_outcode"],
        "dropoff_outcode": parsed["dropoff_outcode"],
        "pickup_sector": parsed["pickup_sector"],
        "dropoff_sector": parsed["dropoff_sector"],
        "pickup_postcode_quality": parsed.get("pickup_postcode_quality") or "",
        "dropoff_postcode_quality": parsed.get("dropoff_postcode_quality") or "",
        "traffic_zone_status": traffic_verdict["status"],
        "traffic_zone_label": traffic_verdict["label"],
        "traffic_zone_scope": traffic_verdict["scope"],
        "traffic_zone_reason": traffic_verdict["reason"],
        "traffic_zone_time_bucket": traffic_verdict["time_bucket"],
        "route_shadow": route_shadow,
        "route_line_audit": route_line_audit,
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
    if USE_SUMMARY_TARGET_FILES:
        summary_total = _today_summary_total_from_triplog(today_date)
        summary_drive_minutes = _today_summary_drive_minutes_from_triplog(today_date)
    else:
        summary_total = None
        summary_drive_minutes = None
    target_total_gbp = summary_total if summary_total is not None else totals_before_append["total_price"]
    target_drive_minutes = summary_drive_minutes if summary_drive_minutes is not None else totals_before_append["drive_minutes"]
    target_insight = _build_local_target_insight(target_total_gbp, target_drive_minutes, metrics["per_min_adj"])
    active_offer_payload = _write_active_offer(
        parsed,
        metrics,
        traffic_verdict,
        route_shadow,
        route_line_audit,
        shortcut_source,
        now_str,
        ocr_sha1,
    )

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

    _append_text(TEXT_LOG_PATH, block)

    _append_jsonl(LEDGER_PATH, ledger_record)
    totals_after_append = _totals_after_append(totals_before_append, ledger_record)

    latest_payload = {
        "ok": True,
        "timestamp": now_str,
        "selected_asset_id": selected_asset_id,
        "selected_asset_created": selected_asset_created,
        "ocr_seconds": round(ocr_time, 4),
        "ocr_sha1": ocr_sha1,
        "ocr_text": ocr_text,
        "input_mode": "shortcut_text" if shortcut_offer_text else "photo_asset",
        "shortcut_input_mode": shortcut_input_mode if shortcut_offer_text else "",
        "shortcut_source": shortcut_source,
        "parse": parse_result,
        "metrics": metrics,
        "ledger_record": ledger_record,
        "today_totals_before_offer": totals_before_append,
        "today_totals": totals_after_append,
        "target_progress_local": target_insight,
        "traffic_verdict": traffic_verdict,
        "route_shadow": route_shadow,
        "route_line_audit": route_line_audit,
        "route_line_shadow": route_line_shadow,
        "active_offer": active_offer_payload,
        "low_rating_decision": low_rating_decision,
    }
    _write_json(LATEST_JSON_PATH, latest_payload)

    state_payload = dict(state or {})
    state_payload["last_ocr_sha1"] = ocr_sha1
    state_payload["today_totals_cache"] = {
        "date": today_date,
        "trip_count": totals_after_append["trip_count"],
        "total_price": totals_after_append["total_price"],
        "drive_minutes": totals_after_append["drive_minutes"],
    }
    if latest_asset is not None:
        state_payload["last_asset_id"] = getattr(latest_asset, "local_id", None)
        state_payload["last_created"] = _created_str(getattr(latest_asset, "creation_date", None))
    _save_state(state_payload)

    t_global_end = time.perf_counter()
    _runtime_print("[T1] Leaving Pythonista at %s (Exec time: %.3fs)" % (
        time.strftime("%H:%M:%S"),
        t_global_end - t_global_start,
    ))


def _looks_like_shortcut_offer_text(text):
    text = ("%s" % (text or "")).strip()
    if len(text) < 12:
        return False
    return bool(re.search("[£$€]\\s*\\d", text))


def _shortcut_source_tag(path):
    normalized = os.path.normpath(path or "")
    if normalized == os.path.normpath(SHORTCUT_INPUT_SCRIPT_DIR_PATH):
        return os.path.basename(os.path.normpath(SCRIPT_DIR)).upper() or "PYSCRIPT"
    if normalized == os.path.normpath(SHORTCUT_INPUT_SCRIPT_DIR_NESTED_PATH):
        return (os.path.basename(os.path.normpath(SCRIPT_DIR)).upper() or "PYSCRIPT") + "_NESTED"
    if normalized == os.path.normpath(SHORTCUT_INPUT_PATH):
        return "PYDOC"
    if normalized == os.path.normpath(SHORTCUT_INPUT_FALLBACK_PATH):
        return "PYROOT"
    return "FILE"


def _shortcut_input_candidates():
    ordered = []
    seen = set()
    for path in (
        SHORTCUT_INPUT_SCRIPT_DIR_PATH,
        SHORTCUT_INPUT_SCRIPT_DIR_NESTED_PATH,
        SHORTCUT_INPUT_PATH,
        SHORTCUT_INPUT_FALLBACK_PATH,
    ):
        normalized = os.path.normpath(path)
        if normalized in seen:
            continue
        seen.add(normalized)
        ordered.append(path)
    return ordered


def _consume_shortcut_offer_text_file():
    deadline = time.perf_counter() + SHORTCUT_INPUT_WAIT_SECONDS
    best_invalid_payload = None
    while True:
        try:
            for path in _shortcut_input_candidates():
                if not os.path.exists(path):
                    continue
                with open(path, "r", encoding="utf-8", errors="ignore") as handle:
                    text = handle.read().strip()
                payload = {
                    "text": text,
                    "path": path,
                    "tag": _shortcut_source_tag(path),
                    "bytes": len(text.encode("utf-8", errors="ignore")),
                    "exists": True,
                    "looks_like_offer": _looks_like_shortcut_offer_text(text),
                }
                if payload["bytes"] > 0 and best_invalid_payload is None:
                    best_invalid_payload = payload
                if not _looks_like_shortcut_offer_text(text):
                    continue
                try:
                    with open(path, "w", encoding="utf-8") as handle:
                        handle.write("")
                except Exception:
                    pass
                return payload
        except Exception:
            pass
        if time.perf_counter() >= deadline:
            if best_invalid_payload is not None:
                best_invalid_payload["invalid_reason"] = "content_rejected"
                return best_invalid_payload
            return {
                "text": "",
                "path": "",
                "tag": "PHOTO",
                "bytes": 0,
                "exists": False,
                "looks_like_offer": False,
                "invalid_reason": "missing_file",
                "checked_paths": _shortcut_input_candidates(),
            }
        time.sleep(SHORTCUT_INPUT_POLL_SECONDS)


def _read_shortcut_offer_input():
    argv_payload = _consume_shortcut_offer_text_argv()
    if argv_payload and argv_payload.get("text"):
        return argv_payload["text"], "argv", argv_payload
    file_payload = _consume_shortcut_offer_text_file()
    if file_payload and file_payload.get("text"):
        return file_payload["text"], "file", file_payload
    return "", "", (file_payload or {"tag": "PHOTO", "path": "", "bytes": 0})


if __name__ == "__main__":
    main()
