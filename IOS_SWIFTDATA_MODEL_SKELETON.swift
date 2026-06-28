import Foundation
import SwiftData

// Build intent:
// - SwiftData-first native model layer
// - route truth stays immutable after ingest
// - lifecycle changes append events instead of silently overwriting history

enum OfferLifecycleState: String, Codable {
    case idle
    case offered
    case armed
    case movingToPickup
    case pickupReached
    case enRoute
    case completed
    case expired
    case declined
    case cancelled
    case ambiguous
}

enum DecisionVerdict: String, Codable {
    case accept
    case decline
    case review
}

enum BeaconStatus: String, Codable {
    case traffic
    case noTraffic
}

enum TimeBucket: String, Codable {
    case overnight
    case morning
    case midday
    case afternoon
    case evening
    case lateNight
}

enum Weekpart: String, Codable {
    case weekday
    case weekend
}

enum PayStatus: String, Codable {
    case good
    case low
    case bad
}

enum PickupStatus: String, Codable {
    case close
    case slightlyFar
    case tooFar
}

enum OperatorRuleType: String, Codable {
    case exactRoad
    case corridor
    case outcode
    case sector
    case timeScopedArea
    case routeRule
}

@Model
final class Offer {
    @Attribute(.unique) var id: UUID
    var createdAt: Date
    var source: String
    var shortcutSourceTag: String?
    var rawOCRText: String
    var ocrSHA1: String?

    // Route truth from ingest.
    var pickupAddress: String
    var dropoffAddress: String
    var pickupPostcode: String?
    var dropoffPostcode: String?
    var pickupOutcode: String?
    var dropoffOutcode: String?
    var pickupSector: String?
    var dropoffSector: String?

    var pickupLatitudeHint: Double?
    var pickupLongitudeHint: Double?
    var dropoffLatitudeHint: Double?
    var dropoffLongitudeHint: Double?

    var pickupMinutes: Double
    var pickupMiles: Double
    var tripMinutes: Double
    var tripMiles: Double
    var shownFareGBP: Double
    var rating: Double
    var vehicleType: String
    var surgeText: String?
    var isReserved: Bool
    var parseValid: Bool
    var parseError: String?
    var currentLifecycleStateRaw: String

    @Relationship(deleteRule: .cascade, inverse: \DecisionSnapshot.offer)
    var decisionSnapshots: [DecisionSnapshot]

    @Relationship(deleteRule: .cascade, inverse: \StateTransitionEvent.offer)
    var stateTransitions: [StateTransitionEvent]

    @Relationship(deleteRule: .cascade, inverse: \RouteEvidence.offer)
    var routeEvidence: RouteEvidence?

    @Relationship(deleteRule: .cascade, inverse: \TripOutcome.offer)
    var tripOutcome: TripOutcome?

    init(
        id: UUID = UUID(),
        createdAt: Date = .now,
        source: String,
        shortcutSourceTag: String? = nil,
        rawOCRText: String,
        ocrSHA1: String? = nil,
        pickupAddress: String,
        dropoffAddress: String,
        pickupPostcode: String? = nil,
        dropoffPostcode: String? = nil,
        pickupOutcode: String? = nil,
        dropoffOutcode: String? = nil,
        pickupSector: String? = nil,
        dropoffSector: String? = nil,
        pickupLatitudeHint: Double? = nil,
        pickupLongitudeHint: Double? = nil,
        dropoffLatitudeHint: Double? = nil,
        dropoffLongitudeHint: Double? = nil,
        pickupMinutes: Double,
        pickupMiles: Double,
        tripMinutes: Double,
        tripMiles: Double,
        shownFareGBP: Double,
        rating: Double,
        vehicleType: String,
        surgeText: String? = nil,
        isReserved: Bool,
        parseValid: Bool,
        parseError: String? = nil,
        currentLifecycleState: OfferLifecycleState = .offered
    ) {
        self.id = id
        self.createdAt = createdAt
        self.source = source
        self.shortcutSourceTag = shortcutSourceTag
        self.rawOCRText = rawOCRText
        self.ocrSHA1 = ocrSHA1
        self.pickupAddress = pickupAddress
        self.dropoffAddress = dropoffAddress
        self.pickupPostcode = pickupPostcode
        self.dropoffPostcode = dropoffPostcode
        self.pickupOutcode = pickupOutcode
        self.dropoffOutcode = dropoffOutcode
        self.pickupSector = pickupSector
        self.dropoffSector = dropoffSector
        self.pickupLatitudeHint = pickupLatitudeHint
        self.pickupLongitudeHint = pickupLongitudeHint
        self.dropoffLatitudeHint = dropoffLatitudeHint
        self.dropoffLongitudeHint = dropoffLongitudeHint
        self.pickupMinutes = pickupMinutes
        self.pickupMiles = pickupMiles
        self.tripMinutes = tripMinutes
        self.tripMiles = tripMiles
        self.shownFareGBP = shownFareGBP
        self.rating = rating
        self.vehicleType = vehicleType
        self.surgeText = surgeText
        self.isReserved = isReserved
        self.parseValid = parseValid
        self.parseError = parseError
        self.currentLifecycleStateRaw = currentLifecycleState.rawValue
        self.decisionSnapshots = []
        self.stateTransitions = []
    }
}

