# Native Decision Engine Contract

## Purpose

This file defines the contract for the native decision engine.

The engine answers one question fast:

- should this offer be accepted, declined, or reviewed?

It must do that using:

- parsed offer truth
- beacon-map corridor evidence
- operator overrides
- pay quality
- timing context

without blocking on heavy recomputation.

## Design Rule

The decision engine is a consumer of truth, not a writer of route truth.

It reads:

- `Offer`
- `RouteEvidence`
- `BeaconEvent` aggregates
- `OperatorRule`
- optional current tracker context

It writes:

- `DecisionSnapshot`

It must not mutate offer route fields.

## Primary Inputs

### Required

- parsed offer
- computed pay metrics
- route evidence
- operator rules
- time bucket

### Optional but useful

- current driver location
- current active tracker session
- existing nearby traffic context
- learned confidence from prior data

## Contract Input Shape

Suggested native input object:

```swift
struct DecisionEngineInput {
    let offer: Offer
    let routeEvidence: RouteEvidence?
    let activeRules: [OperatorRule]
    let now: Date
    let currentTimeBucket: TimeBucket
    let weekday: Int
    let weekpart: Weekpart
    let currentLocation: CLLocationCoordinate2D?
}
```

## Primary Outputs

The engine should return:

- verdict
- compact operator-facing label
- internal weighted reasons
- machine-readable reason codes

## Contract Output Shape

```swift
struct DecisionEngineOutput {
    let verdict: DecisionVerdict
    let compactLabel: String
    let routeTrapCount: Int
    let timedRouteTrapCount: Int
    let routeTrapScore: Double
    let trafficStatus: String
    let trafficLabel: String?
    let trafficReason: String?
    let payStatus: PayStatus
    let pickupStatus: PickupStatus
    let operatorOverrideApplied: Bool
    let operatorOverrideName: String?
    let reasonSummary: String
    let reasonCodes: [String]
    let confidence: Double
}
```

## Core Precedence

The engine should evaluate in this order:

1. operator hard overrides
2. route corridor beacon danger
3. destination zone pressure
4. pay quality
5. rating and secondary heuristics

This order is intentional.

The product goal is not to build a generic scoring blend. The product goal is to avoid bad routes quickly.

## Rule Layers

### Layer 1: Operator hard overrides

Examples:

- blacklisted road
- blacklisted corridor
- hard red zone at specific times

Expected behavior:

- if a hard decline override matches, return `decline` immediately
- if a hard accept override exists in future, it can short-circuit too

### Layer 2: Route corridor evidence

This is the primary live risk layer.

Inputs:

- exact route trap hits
- near route trap hits
- timed route trap hits
- weighted route trap score

Expected compact output:

- `RED x4`
- `AMBER x2`
- `GREEN x0`

### Layer 3: Destination zone logic

Use only after the route logic has been evaluated.

This is where:

- family color
- sector pressure
- central-edge caution

can assist but should not dominate the route corridor result.

### Layer 4: Pay quality

Pay should filter obvious bad trips and rescue obvious strong ones, but not blindly overrule route toxicity.

Inputs:

- adjusted per minute
- adjusted per mile
- adjusted hourly
- pickup burden

### Layer 5: Secondary heuristics

Examples:

- rider rating
- reserved flag
- surge text
- vehicle type

These should be additive, not dominant.

## Recommended Verdict Rules

### Hard decline

Return `decline` if:

- operator hard blacklist matched
- or route trap count >= hard threshold
- or timed route trap count >= hard threshold
- or route trap score >= hard threshold

### Review

Return `review` if:

- route evidence is mixed
- pay is strong but route evidence is moderate
- destination appears neutral but corridor evidence is incomplete
- GPS or beacon confidence is too thin for hard action

### Accept

Return `accept` if:

- route evidence is clean
- no hard overrides matched
- pay passes threshold
- pickup burden is acceptable

## Threshold Model

Thresholds should not be hardcoded forever inside the engine body.

They should live in configurable settings such as:

- `hardDeclineTrapCount`
- `hardDeclineTimedTrapCount`
- `hardDeclineTrapScore`
- `reviewTrapCount`
- `minimumPerMinuteAdjusted`
- `minimumHourlyAdjusted`
- `maximumPickupMinutes`
- `maximumPickupMiles`

## Reason Codes

The engine must emit machine-readable reasons.

Examples:

- `operator_blacklist_road`
- `operator_blacklist_corridor`
- `route_trap_count_hard`
- `route_trap_score_hard`
- `timed_route_trap_count_hard`
- `destination_zone_red`
- `pay_floor_failed`
- `pickup_too_far`
- `rating_too_low`
- `route_clean`
- `pay_strong`

## Compact Notification Format

The operator-facing top line should stay compressed.

Target pattern:

- `<rating> | <fare> | <color> x<count>`

Examples:

- `4.82 | GBP13.24 | RED x3`
- `4.90 | GBP13.04 | AMBER x1`
- `4.86 | GBP9.26 | GREEN x0`

Short reason line may follow:

- `Route score 4.2 | timed hits 2`
- `Parkhurst trap`
- `Clean corridor`

## Decision Snapshot Persistence

Every completed decision run should persist a `DecisionSnapshot`.

At minimum it should store:

- verdict
- route trap count
- timed route trap count
- route trap score
- reason codes
- compact label

This is necessary for auditability and future replay.

## Performance Rules

The decision engine must assume:

- live offer scoring is latency-sensitive
- notification must happen quickly
- raw beacon history should not be scanned during live scoring

Therefore the engine should consume:

- compact `RouteEvidence`
- compact time-window aggregates
- precomputed operator rules

not full raw history.

## Failure Modes

If route evidence is missing:

- do not freeze
- downgrade to lighter zone logic
- return `review` rather than false confidence if needed

If operator rules are missing:

- continue with corridor + pay logic

If beacon data is sparse:

- use weaker confidence
- prefer `review` over forced `accept`

## Shadow Mode and Production Mode

The engine should support two modes:

### Shadow mode

- computes full decision output
- stores it
- does not drive automation

### Production mode

- computes full decision output
- can drive UI prompts
- later may gate semi-automatic or automatic action

## Recommended Interface

Suggested main interface:

```swift
protocol DecisionEngine {
    func evaluate(_ input: DecisionEngineInput) -> DecisionEngineOutput
}
```

Optional:

```swift
protocol DecisionSettingsProvider {
    var hardDeclineTrapCount: Int { get }
    var hardDeclineTimedTrapCount: Int { get }
    var hardDeclineTrapScore: Double { get }
    var minimumPerMinuteAdjusted: Double { get }
    var maximumPickupMinutes: Double { get }
}
```

## Minimum Useful Native Version

The first useful engine should do these five things well:

1. apply operator blacklists
2. read route corridor evidence
3. return `RED xN / AMBER xN / GREEN x0`
4. use pay as a secondary filter
5. persist a decision snapshot

Everything else can evolve later.
