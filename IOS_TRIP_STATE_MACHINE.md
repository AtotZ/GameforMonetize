# Native iOS Trip State Machine

## Purpose

This file defines the native trip lifecycle logic for the future iOS app.

It answers:

- how the app should infer accepted trips
- how the app should infer declined or expired offers
- how the app should infer en-route movement
- how the app should infer completed trips
- what should be written into the local DB at each step

This state machine is intended to use only Apple-allowed signals such as:

- offer ingest from shortcut or app-side capture
- `CoreLocation`
- `CoreMotion`
- local tracker state
- route progress
- visit and region monitoring where helpful

It should not depend on private Uber app APIs.

## Product Role

This is the bridge between:

- offered trip truth
- observed driver behavior
- completed-trip ground truth

Without this state machine, the app only knows what was offered.
With it, the app can build a much stronger DB of:

- accepted trips
- declined trips
- cancelled trips
- completed trips
- route-following behavior

That DB is one of the most important assets for future native automation.

## Core Principle

The app should treat offer OCR as the writer of route truth:

- pickup address
- dropoff address
- shown fare
- estimated pickup/trip minutes
- estimated pickup/trip miles
- product type

The GPS state machine should then confirm behavioral truth:

- whether the driver actually moved toward pickup
- whether pickup was likely reached
- whether the trip moved along the offered route
- whether dropoff was likely completed

The GPS layer must never rewrite the route truth fields themselves.

## Allowed Signals

### Allowed and realistic

- `CoreLocation` background updates
- significant location change
- visit monitoring
- region monitoring
- `CoreMotion` activity
- heading and speed
- foreground app lifecycle
- local notifications

### Not reliable for App Store-safe auto-action

- reading Uber internals
- inspecting Uber private UI state
- auto tapping Uber buttons
- guaranteed cross-app offer detection from screen contents

Therefore:

- accepted/completed inference is realistic
- full auto accept/decline inside Uber is not the primary native assumption

## State Model

The native tracker should use a clear finite state machine.

Recommended states:

- `idle`
- `offered`
- `armed`
- `moving_to_pickup`
- `pickup_reached`
- `en_route`
- `completed`
- `expired`
- `declined`
- `cancelled`
- `ambiguous`

## State Definitions

### `idle`

No active candidate trip.

### `offered`

A new offer has been parsed and stored, but no movement evidence exists yet.

### `armed`

The app is watching the offered trip for a short decision window.

This window exists because the trip can:

- be ignored
- be declined
- be accepted
- disappear for unrelated reasons

### `moving_to_pickup`

Movement suggests the driver is intentionally heading toward the pickup.

### `pickup_reached`

The device has likely arrived at pickup or within the pickup dwell zone.

### `en_route`

Movement after pickup aligns with the offered route toward dropoff.

### `completed`

Movement, stopping behavior, and route progress strongly indicate the dropoff has been completed.

### `expired`

The offer disappeared or aged out without enough evidence of acceptance.

### `declined`

The app has strong evidence the driver did not take the offer and instead remained idle or moved incompatibly.

### `cancelled`

The trip likely started but did not complete as expected.

### `ambiguous`

Signals conflict or are too weak to make a confident automatic label.

## Lifecycle Overview

The intended lifecycle is:

1. offer parsed
2. candidate stored as `offered`
3. watch short acceptance window
4. if movement aligns with pickup, transition to `moving_to_pickup`
5. if pickup reached, transition to `pickup_reached`
6. if route progress begins toward dropoff, transition to `en_route`
7. if route progress and stopping behavior fit arrival, transition to `completed`

Fallback paths:

- `offered` -> `expired`
- `offered` -> `declined`
- `moving_to_pickup` -> `cancelled`
- `pickup_reached` -> `cancelled`
- `en_route` -> `cancelled`
- any uncertain branch -> `ambiguous`

## Acceptance Inference

### Goal

Infer that the driver accepted the trip without needing a manual accept tap.

### Strong signals

- movement starts within a short window after offer ingest
- heading aligns broadly toward pickup
- distance to pickup decreases consistently
- speed rises above idle threshold
- route to pickup remains plausible for several pings

### Suggested logic

Transition `offered` -> `moving_to_pickup` if all hold:

- offer age <= 5 minutes
- at least 2 or 3 consecutive location updates reduce pickup distance
- net pickup distance reduction exceeds a minimum threshold
- motion is not stationary

Suggested practical thresholds:

- minimum distance reduction: 150 to 250 meters
- minimum movement speed: above walking-idle noise
- consecutive confirming pings: 2 to 3

### Anti-false-positive guards

Do not mark accepted if:

- the driver remains stationary
- movement is mostly away from pickup
- the offer disappears and no pickup-aligned movement follows
- another newer offer supersedes it first

## Pickup Reached Inference

Transition `moving_to_pickup` -> `pickup_reached` when:

- device enters a pickup radius
- or route-to-pickup progress is effectively complete
- and movement slows or pauses in a way consistent with pickup

Suggested pickup evidence:

