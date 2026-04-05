import Foundation

struct DailySummary: Codable, Sendable {
    let date: String
    let commentsPosted: Int
    let postsMade: Int
    let repliesSent: Int
    let likesGiven: Int
    let lastActionTime: String?
}

struct EngagementTrend: Codable, Sendable, Identifiable {
    var id: String { date }
    let date: String
    let comments: Int
    let posts: Int
    let replies: Int
    let likes: Int
}

struct PersonaStats: Codable, Sendable, Identifiable {
    var id: String { persona }
    let persona: String
    let totalActions: Int
    let comments: Int
    let posts: Int
    let replies: Int
}
