import Foundation

struct FeedSource: Codable, Sendable, Identifiable {
    let id: Int
    let name: String
    let url: String
    let type: String
    let category: String
    let active: Bool
    let lastFetched: String?
    let createdAt: String?
}

struct FeedsResponse: Codable, Sendable {
    let feeds: [FeedSource]
    let total: Int
}

struct FeedCreate: Codable, Sendable {
    let name: String
    let url: String
    var type: String?
    var category: String?
    var active: Bool?
}

struct FeedUpdate: Codable, Sendable {
    var name: String?
    var url: String?
    var type: String?
    var category: String?
    var active: Bool?
}