- inside 50 to 100 meter pickup radius
- or inside a wider radius with clear dwell
- low speed for a short dwell period

This state matters because it separates:

- accepted but never arrived
- accepted and likely collected rider

## En-Route Inference

Transition `pickup_reached` -> `en_route` when:

- the device leaves pickup area
- and begins making progress along the pickup-to-dropoff route

Required signals:

- distance from pickup increases after dwell
- route progress toward dropoff increases
- movement aligns with route corridor more than random drift

This is where the route engine becomes essential.

The app should prefer:

- route polyline progress
- corridor snap confidence
- distance to route centerline

rather than only:

- radius around dropoff

## Completion Inference

Transition `en_route` -> `completed` when:

- route progress reaches a high completion threshold
- and speed drops or stop behavior looks like arrival
- and the device is near the end corridor or dropoff area

Suggested completion evidence:

- route progress >= 90%
- low speed or stop within final route segment
- no continued movement inconsistent with post-dropoff completion

This mirrors the route-progress direction already documented in the parent OnisAI GPS route plan.

## Declined vs Expired

The system should distinguish these where possible.

### `expired`

Use when:

- the offer window ended
- no acceptance evidence appeared
- the app cannot confidently say the driver actively rejected it

### `declined`

Use when:

- a manual decline signal exists
- or a newer accepted behavior clearly superseded the old offer
- or movement pattern clearly contradicts pickup acceptance

If confidence is weak, prefer `expired` over `declined`.

## Cancelled Inference

Use `cancelled` when the app saw partial trip behavior but not a clean completion.

Examples:

- movement toward pickup began but reversed hard
- pickup was reached but en-route behavior never formed
- en-route began but route completion evidence collapsed

This is important because cancelled trips should not be merged into clean completed-trip analytics.

## Ambiguous State

`ambiguous` is not a failure. It is a safety valve.

Use it when:

- signals conflict
- GPS quality is poor
- route geometry is missing
- battery/background execution interrupted the chain
- two competing candidate trips overlap

The app should preserve these cases for later review rather than forcing a wrong label.

## Candidate Arbitration

Multiple offers can exist close together.

The native app should maintain:

- one primary active candidate
- optional secondary shadow candidates

Arbitration should prefer:

1. newest offer
2. strongest pickup-aligned movement
3. strongest route progression evidence

When one candidate becomes strongly active, weaker overlapping candidates should usually become:

- `declined`
- `expired`
- or `ambiguous`

depending on confidence.

## DB Write Rules

### At offer ingest

Create `Offer` row with:

- raw OCR
- parsed trip truth
- decision snapshot
- initial state = `offered`

### At each state transition

Append state transition event:

- previous state
- new state
- timestamp
- reason codes
- evidence summary

Do not overwrite history silently.

### At completion

Create or finalize `TripOutcome` row with:

- linked offer id
- accepted inference confidence
- completed inference confidence
- route progress summary
- duration summary
- movement evidence summary
- final label = `completed`

### At decline or expiry

Finalize candidate with:

- final label
- confidence
- reason codes

### At ambiguity

Persist enough evidence for later audit:

- last known route progress
- pickup/dropoff distances
- movement class
- confidence breakdown

## Reason Codes

Every transition should carry machine-readable reason codes.

Examples:

- `pickup_distance_decreasing`
- `pickup_radius_entered`
- `pickup_dwell_detected`
- `route_progress_started`
- `route_progress_completed`
- `dropoff_stop_detected`
- `offer_aged_out`
- `movement_away_from_pickup`
- `candidate_superseded`
- `gps_confidence_low`
- `route_missing`
- `background_gap`

These reason codes are critical for debugging and trust.

## Confidence Model

Every final label should carry a confidence score.

Suggested outputs:

- `high`
- `medium`
- `low`

Or numeric:

- `0.0` to `1.0`

Recommended final labels by confidence:

- auto analytics may trust `high`
- model training may use `high` and some `medium`
- automation policy should generally ignore `low`

## Minimum Useful Native Version

The first useful native state machine does not need full auto accept/decline.

It only needs to do these well:

- store offers
- infer accepted vs not accepted
- infer completed vs not completed
- build a reliable completed-trip DB

That alone is a major product upgrade over offer-only history.

## Relationship To Beacon Logic

Beacon-map corridor scoring and GPS state inference serve different roles:

- beacon map helps decide whether to take the trip
- GPS tracker helps confirm what actually happened after the offer

They should remain separate but linked.

The joined data later becomes powerful:

- offered route risk
- actual accepted behavior
- actual completion outcome

That is how the app graduates from a scorer into a learning operator system.

## Immediate Native Build Use

This state machine should directly feed:

- completed-trip DB building
- accepted/declined training labels
- route outcome analytics
- future auto-policy confidence gating

## Recommended Next Build Order

1. implement local `Offer` + `TripOutcome` models
2. add transition event log
3. add pickup-distance trend inference
4. add route progress inference
5. add completed inference
6. add ambiguity/cancel paths
7. only after that, use these labels in deeper automation logic
