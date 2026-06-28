# Native Route Corridor Engine Contract

## Purpose

This file defines the route corridor engine contract for the native iOS app.

This engine is responsible for turning:

- pickup
- dropoff
- beacon geometry
- timing relevance

into the most important traffic-risk signal in the product.

## Product Role

This engine exists because endpoint-only scoring is not enough.

A trip can look fine on:

- dropoff postcode
- destination family
- pay

and still be operationally bad because the route crosses known trap corridors.

So the corridor engine is the layer that answers:

- what does this route actually pass through?

## Inputs

### Required

- pickup coordinate or resolved pickup point
- dropoff coordinate or resolved dropoff point
- active beacon geometry index
- operator corridor and road rules
- current time bucket
- weekday
- weekpart

### Optional

- live current driver location
- MapKit route polyline metadata
- prior corridor confidence

## Input Shape

```swift
struct RouteCorridorEngineInput {
    let offerID: UUID
    let pickupCoordinate: CLLocationCoordinate2D
    let dropoffCoordinate: CLLocationCoordinate2D
    let routeMode: RouteMode
    let currentTimeBucket: TimeBucket
    let weekday: Int
    let weekpart: Weekpart
    let corridorWidthMeters: Double
}
```

## Route Modes

Recommended route modes:

- `straightLine`
- `mapKitRoute`
- `cachedRoute`

Expected behavior:

- prefer real routed geometry where available
- fall back to straight-line corridor only when necessary

## Beacon Geometry Inputs

The engine should not consume raw beacon history by scanning the full store every time.

It should consume a compact geometry index built from beacon data, such as:

- route points
- line-grid cells
- outcode and sector centroid helpers
- time-window groupings

## Core Output

The corridor engine should return compact route evidence suitable for live decisioning.

## Output Shape

```swift
struct RouteCorridorEngineOutput {
    let routeMode: RouteMode
    let corridorWidthMeters: Double
    let exactHits: Int
    let nearHits: Int
    let timedHits: Int
    let weightedTrapScore: Double
    let operatorRuleHits: Int
    let matchedBeaconIDs: [UUID]
    let matchedOutcodes: [String]
    let matchedSectors: [String]
    let primaryReason: String?
    let confidence: Double
}
```

## What Counts As A Hit

### Exact hit

A beacon lies inside the primary route corridor.

### Near hit

A beacon lies just outside the primary corridor but still close enough to suggest route pressure.

### Timed hit

A hit whose time profile aligns with the current trip timing context.

Examples:

- same 15-minute window
- same weekday
- same weekpart

Timed hits matter more than generic historical hits.

## Geometry Model

### Preferred native model

1. request routed path from MapKit
2. represent that as polyline segments
3. buffer the polyline into a corridor
4. intersect beacon geometry against that corridor

### Fallback model

1. build straight line from pickup to dropoff
2. buffer into a wide corridor
3. intersect against beacon geometry

The fallback is useful, but it should not be the long-term gold standard.

## Corridor Width

The engine should not use a zero-width line.

Recommended runtime width:

- configurable
- default practical driving width

The width should reflect:

- route uncertainty
- lane spread
- nearby congestion bleed

The product goal is operational usefulness, not geometric purity.

## Weighting Logic

The weighted trap score should combine:

- exact hits
- near hits
- timed hits
- beacon density
- weekday relevance
- weekpart relevance
- operator corridor penalties

Suggested weighting direction:

- exact timed hits count most
- exact non-timed hits next
- near timed hits next
- near non-timed hits least

## Operator Rules

The engine must also evaluate explicit operator corridor and road rules.

Examples:

- Parkhurst corridor
- Holloway Road trap
- hand-known all-day bad pull

These should appear separately from generic beacon hits so the decision layer can explain:

- `RED x2`
- `Parkhurst trap`

instead of pretending all danger came from anonymous beacon density.

## Time Awareness

Time matters heavily.

The same route can be:

- clean in late evening
- toxic in morning
- mixed in midday

So the corridor engine must carry time context through the intersection logic.

Minimum time dimensions:

- time bucket
- 15-minute window
- weekday
- weekpart

## Confidence

The engine should emit a confidence score.

Confidence should rise when:

- route geometry is real MapKit route
- multiple matching beacons exist
- hits align with current time window
- operator rules confirm the same pattern

Confidence should fall when:

- geometry is straight-line fallback only
- only one weak near hit exists
- time mismatch is large
- input coordinates are coarse

## Performance Constraints

This engine participates in the live offer path.

Therefore:

- no full raw beacon scans
- no heavy rebuild during scoring
- no blocking network call if avoidable
- compact indexes must be prebuilt

If a fresh routed path is too expensive in the live window, the engine should:

- use cached geometry
- or degrade gracefully to lighter mode

not stall notification.

## Failure Behavior

If pickup or dropoff coordinates cannot be resolved:

- return low-confidence empty route evidence
- do not crash the decision path

If route geometry cannot be built:

- fall back to straight-line mode if allowed

If beacon index is unavailable:

- return zero-hit low-confidence evidence

## Persistence

After evaluation, the output should be persisted as `RouteEvidence`.

This avoids recomputing the same route evidence repeatedly for one offer and preserves an audit trail.

## Recommended Interface

```swift
protocol RouteCorridorEngine {
    func evaluate(_ input: RouteCorridorEngineInput) -> RouteCorridorEngineOutput
}
```

Supporting collaborators:

```swift
protocol RouteProvider {
    func buildRoute(
        from pickup: CLLocationCoordinate2D,
        to dropoff: CLLocationCoordinate2D
    ) async throws -> RouteGeometry
}

protocol BeaconGeometryIndex {
    func queryCorridorHits(
        polyline: [CLLocationCoordinate2D],
        widthMeters: Double,
        weekday: Int,
        weekpart: Weekpart,
        timeBucket: TimeBucket
    ) -> BeaconIntersectionResult
}
```

## Minimum Useful Native Version

The first useful corridor engine only needs to do these well:

1. build corridor between pickup and dropoff
2. count exact and near beacon hits
3. count timed hits
4. return `RED xN / AMBER xN / GREEN x0`
5. persist the result

That alone upgrades the app from endpoint scoring to route scoring.
