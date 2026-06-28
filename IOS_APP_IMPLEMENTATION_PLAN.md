# Native iOS App Plan

## Objective

Convert the live Pythonista Uber decision workflow into a native iPhone app with:

- fast offer ingestion
- local beacon intelligence
- route corridor trap scoring
- configurable decision logic
- future-ready automation hooks

This document is the build plan.

## High-Level Outcome

The finished native app should answer, in a few seconds or less:

- What is this trip worth?
- Where is it taking me?
- Does the route cross known traffic traps?
- Is this a likely accept or decline?

And eventually:

- accept automatically
- decline automatically

where platform access and deployment model allow it.

## Scope Split

### Current proven scope

- offer OCR parsing
- economics calculation
- postcode extraction
- traffic beacon capture
- outcode/sector risk model
- route-line shadow scoring
- GitHub-based data ops

### New native scope

- SwiftUI shell
- persistent local database
- visual map UI
- structured settings
- native telemetry and capture services
- internal model engine

## Architecture

### App layers

1. `Capture Layer`
2. `Parsing Layer`
3. `Evidence Layer`
4. `Decision Layer`
5. `Presentation Layer`
6. `Sync / Export Layer`

### Suggested module map

- `AppCore`
- `OfferCapture`
- `OfferParser`
- `TrafficBeaconing`
- `TrafficEvidenceStore`
- `RouteEngine`
- `DecisionEngine`
- `OperatorRules`
- `HistoryStore`
- `NotificationEngine`
- `MapUI`
- `DebugTools`

## Storage Strategy

Use local structured persistence, not loose files as the primary runtime mechanism.

Recommended:
- SQLite or SwiftData/Core Data for app runtime
- JSON export snapshots for debug and backup

Core entities:

- `Offer`
- `OfferParseDebug`
- `BeaconEvent`
- `BeaconAggregate`
- `RouteEvidence`
- `OperatorRule`
- `DecisionSnapshot`
- `TripOutcome`

## Data Model

### Offer

Fields:
- timestamp
- raw OCR text
- pickup address
- dropoff address
- pickup postcode/outcode/sector
- dropoff postcode/outcode/sector
- pickup minutes/miles
- trip minutes/miles
- fare
- rating
- vehicle type
- reserved flag
- surge text

### BeaconEvent

Fields:
- timestamp
- latitude
- longitude
- address
- postcode/outcode/sector
- time bucket
- weekday
- weekpart
- speed/course
- status (`traffic`, future `no_traffic`)
- precision level

### RouteEvidence

Fields:
- offer id
- route line length
- exact beacon hits
- near beacon hits
- weighted trap score
- matched time windows
- matched corridors

### DecisionSnapshot

Fields:
- offer id
- pay metrics
- traffic verdict
- route verdict
- final verdict
- reason list
- operator overrides applied

## Parsing Port Plan

Port the Python parser in stages.

### Stage 1

Port pure deterministic helpers:
- money parsing
- time/distance parsing
- postcode normalization
- address cleanup
- vehicle type extraction

### Stage 2

Port structural parsing:
- pickup/trip pairs
- address block extraction
- surge/reserved/rating logic
- parse validity checks

### Stage 3

Port derived metrics:
- adjusted per minute
- hourly adjusted
- pickup/trip status
- CCZ handling

Important:
- preserve the latest OCR fixes
- do not reintroduce old postcode regressions

## Beacon Strategy

### Immediate goal

Manual beacon capture remains acceptable in early native versions if it is faster and cleaner than Pythonista.

### Later goal

Passive or semi-passive beacon capture that creates traffic evidence without extra friction.

### Beacon outputs

The app should maintain:
- raw event history
- per-day shards
- outcode aggregates
- sector aggregates
- time window aggregates
- line-grid cells
- route-point cloud
- corridor summaries

## Route Corridor Engine

This is the key differentiator.

### Problem

Dropoff can look fine while the path is terrible.

### Required engine

Given pickup and dropoff:

1. derive route corridor
2. expand to a fat line / polygon
3. intersect known beacon geometry
4. weight hits by:
   - distance to centerline
   - time bucket
   - same weekday/weekpart
   - confidence
   - operator blacklist corridors

### Current shortcut-era approximation

