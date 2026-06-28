# iOS App Handoff

## Purpose

This file is the durable handoff for the GameforMonetize system and the future native iOS app. It explains:

- what exists today in Pythonista
- what the real product goal is
- what the target native app should do
- which parts are already proven
- which parts are still heuristic, shadow-mode, or aspirational

This is intended to be sufficient context for a future engineer or future Codex chat to continue the project without relying on conversation history.

## Product Goal

Build a fast iPhone-native driver decision app that evaluates Uber offers in near real time and eventually automates the decision flow as far as the platform allows.

The long-term target is:

- detect a new incoming offer
- extract trip details immediately
- compute economics, traffic risk, and route risk
- decide accept or decline from driver-defined rules
- optionally auto-act if technically and legally feasible on the target deployment path

The driver's real problem is not only destination risk. Many trips look acceptable on dropoff alone but are bad because the path toward the dropoff goes through persistent traffic corridors. The app must therefore evaluate:

- pickup zone
- dropoff zone
- route line trap density
- time-of-day traffic evidence
- personal operator overrides

## Current Live System

The live deployed workflow is Pythonista + iOS Shortcuts + GitHub self-update.

### 1. One-tap offer parser

Source of truth:
- `UberTripLoggerPostcodeIsolation.py`

Deployed phone name:
- `UberTripLogger.py`

What it does:
- receives OCR text from Shortcut arguments
- parses price, rating, pickup/trip minutes, pickup/trip miles
- isolates pickup and dropoff addresses
- extracts postcode, outcode, sector
- computes adjusted trip economics
- computes traffic verdict
- computes route-line shadow trap score
- schedules a local notification
- opens Uber again
- writes compact offer files and debug payloads

Important outputs:
- `active_offer.json`
- append-only offer history
- latest debug JSON
- trip ledger/log files

### 2. Two-tap traffic beacon logger

Source:
- `traffic_beacon.py`

What it does:
- captures GPS
- reverse geocodes to address/postcode
- saves beacon as traffic event
- rebuilds beacon DB
- rebuilds route-support structures

Current DB concepts:
- outcode counts
- sector counts
- family counts
- time buckets
- 15-minute windows
- route-point raw beacon geometry
- line-grid cells

### 3. Long-press updater

Source:
- `update_from_github.py`

Related uploader:
- `upload_data_to_private_github.py`

What it does:
- updates deployed files from GitHub
- updates itself
- can defer heavy upload based on power/thermal state
- syncs operational data to private GitHub

## What Is Already Proven

The following ideas are no longer theoretical:

- OCR-based live offer parsing on iPhone
- postcode/outcode/sector extraction from noisy OCR
- fast notification-based trip scoring
- local beacon logging from GPS
- traffic evidence grouped by area and time
- self-updating phone scripts from GitHub
- private data sync for offline analysis
- route-line shadow scoring using beacon geometry

These are important because the native app should reuse the same product logic, not restart from zero.

## Core Product Insight

The system should think like this:

1. An offer is not judged only by fare.
2. A destination is not judged only by postcode family.
3. The path to the job matters as much as the endpoint.
4. Repeated driver-observed traffic beacons are more useful than generic assumptions.
5. Operator truth matters and should override weak model evidence.

Examples:

- `Parkhurst Road / Holloway Road` is treated as a real trap because the operator explicitly confirmed it from experience.
- A route may land in a neutral area but still be bad if the corridor crosses multiple known trap beacons.
- One beacon can be operationally important even before the database becomes statistically large.

## Current Traffic Logic Model

The live logic blends four sources:

### Hardcoded area rules

Examples:
- north/east pull as red families
- central-edge zones such as City, London Bridge, Westminster
- operator-specific blacklisted roads

### Beacon DB verdict

The system uses stored beacon evidence by:
- outcode
- sector
- time bucket
- fine 15-minute windows
- same weekday / same weekpart relevance

### Route-line shadow

The system draws a fat line from pickup to dropoff using local beacon geometry and computes:
- exact hits
- near hits
- time-aligned hits
- weighted trap score

This currently runs in shadow mode and is suitable for soft or hard route overrides.

### Operator overrides

These are explicit truths added because lived experience beats weak model confidence.

Current example:
- `Parkhurst Road / Holloway Road` hard red road trap

## Important Engineering Lessons

