import Foundation

struct PersonaSummary: Codable, Sendable, Identifiable {
    var id: String { name }
    let name: String
    let displayName: String
    let persona: String
    let location: String?
    let activeHours: [String: String]?
    let behavior: [String: AnyCodable]?
}

struct PersonaDetail: Codable, Sendable, Identifiable {
    var id: String { name }
    let name: String
    let displayName: String
    let persona: String
    let systemPrompt: String
    let sessionDir: String
    let location: String?
    let linkedinUrl: String?
    let activeHours: [String: String]?
    let voice: [String: AnyCodable]?
    let engagementRules: [String: AnyCodable]?
    let behavior: [String: AnyCodable]?
}

struct PersonaUpdate: Codable, Sendable {
    var displayName: String?
    var location: String?
    var behavior: [String: AnyCodable]?
}

struct PersonaHeartbeatStatus: Codable, Sendable, Identifiable {
    var id: String { name }
    let name: String
    let displayName: String
    let hasActiveSession: Bool
    let inActiveHours: Bool
    let activeHours: [String: String]?
    let schedule: [String: AnyCodable]?
    let dailyStats: [String: AnyCodable]?
    let isRunning: Bool
}

struct PersonaScheduleDetail: Codable, Sendable {
    let name: String
    let displayName: String
    let schedule: [String: AnyCodable]
    let activeHours: [String: String]
    let behavior: [String: AnyCodable]
}

struct ScheduleUpdate: Codable, Sendable {
    var commentsPerCycle: Int?
    var postChancePerCycle: Double?
    var kyleCommentChance: Double?
    var cycleIntervalMinutes: Int?
}

struct HeartbeatTriggerRequest: Codable, Sendable {
    let dryRun: Bool
}

struct HeartbeatTriggerResponse: Codable, Sendable {
    let status: String
    let persona: String
    let displayName: String
    let dryRun: Bool
}

struct AllHeartbeatTriggerResponse: Codable, Sendable {
    let status: String
    let triggered: [HeartbeatPersonaRef]
    let skipped: [HeartbeatSkippedRef]
    let dryRun: Bool
}

struct HeartbeatPersonaRef: Codable, Sendable {
    let name: String
    let displayName: String
}

struct HeartbeatSkippedRef: Codable, Sendable {
    let name: String
    let displayName: String
    let reason: String
}