The live Pythonista version uses:
- line-grid cells
- route-point cloud
- local weighted hit scoring

### Native target

Use real geometry and routing if possible:
- MapKit route polyline
- buffered corridor
- fast spatial intersection

This is better than a naive straight line.

## Decision Engine

The decision engine should be explicit and auditable.

### Inputs

- parsed offer
- pay metrics
- beacon DB evidence
- route corridor evidence
- operator rules
- time bucket

### Outputs

- `ACCEPT`
- `DECLINE`
- `REVIEW`

### Rule categories

- pay floor
- pickup penalty
- low rating
- destination family
- destination sector
- route trap count
- route trap score
- blacklisted road hit
- operator exceptions

## Operator Override System

This must be first-class.

Examples:
- Parkhurst/Holloway is bad regardless of weak sample count
- certain central zones are acceptable only in specific times
- some north/east pulls are hard decline

Override types:
- exact road
- corridor
- outcode
- sector
- time-scoped area
- route rule

## Accepted / Declined Outcome Labeling

Long-term, the app needs to know not only what was offered, but what happened next.

Target behavior:

- infer accepted trip if device movement aligns with pickup then route progression
- infer decline if offer disappears without matching movement
- confirm completed trip when subsequent movement and stop pattern fit dropoff

This is a later native feature and should not block the initial build.

## Automation Plan

### Phase A: assistive

- notification
- verdict
- map
- no automatic action

### Phase B: semi-automatic

- pre-arm decision
- quick confirm/decline UI
- smart prompts

### Phase C: automatic

- continuous offer detection
- auto accept/decline policy
- background evidence capture

Note:
- final automatic action depends heavily on iOS platform limits and deployment model

## UX Plan

### Core screens

1. `Live Offer`
2. `Beacon Map`
3. `Trip History`
4. `Trap Corridors`
5. `Rules / Overrides`
6. `Debug / Data Export`

### Live Offer screen must show

- fare
- rating
- pickup/trip time and miles
- traffic color
- route trap count
- route trap score
- short reason string

Example compact UI:
- `RED 4 traps`
- `Route score 6.2`
- `Parkhurst trap`

## Performance Rules

- scoring must stay near-instant
- notifications cannot wait on heavy rebuilds
- expensive work must be cached or deferred
- raw history should not be scanned every time
- all live scoring should run from compact indexes

## Delivery Milestones

### Milestone 1: Core native prototype

- SwiftUI app shell
- parser port
- local offer scoring
- basic verdict UI

### Milestone 2: Beacon intelligence

- beacon event capture
- aggregate storage
- map visualization
- road/corridor overlay

### Milestone 3: Route intelligence

- route polyline
- corridor intersection engine
- route trap score in verdict

### Milestone 4: Outcome learning

- accepted/declined inference
- trip outcome linkage
- better confidence logic

### Milestone 5: Automation track

- if technically feasible, auto decision execution

## Immediate Engineering Tasks

1. Preserve the current Pythonista logic as the reference behavior.
2. Build a native parser test set from real saved offers.
3. Port the parser and verdict logic into pure Swift models.
4. Port beacon DB structures and route-line math.
5. Rebuild the live offer notification UI natively.
6. Add a map showing beacon points and blacklisted corridors.

## Pythonista Reference Rules

When consulting the live scripts during the port, treat these as reference assets:

- `UberTripLoggerPostcodeIsolation.py` is the current parser/verdict reference
- `traffic_beacon.py` is the current beacon/evidence reference
- do not treat older logger snapshots as truth
- be careful with notification-order regressions

## Risks

### Technical

- OCR parity between Python and native implementation
- routing/corridor geometry complexity
- background execution limits
- cross-app automation restrictions on iOS

### Product

- overfitting sparse beacon evidence
- slow scoring if raw history is used directly
- false confidence from destination-only heuristics

## Success Criteria

The native app is successful when:

- it matches or beats Pythonista latency
- it reproduces current verdict quality
- it uses route trap logic reliably
- it lets the driver decide in under 3 seconds
- it creates durable structured history for future automation

## Build Philosophy

- keep the live Pythonista system stable
- use it as reference, not as forever runtime
- port validated logic first
- add automation only after decision quality is strong
- prioritize route intelligence over generic zone labels
