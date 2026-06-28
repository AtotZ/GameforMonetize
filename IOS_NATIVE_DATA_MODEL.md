# Native iOS Data Model

## Purpose

This file defines the native app persistence model.

This project should be built SwiftData-first, with Core Data compatibility in mind.
It should not be planned as a SQLite-first app.

Why:

- the target runtime is native iPhone
- SwiftData integrates cleanly with SwiftUI
- object relationships matter heavily in this app
- history, state transitions, and route evidence are easier to model as linked entities
- later Cloud sync or export flows can sit above the model layer

## Persistence Choice

### Preferred

- `SwiftData`

### Compatible fallback

- `Core Data`

### Not the primary plan

- raw file persistence
- hand-managed local JSON as runtime truth
- SQLite-first schema design

JSON remains useful for:

- export
- debug snapshots
- handoff
- backup

but not as the live source of truth.

## Design Principles

The native data layer must support:

- fast live offer scoring
- durable trip lifecycle history
- beacon evidence aggregation
- route corridor evidence
- explainable decisions
- future accepted/completed learning

The model should separate:

- route truth
- behavior truth
- derived evidence
- operator overrides

## Primary Entities

Recommended first-class entities:

- `Offer`
- `DecisionSnapshot`
- `TripOutcome`
- `StateTransitionEvent`
- `BeaconEvent`
- `RouteEvidence`
- `OperatorRule`
- `TrackerSession`

Optional later entities:

- `BeaconAggregateWindow`
- `CorridorProfile`
- `ImportBatch`
- `ExportSnapshot`

## Offer

`Offer` is the authoritative stored record of what was shown on the offer card.

### Role

- owns route truth
- stores parsed OCR output
- anchors later decision and outcome records

### Required fields

- `id: UUID`
- `createdAt: Date`
- `source: String`
- `shortcutSourceTag: String?`
- `rawOCRText: String`
- `ocrSHA1: String?`
- `pickupAddress: String`
- `dropoffAddress: String`
- `pickupPostcode: String?`
- `dropoffPostcode: String?`
- `pickupOutcode: String?`
- `dropoffOutcode: String?`
- `pickupSector: String?`
- `dropoffSector: String?`
- `pickupLatitudeHint: Double?`
- `pickupLongitudeHint: Double?`
- `dropoffLatitudeHint: Double?`
- `dropoffLongitudeHint: Double?`
- `pickupMinutes: Double`
- `pickupMiles: Double`
- `tripMinutes: Double`
- `tripMiles: Double`
- `shownFareGBP: Double`
- `rating: Double`
- `vehicleType: String`
- `surgeText: String?`
- `isReserved: Bool`
- `parseValid: Bool`
- `parseError: String?`

### Relationships

- one `Offer` -> many `DecisionSnapshot`
- one `Offer` -> zero or one `TripOutcome`
- one `Offer` -> many `StateTransitionEvent`
- one `Offer` -> zero or one `RouteEvidence`

## DecisionSnapshot

`DecisionSnapshot` stores what the decision engine believed at a specific moment.

### Role

- preserves scoring history
- explains why the app said accept, decline, or review
- keeps route and beacon logic auditable

### Required fields

- `id: UUID`
- `createdAt: Date`
- `offerID: UUID`
- `verdict: String`
- `trafficStatus: String`
- `trafficLabel: String?`
- `trafficReason: String?`
- `routeTrapCount: Int`
- `timedRouteTrapCount: Int`
- `nearRouteTrapCount: Int`
- `routeTrapScore: Double`
- `perMinuteAdjustedGBP: Double`
- `perMileIncludingPickupGBP: Double`
- `hourlyAdjustedGBP: Double`
- `payStatus: String`
- `pickupStatus: String`
- `reasonSummary: String?`
- `reasonCodes: [String]`
- `operatorOverrideApplied: Bool`
- `operatorOverrideName: String?`
- `confidence: Double?`

### Relationship

- many `DecisionSnapshot` -> one `Offer`

Usually one live offer will only need one primary snapshot, but keeping the entity separate avoids silent overwrites later.

## TripOutcome

`TripOutcome` is the behavioral truth record for what happened after the offer.

### Role

- accepted / declined / expired / cancelled / completed truth
- route-progress truth
- later final fare or end-of-trip confirmation hooks

### Required fields

- `id: UUID`
- `offerID: UUID`
- `finalState: String`
- `acceptedInferenceConfidence: Double`
- `completedInferenceConfidence: Double`
- `startedAt: Date?`
- `pickupReachedAt: Date?`
- `enRouteAt: Date?`
- `completedAt: Date?`
- `finalizedAt: Date`
- `routeProgressMax: Double?`
- `pickupDistanceReductionMeters: Double?`
- `dropoffArrivalDistanceMeters: Double?`
- `movementSummary: String?`
- `reasonCodes: [String]`
- `manualOverrideState: String?`
- `manualOverrideNote: String?`

### Optional later fare overlay fields

- `finalFareGBP: Double?`
- `tipGBP: Double?`
- `actualMinutes: Double?`
- `actualMiles: Double?`

These belong here only if native later owns final-outcome ingestion too.

### Relationship

- one `TripOutcome` -> one `Offer`

## StateTransitionEvent

This is the event log for the trip state machine.

### Role

- preserves lifecycle steps
- explains why a candidate changed state
- makes regressions easier to debug

### Required fields

- `id: UUID`
- `offerID: UUID`
- `timestamp: Date`
- `fromState: String`
- `toState: String`
- `reasonCodes: [String]`
- `pickupDistanceMeters: Double?`
- `dropoffDistanceMeters: Double?`
- `routeProgress: Double?`
- `speedMPS: Double?`
- `headingDegrees: Double?`
- `confidence: Double?`
- `note: String?`

