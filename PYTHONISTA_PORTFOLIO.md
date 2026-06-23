# Pythonista Dispatch Automation Portfolio

## Project Summary

This repository documents a real mobile decision-support system built for live Uber-driver use on iPhone using Pythonista, iOS Shortcuts, and GitHub-based self-updating scripts.

The system was built to reduce offer-evaluation latency while driving by converting OCR text from Uber offer cards into structured trip data, scoring the trip in real time, and showing an immediate push notification with:

- rider rating
- offer value
- traffic-risk verdict
- per-minute and per-mile economics

It also includes a separate traffic-beacon logger that records real-world traffic/no-traffic observations by postcode and time bucket, allowing the offer parser to evolve from static zone heuristics into evidence-backed traffic decisions.

## What This System Does

### 1. One-tap offer parser

Main runtime:
- `UberTripLoggerPostcodeIsolation.py`

Deployed on phone as:
- `UberTripLogger.py`

Workflow:
- iOS Shortcut takes screenshot
- Shortcut extracts text from image
- Shortcut runs Pythonista script with extracted text
- Pythonista parses trip card
- Push notification returns scored result immediately

Core features:
- OCR text parsing from Uber offer cards
- pickup/dropoff address extraction
- postcode, outcode, and sector isolation
- fare math and adjusted per-minute calculations
- CCZ bonus handling
- low-rating decline logic
- compact active-offer JSON output
- append-only offer history
- traffic-risk verdict in notification title

### 2. Two-tap traffic beacon logger

Runtime:
- `traffic_beacon.py`

Workflow:
- separate Shortcut runs a lightweight Pythonista location capture
- current GPS location is reverse-geocoded
- postcode/outcode/sector are extracted
- event is saved as either `traffic` or `no_traffic`
- beacon DB is rebuilt for later use by 1-tap scoring

Core features:
- GPS snapshot
- postcode extraction from reverse geocode
- time-bucket labeling
- outcode/sector/family aggregation
- confidence levels and sample counts
- route DB foundation for future corridor logic

### 3. Long-press self-updater

Runtime:
- `update_from_github.py`

Workflow:
- long-press Shortcut runs updater in Pythonista
- updater pulls raw files from GitHub
- updater overwrites local deployed files
- updater also updates itself

This removed the need for:
- manual copy/paste
- local HTML bridges
- same-network syncing

## Why This Is Valuable

This project is not a toy script. It is an operational mobile workflow system built around real constraints:

- iPhone-only environment
- no Mac requirement for normal updates
- live usage while driving
- very low tolerance for interaction friction
- constantly changing heuristics based on field observations

It demonstrates:

- product-minded automation design
- AI-assisted systems iteration
- real-world OCR/parser hardening
- mobile workflow engineering under platform limitations
- pragmatic deployment architecture
- operational logging and feedback-loop design

## Technical Design

### Offer pipeline

Input:
- screenshot text from iOS Shortcut

Processing:
- parser normalizes OCR noise
- identifies price, rating, pickup/trip minutes, pickup/trip miles
- isolates pickup and dropoff addresses
- extracts full postcode, outcode, and sector
- computes fare metrics
- applies traffic-risk verdict

Output:
- iOS push notification
- text log
- JSONL ledger
- latest offer JSON
- active offer JSON

### Traffic pipeline

Input:
- manual beacon event from shortcut

Processing:
- GPS snapshot
- reverse geocode
- postcode extraction
- time-bucket classification
- aggregate DB rebuild

Output:
- `TrafficBeacon-latest.json`
- `TrafficBeacon-history.json`
- `TrafficBeacon-db.json`
- `TrafficRoute-db.json`

### Traffic decision model

Current logic prioritizes:

1. dropoff risk
2. beacon DB verdicts
3. hardcoded red/amber fallback zones
4. pickup fallback only if dropoff is not decisive

Current beacon logic includes:
- same-time bucket green upgrades
- recency gating
- confidence thresholds
- sample-count thresholds
- red/amber balancing so stale trap history does not dominate forever

## Current Important Files

### Main maintained files

- `UberTripLoggerPostcodeIsolation.py`
- `traffic_beacon.py`
- `update_from_github.py`

### Legacy/original file kept for reference

- `UberTripLogger.py`

This file is preserved as the older/original branch. The maintained production logic now lives in:
- `UberTripLoggerPostcodeIsolation.py`

### Current deployed version markers

At the time of writing:
- `UberTripLoggerPostcodeIsolation.py`: `2026-06-23-postcode-isolation-trapdb-v10`
- `traffic_beacon.py`: `2026-06-23-traffic-beacon-db-v4`
- `update_from_github.py`: `2026-06-23-updater-selfupdate-v2`

## Shortcut Architecture

### 1-tap shortcut

Purpose:
- parse current Uber offer and notify instantly

High-level steps:
1. take screenshot
2. extract text from screenshot
3. run `UberTripLogger.py` in Pythonista with extracted text
4. open Uber app again if needed

### 2-tap shortcut

Purpose:
- save a traffic beacon at current location

High-level steps:
1. run `traffic_beacon.py` in Pythonista

### Long-press shortcut

Purpose:
- force-update deployed Pythonista files from GitHub

High-level steps:
1. run `update_from_github.py` in Pythonista

## CV-Friendly Framing

Suggested description:

Built an iPhone-native dispatch automation system using Pythonista, iOS Shortcuts, and GitHub-based self-updating scripts to parse Uber offer cards in real time, extract postcodes and trip metrics, classify traffic risk using live beacon evidence, and return immediate decision notifications for in-vehicle operational use.

Short resume bullets:

- Built a mobile OCR-driven trip scoring workflow for live Uber offer evaluation on iPhone.
- Designed postcode/outcode/sector extraction and fare-scoring logic for real-time push decisions.
- Implemented a traffic-beacon database using GPS snapshots, reverse geocoding, time buckets, and confidence scoring.
- Created a GitHub-powered self-updating deployment flow for Pythonista scripts without manual file sync.
- Iterated the system as an operational product under real driving and platform constraints.

## What Future Chats Should Know

If this repo is used as context in a future Codex chat, the key facts are:

- active 1-tap production logic lives in `UberTripLoggerPostcodeIsolation.py`
- local deployed phone filename is still `UberTripLogger.py`
- `traffic_beacon.py` is the separate manual traffic/no-traffic logger
- `update_from_github.py` is the long-press updater and it self-updates
- traffic DB is intended to grow into stronger time-aware and route-aware verdicts
- `active_offer.json` is the cleanest current offer artifact
- text trip logs are noisier than active-offer JSON and are not the best source of truth for current live state

## Next Planned Evolution

- stronger time-aware beacon scoring
- sector-first confidence weighting
- route/corridor evidence built from beacon paths
- compact traffic confidence fields in active-offer output
- cleaner portfolio packaging of screenshots, shortcut diagrams, and example outputs