@Model
final class DecisionSnapshot {
    @Attribute(.unique) var id: UUID
    var createdAt: Date
    var verdictRaw: String
    var trafficStatus: String
    var trafficLabel: String?
    var trafficReason: String?
    var routeTrapCount: Int
    var timedRouteTrapCount: Int
    var nearRouteTrapCount: Int
    var routeTrapScore: Double
    var perMinuteAdjustedGBP: Double
    var perMileIncludingPickupGBP: Double
    var hourlyAdjustedGBP: Double
    var payStatusRaw: String
    var pickupStatusRaw: String
    var reasonSummary: String?
    var reasonCodes: [String]
    var operatorOverrideApplied: Bool
    var operatorOverrideName: String?
    var confidence: Double?

    var offer: Offer?

    init(
        id: UUID = UUID(),
        createdAt: Date = .now,
        verdict: DecisionVerdict,
        trafficStatus: String,
        trafficLabel: String? = nil,
        trafficReason: String? = nil,
        routeTrapCount: Int,
        timedRouteTrapCount: Int,
        nearRouteTrapCount: Int,
        routeTrapScore: Double,
        perMinuteAdjustedGBP: Double,
        perMileIncludingPickupGBP: Double,
        hourlyAdjustedGBP: Double,
        payStatus: PayStatus,
        pickupStatus: PickupStatus,
        reasonSummary: String? = nil,
        reasonCodes: [String] = [],
        operatorOverrideApplied: Bool = false,
        operatorOverrideName: String? = nil,
        confidence: Double? = nil
    ) {
        self.id = id
        self.createdAt = createdAt
        self.verdictRaw = verdict.rawValue
        self.trafficStatus = trafficStatus
        self.trafficLabel = trafficLabel
        self.trafficReason = trafficReason
        self.routeTrapCount = routeTrapCount
        self.timedRouteTrapCount = timedRouteTrapCount
        self.nearRouteTrapCount = nearRouteTrapCount
        self.routeTrapScore = routeTrapScore
        self.perMinuteAdjustedGBP = perMinuteAdjustedGBP
        self.perMileIncludingPickupGBP = perMileIncludingPickupGBP
        self.hourlyAdjustedGBP = hourlyAdjustedGBP
        self.payStatusRaw = payStatus.rawValue
        self.pickupStatusRaw = pickupStatus.rawValue
        self.reasonSummary = reasonSummary
        self.reasonCodes = reasonCodes
        self.operatorOverrideApplied = operatorOverrideApplied
        self.operatorOverrideName = operatorOverrideName
        self.confidence = confidence
    }
}

@Model
final class TripOutcome {
    @Attribute(.unique) var id: UUID
    var finalStateRaw: String
    var acceptedInferenceConfidence: Double
    var completedInferenceConfidence: Double
    var startedAt: Date?
    var pickupReachedAt: Date?
    var enRouteAt: Date?
    var completedAt: Date?
    var finalizedAt: Date
    var routeProgressMax: Double?
    var pickupDistanceReductionMeters: Double?
    var dropoffArrivalDistanceMeters: Double?
    var movementSummary: String?
    var reasonCodes: [String]
    var manualOverrideState: String?
    var manualOverrideNote: String?
    var finalFareGBP: Double?
    var tipGBP: Double?
    var actualMinutes: Double?
    var actualMiles: Double?

