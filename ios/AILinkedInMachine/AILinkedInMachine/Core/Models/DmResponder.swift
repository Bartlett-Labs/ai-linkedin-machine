import Foundation

struct DmResponderStatus: Codable, Sendable {
    let repliedToday: Int
    let dailyLimit: Int
    let queueDepth: Int
    let queue: [DmQueueEntry]
    let totalReplied: Int
    let recentReplies: [DmSentReply]
    let intentBreakdown: [String: Int]
}

struct DmQueueEntry: Codable, Sendable, Identifiable {
    var id: String { "\(sender)-\(threadIndex)" }
    let sender: String
    let profileUrl: String
    let threadIndex: Int
    let intent: String
    let replyText: String
    let lastIncomingText: String
    let queuedAt: String
    let sendAt: String
    let sent: Bool
}

struct DmSentReply: Codable, Sendable, Identifiable {
    var id: String { "\(sender)-\(sentAt)" }
    let sender: String
    let intent: String
    let replyText: String
    let sentAt: String
}

struct DmRepliesResponse: Codable, Sendable {
    let replies: [DmSentReply]
    let total: Int
    let limit: Int
    let offset: Int
}

struct DmQueueResponse: Codable, Sendable {
    let queue: [DmQueueEntry]
    let count: Int
}

struct DmTriggerRequest: Codable, Sendable {
    let dryRun: Bool
    let maxReplies: Int?
}

struct DmTriggerResponse: Codable, Sendable {
    let status: String
    let dryRun: Bool
}
