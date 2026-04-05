import Foundation

struct EngagementAlert: Codable, Sendable, Identifiable {
    var id: String { alertId }
    let alertId: String
    let commenterName: String
    let commenterUrl: String
    let commentText: String
    let postUrl: String
    let postTitle: String
    let discoveredAt: String
    let elapsedMinutes: Int
    let urgency: String
    let responded: Bool
}