    var offer: Offer?

    init(
        id: UUID = UUID(),
        finalState: OfferLifecycleState,
        acceptedInferenceConfidence: Double,
        completedInferenceConfidence: Double,
        finalizedAt: Date = .now,
        reasonCodes: [String] = []
    ) {
        self.id = id
        self.finalStateRaw = finalState.rawValue
        self.acceptedInferenceConfidence = acceptedInferenceConfidence
        self.completedInferenceConfidence = completedInferenceConfidence
        self.finalizedAt = finalizedAt
        self.reasonCodes = reasonCodes
    }
}

@Model
final class StateTransitionEvent {
    @Attribute(.unique) var id: UUID
    var timestamp: Date
    var fromStateRaw: String
    var toStateRaw: String
    var reasonCodes: [String]
    var pickupDistanceMeters: Double?
    var dropoffDistanceMeters: Double?
    var routeProgress: Double?
    var speedMPS: Double?
    var headingDegrees: Double?
    var confidence: Double?
    var note: String?

    var offer: Offer?

    init(
        id: UUID = UUID(),
        timestamp: Date = .now,
        fromState: OfferLifecycleState,
        toState: OfferLifecycleState,
        reasonCodes: [String] = [],
        pickupDistanceMeters: Double? = nil,
        dropoffDistanceMeters: Double? = nil,
        routeProgress: Double? = nil,
        speedMPS: Double? = nil,
        headingDegrees: Double? = nil,
        confidence: Double? = nil,
        note: String? = nil
    ) {
        self.id = id
        self.timestamp = timestamp
        self.fromStateRaw = fromState.rawValue
        self.toStateRaw = toState.rawValue
        self.reasonCodes = reasonCodes
        self.pickupDistanceMeters = pickupDistanceMeters
        self.dropoffDistanceMeters = dropoffDistanceMeters
        self.routeProgress = routeProgress
        self.speedMPS = speedMPS
        self.headingDegrees = headingDegrees
        self.confidence = confidence
        self.note = note
    }
}

@Model
final class BeaconEvent {
    @Attribute(.unique) var id: UUID
    var timestamp: Date
    var statusRaw: String
    var address: String
    var postcode: String?
    var outcode: String?
    var sector: String?
    var latitude: Double
    var longitude: Double
    var horizontalAccuracy: Double?
    var speedMPS: Double?
    var courseDegrees: Double?
    var weekday: Int
    var weekpartRaw: String
    var hour: Int
    var minute: Int
    var timeBucketRaw: String
    var fifteenMinuteWindow: String
    var source: String
    var lineGridCell: String?
    var corridorTag: String?

    var trackerSession: TrackerSession?

    init(
        id: UUID = UUID(),
        timestamp: Date = .now,
        status: BeaconStatus,
        address: String,
        postcode: String? = nil,
        outcode: String? = nil,
        sector: String? = nil,
        latitude: Double,
        longitude: Double,
        horizontalAccuracy: Double? = nil,
        speedMPS: Double? = nil,
        courseDegrees: Double? = nil,
        weekday: Int,
        weekpart: Weekpart,
        hour: Int,
        minute: Int,
        timeBucket: TimeBucket,
        fifteenMinuteWindow: String,
        source: String,
        lineGridCell: String? = nil,
        corridorTag: String? = nil
    ) {
        self.id = id
        self.timestamp = timestamp
        self.statusRaw = status.rawValue
        self.address = address
        self.postcode = postcode
        self.outcode = outcode
        self.sector = sector
        self.latitude = latitude
        self.longitude = longitude
        self.horizontalAccuracy = horizontalAccuracy
        self.speedMPS = speedMPS
        self.courseDegrees = courseDegrees
        self.weekday = weekday
        self.weekpartRaw = weekpart.rawValue
        self.hour = hour
        self.minute = minute
        self.timeBucketRaw = timeBucket.rawValue
        self.fifteenMinuteWindow = fifteenMinuteWindow
        self.source = source
        self.lineGridCell = lineGridCell
        self.corridorTag = corridorTag
    }
}

