import Foundation

struct Lead: Codable, Sendable, Identifiable {
    var id: String { name }
    let name: String
    let title: String
    let company: String
    let score: Int
    let reasons: [String]
    let sourceUrl: String
    let interactionType: String
    let commentPreview: String
    let discoveredAt: String
    let status: String
    let interactionCount: Int
    let lastSeen: String?
    let notes: String?
}

struct LeadsResponse: Codable, Sendable {
    let leads: [Lead]
    let total: Int
}

struct LeadUpdate: Codable, Sendable {
    var status: String?
    var notes: String?
}