### Relationship

- many `StateTransitionEvent` -> one `Offer`

## BeaconEvent

`BeaconEvent` is the atomic traffic observation unit.

### Role

- raw traffic mine record
- source for time-window aggregation
- source for corridor scoring

### Required fields

- `id: UUID`
- `timestamp: Date`
- `status: String`
- `address: String`
- `postcode: String?`
- `outcode: String?`
- `sector: String?`
- `latitude: Double`
- `longitude: Double`
- `horizontalAccuracy: Double?`
- `speedMPS: Double?`
- `courseDegrees: Double?`
- `weekday: Int`
- `weekpart: String`
- `hour: Int`
- `minute: Int`
- `timeBucket: String`
- `fifteenMinuteWindow: String`
- `source: String`

### Optional geometry helpers

- `lineGridCell: String?`
- `corridorTag: String?`

## RouteEvidence

`RouteEvidence` stores the route-level beacon intersection summary for one offer.

### Role

- corridor-first acceptance logic
- route trap count shorthand
- compact evidence without rescanning raw history every time

### Required fields

- `id: UUID`
- `offerID: UUID`
- `computedAt: Date`
- `routeMode: String`
- `corridorWidthMeters: Double`
- `exactHits: Int`
- `nearHits: Int`
- `timedHits: Int`
- `weightedTrapScore: Double`
- `operatorRuleHits: Int`
- `primaryReason: String?`
- `matchedOutcodes: [String]`
- `matchedSectors: [String]`
- `matchedBeaconIDs: [UUID]`

### Optional geometry cache

- `routePolylineEncoded: String?`
- `corridorBoundingBox: String?`

The native app can choose whether to cache the route polyline directly here or in a separate route object later.

## OperatorRule

`OperatorRule` stores explicit human truth.

### Role

- override weak model evidence
- encode blacklist roads, corridors, and time-scoped exceptions

### Required fields

- `id: UUID`
- `createdAt: Date`
- `updatedAt: Date`
- `name: String`
- `ruleType: String`
- `status: String`
- `priority: Int`
- `matchKeywords: [String]`
- `matchOutcodes: [String]`
- `matchSectors: [String]`
- `timeBuckets: [String]`
- `weekparts: [String]`
- `reasonCode: String`
- `note: String?`
- `isEnabled: Bool`

## TrackerSession

`TrackerSession` groups location behavior over an operational period.

### Role

- helps background GPS lifecycle
- ties multiple offers to one working session
- supports future diagnostics

### Required fields

- `id: UUID`
- `startedAt: Date`
- `endedAt: Date?`
- `state: String`
- `deviceStateSummary: String?`
- `batteryAtStart: Double?`
- `batteryAtEnd: Double?`
- `lowPowerModeAtStart: Bool`
- `thermalStateAtStart: String?`

### Optional relationships

- one `TrackerSession` -> many `Offer`
- one `TrackerSession` -> many `BeaconEvent`

## Relationships Overview

Recommended graph:

- `Offer`
  - has many `DecisionSnapshot`
  - has many `StateTransitionEvent`
  - has zero or one `TripOutcome`
  - has zero or one `RouteEvidence`
- `BeaconEvent`
  - remains independent raw evidence
- `OperatorRule`
  - independent but referenced by decision and route logic
- `TrackerSession`
  - parent operational context for offers and beacons

## Minimum Viable SwiftData Model

If building the first native version fast, the minimum required entities are:

- `Offer`
- `DecisionSnapshot`
- `TripOutcome`
- `StateTransitionEvent`
- `BeaconEvent`

`RouteEvidence` can still be included early because it is strategically important, but the app can compute it lazily at first.

## Required Query Patterns

The model must support these fast queries:

- latest offered trip
- all open candidate trips
- latest decision snapshot for an offer
- all state transitions for one offer
- beacon events by:
  - outcode
  - sector
  - time bucket
  - 15-minute window
  - recent time range
- route evidence for one offer
- recent completed outcomes

This means the app should index at the model layer around:

- timestamps
- offer ids
- outcodes
- sectors
- time bucket fields
- final state

## Value Types and Enums

Strongly prefer typed enums in Swift rather than free text everywhere.

Recommended enums:

- `OfferLifecycleState`
- `DecisionVerdict`
- `BeaconStatus`
- `TimeBucket`
- `Weekpart`
- `OperatorRuleType`
- `PayStatus`
- `PickupStatus`

Persist them in a way that remains migration-safe.

## Data Retention Strategy

SwiftData runtime should keep:

- full current-day offers
- full current-day transitions
- full beacon raw history
- compact route evidence

Longer-term retention can be:

- full local history for recent period
- older history archived to export files or cloud sync

But the app should not depend on raw history scans for live scoring.

## Export Strategy

The native app should export JSON snapshots for:

- offers
- completed outcomes
- beacon events
- route evidence
- operator rules

That keeps interoperability with analysis tooling and future chats.

## Migration Guidance

The model should be introduced in this order:

1. `Offer`
2. `DecisionSnapshot`
3. `StateTransitionEvent`
4. `TripOutcome`
5. `BeaconEvent`
6. `RouteEvidence`
7. `OperatorRule`
8. `TrackerSession`

This order matches the actual product dependency chain.

## Immediate Recommendation

For the first native build:

- use SwiftData
- define the six core entities
- keep route truth immutable after ingest
- append state transitions instead of rewriting hidden state
- compute corridor evidence into `RouteEvidence`
- keep export JSON as a secondary debug/output layer only