### Notification order is fragile

The one-tap notification path has regressed multiple times when logic was added before scheduling the notification.

The safest pattern is:

1. parse fast
2. compute minimum required verdict
3. schedule notification
4. reopen Uber
5. do heavier post-notification work

This should be preserved in all future Pythonista changes and in the native app where similar latency-sensitive UI feedback exists.

### OCR cleanup must be surgical

Broad postcode fixes can introduce regressions. Recent defensive fixes were added for:

- fake single-letter postcodes such as `C1 0CK`
- merged addresses containing two postcode fragments
- central OCR artifacts such as `WCH 7AG` -> `WC2H 7AG`

### Data structures matter more than raw file size

Raw beacon history can grow, but the app should score against compact structures:

- line grid
- route points
- per-day history shards
- aggregated outcode/sector windows

The live system is already moving in this direction.

## Native App Vision

The native iOS app should replace the Shortcut/Pythonista runtime with a real architecture:

- SwiftUI app shell
- local persistent store
- OCR / text extraction pipeline
- map/corridor engine
- beacon capture service
- offer classifier
- route risk engine
- driver preference engine
- accept/decline policy engine

### Target modules

- `OfferIngest`
- `OCRParser`
- `TripModel`
- `BeaconStore`
- `TrafficEvidenceEngine`
- `RouteCorridorEngine`
- `DecisionEngine`
- `NotificationPresenter`
- `MapReviewUI`
- `OperatorOverrides`

## Automation End-State

The full dream workflow is:

1. offer appears
2. app detects it automatically
3. text is extracted
4. parser builds structured trip
5. economics + traffic + route risk run
6. decision policy returns:
   - accept
   - decline
   - hold/manual
7. app acts or prompts accordingly

### Auto-beacon goal

The app should also learn passively:

- when driver is stationary in traffic
- where repeated congestion occurs
- at what time bucket
- on which corridor direction

### Auto-accept / auto-decline goal

This should exist as a policy layer, for example:

- decline if route trap score >= threshold
- decline if operator-blacklisted road is on route
- decline if pay below adjusted target floor
- decline if low rider rating and reliable extraction
- accept if pay strong and route clean

This logic should remain configurable.

## Reality Check On iOS Automation

A native App Store-safe app may not be able to fully control another app or auto-tap accept/decline in the way a private automation build could.

Therefore there are two tracks:

### Track A: App Store-safe decision app

- parses
- scores
- warns
- displays route traps
- helps decide quickly

### Track B: private / internal / advanced automation build

- tries to detect offer state continuously
- may use broader device/screen capabilities
- could drive closer to auto-action if technically possible

The codebase should be designed so the decision engine is shared regardless of which automation track is used.

## Data Assets That Matter Most

The most important long-term assets are:

- offer history
- accepted/completed trip history
- traffic beacon history
- line-grid/corridor structures
- operator override catalog
- route-level outcomes

These become the training and rules foundation for the real app.

## Recommended Native Build Priorities

### Phase 1

- port parser
- port verdict logic
- port route-line scoring
- port beacon DB loading
- local JSON/SQLite persistence
- manual review UI

### Phase 2

- live beacon capture
- route map visualization
- operator override editor
- trip history inspection

### Phase 3

- accepted-trip behavioral labeling
- route learning
- time-window confidence weighting
- smarter corridor risk scoring

### Phase 4

- optional automation layer
- auto accept / decline policy execution where feasible

## Non-Negotiable Product Principles

- speed first
- no notification regressions
- operator truth overrides weak model confidence
- route matters more than endpoint alone
- time bucket matters
- keep raw history, but score from compact indexes
- never destroy working behavior for speculative upgrades

## Files Most Relevant Right Now

- `UberTripLoggerPostcodeIsolation.py`
- `traffic_beacon.py`
- `update_from_github.py`
- `upload_data_to_private_github.py`
- `pythonista_update_manifest.json`
- `PYTHONISTA_PORTFOLIO.md`

## Summary

This project is already more than a script. It is an early mobile decision engine with real operational data, self-updating infrastructure, and a clear path toward a native iOS product.

The native app should not be framed as a fresh idea. It is the productization of a working field system whose core insights have already been validated on-road:

- parse the offer fast
- understand where it goes
- understand what it pays
- understand what traffic it crosses
- act before the driver loses the trip
