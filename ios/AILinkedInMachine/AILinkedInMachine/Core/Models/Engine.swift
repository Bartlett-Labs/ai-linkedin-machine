import Foundation

struct EngineControl: Codable, Sendable {
    let mode: String
    let phase: String
    let mainUserPosting: Bool
    let phantomEngagement: Bool
    let commenting: Bool
    let replying: Bool
    let lastRun: String?
}

struct EngineUpdate: Codable, Sendable {
    var mode: String?
    var phase: String?
    var mainUserPosting: Bool?
    var phantomEngagement: Bool?
    var commenting: Bool?
    var replying: Bool?
}

struct KillSwitchStatus: Codable, Sendable {
    let active: Bool
    let message: String
}

struct HealthStatus: Codable, Sendable {
    let status: String
}
