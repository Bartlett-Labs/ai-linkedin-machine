import Foundation

struct QueueItem: Codable, Sendable, Identifiable {
    let id: Int
    let createdAt: String?
    let postId: String
    let actionType: String
    let persona: String
    let targetName: String
    let targetUrl: String
    let draftText: String
    let status: String
    let scheduledTime: String?
    let executedAt: String?
    let notes: String
}

struct QueueResponse: Codable, Sendable {
    let items: [QueueItem]
    let total: Int
    let limit: Int
    let offset: Int
}

struct QueueStats: Codable, Sendable {
    let total: Int
    let ready: Int?
    let inProgress: Int?
    let done: Int?
    let failed: Int?
    let skipped: Int?

    private enum CodingKeys: String, CodingKey {
        case total
        case ready = "READY"
        case inProgress = "IN_PROGRESS"
        case done = "DONE"
        case failed = "FAILED"
        case skipped = "SKIPPED"
    }
}

struct QueueItemUpdate: Codable, Sendable {
    var status: String?
    var draftText: String?
    var notes: String?
}

struct QueueItemCreate: Codable, Sendable {
    var postId: String?
    var persona: String?
    let draftText: String
    var actionType: String?
    var targetUrl: String?
    var notes: String?
}
