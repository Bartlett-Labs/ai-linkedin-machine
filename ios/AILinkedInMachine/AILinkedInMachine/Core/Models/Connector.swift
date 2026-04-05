import Foundation

struct ConnectorStatus: Codable, Sendable {
    let sentToday: Int
    let dailyLimit: Int
    let remaining: Int
    let commenterToday: Int
    let outboundToday: Int
    let acceptedToday: Int
    let totalAccepted: Int
    let totalAllTime: Int
    let config: ConnectorConfig
}

struct ConnectorConfig: Codable, Sendable {
    let commenterPriority: Bool
    let searchKeywords: [String]
    let location: String
}

struct ConnectionRequest: Codable, Sendable, Identifiable {
    var id: String { "\(name)-\(timestamp)" }
    let name: String
    let profileUrl: String
    let headline: String
    let note: String
    let source: String
    let searchKeyword: String?
    let postContext: String?
    let relevanceScore: Double?
    let timestamp: String
    let dryRun: Bool
}

struct ConnectionRequestsResponse: Codable, Sendable {
    let requests: [ConnectionRequest]
    let total: Int
    let limit: Int
    let offset: Int
}

struct ConnectorTriggerRequest: Codable, Sendable {
    let dryRun: Bool
}

struct ConnectorTriggerResponse: Codable, Sendable {
    let status: String
    let dryRun: Bool
}

struct VoiceRecord: Codable, Sendable, Identifiable {
    var id: String { "\(name)-\(timestamp)" }
    let name: String
    let profileUrl: String
    let script: String
    let audioFile: String?
    let timestamp: String
    let dryRun: Bool
}

struct VoiceQueuePending: Codable, Sendable, Identifiable {
    var id: String { "\(name)-\(sentAt)" }
    let name: String
    let profileUrl: String
    let headline: String
    let source: String
    let sentAt: String
}

struct VoiceQueueResponse: Codable, Sendable {
    let pending: [VoiceQueuePending]
    let sent: [VoiceRecord]
    let totalSent: Int
}