@Model
final class RouteEvidence {
    @Attribute(.unique) var id: UUID
    var computedAt: Date
    var routeMode: String
    var corridorWidthMeters: Double
    var exactHits: Int
    var nearHits: Int
    var timedHits: Int
    var weightedTrapScore: Double
    var operatorRuleHits: Int
    var primaryReason: String?
    var matchedOutcodes: [String]
    var matchedSectors: [String]
    var matchedBeaconIDs: [UUID]
    var routePolylineEncoded: String?
    var corridorBoundingBox: String?

    var offer: Offer?

    init(
        id: UUID = UUID(),
        computedAt: Date = .now,
        routeMode: String,
        corridorWidthMeters: Double,
        exactHits: Int,
        nearHits: Int,
        timedHits: Int,
        weightedTrapScore: Double,
        operatorRuleHits: Int = 0,
        primaryReason: String? = nil,
        matchedOutcodes: [String] = [],
        matchedSectors: [String] = [],
        matchedBeaconIDs: [UUID] = [],
        routePolylineEncoded: String? = nil,
        corridorBoundingBox: String? = nil
    ) {
        self.id = id
        self.computedAt = computedAt
        self.routeMode = routeMode
        self.corridorWidthMeters = corridorWidthMeters
        self.exactHits = exactHits
        self.nearHits = nearHits
        self.timedHits = timedHits
        self.weightedTrapScore = weightedTrapScore
        self.operatorRuleHits = operatorRuleHits
        self.primaryReason = primaryReason
        self.matchedOutcodes = matchedOutcodes
        self.matchedSectors = matchedSectors
        self.matchedBeaconIDs = matchedBeaconIDs
        self.routePolylineEncoded = routePolylineEncoded
        self.corridorBoundingBox = corridorBoundingBox
    }
}

@Model
final class OperatorRule {
    @Attribute(.unique) var id: UUID
    var createdAt: Date
    var updatedAt: Date
    var name: String
    var ruleTypeRaw: String
    var status: String
    var priority: Int
    var matchKeywords: [String]
    var matchOutcodes: [String]
    var matchSectors: [String]
    var timeBuckets: [String]
    var weekparts: [String]
    var reasonCode: String
    var note: String?
    var isEnabled: Bool

    init(
        id: UUID = UUID(),
        createdAt: Date = .now,
        updatedAt: Date = .now,
        name: String,
        ruleType: OperatorRuleType,
        status: String,
        priority: Int,
        matchKeywords: [String] = [],
        matchOutcodes: [String] = [],
        matchSectors: [String] = [],
        timeBuckets: [String] = [],
        weekparts: [String] = [],
        reasonCode: String,
        note: String? = nil,
        isEnabled: Bool = true
    ) {
        self.id = id
        self.createdAt = createdAt
        self.updatedAt = updatedAt
        self.name = name
        self.ruleTypeRaw = ruleType.rawValue
        self.status = status
        self.priority = priority
        self.matchKeywords = matchKeywords
        self.matchOutcodes = matchOutcodes
        self.matchSectors = matchSectors
        self.timeBuckets = timeBuckets
        self.weekparts = weekparts
        self.reasonCode = reasonCode
        self.note = note
        self.isEnabled = isEnabled
    }
}

@Model
final class TrackerSession {
    @Attribute(.unique) var id: UUID
    var startedAt: Date
    var endedAt: Date?
    var state: String
    var deviceStateSummary: String?
    var batteryAtStart: Double?
    var batteryAtEnd: Double?
    var lowPowerModeAtStart: Bool
    var thermalStateAtStart: String?

    @Relationship(deleteRule: .nullify, inverse: \BeaconEvent.trackerSession)
    var beaconEvents: [BeaconEvent]

    init(
        id: UUID = UUID(),
        startedAt: Date = .now,
        endedAt: Date? = nil,
        state: String,
        deviceStateSummary: String? = nil,
        batteryAtStart: Double? = nil,
        batteryAtEnd: Double? = nil,
        lowPowerModeAtStart: Bool = false,
        thermalStateAtStart: String? = nil
    ) {
        self.id = id
        self.startedAt = startedAt
        self.endedAt = endedAt
        self.state = state
        self.deviceStateSummary = deviceStateSummary
        self.batteryAtStart = batteryAtStart
        self.batteryAtEnd = batteryAtEnd
        self.lowPowerModeAtStart = lowPowerModeAtStart
        self.thermalStateAtStart = thermalStateAtStart
        self.beaconEvents = []
    }
}
