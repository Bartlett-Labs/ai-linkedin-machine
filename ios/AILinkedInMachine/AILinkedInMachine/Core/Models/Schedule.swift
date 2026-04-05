import Foundation

struct ActivityWindow: Codable, Sendable, Identifiable {
    var id: String { windowName }
    let windowName: String
    let startHour: Int
    let endHour: Int
    let daysOfWeek: String
    let enabled: Bool
}

struct ScheduleConfig: Codable, Sendable, Identifiable {
    var id: String { mode }
    let mode: String
    let postsPerWeek: Int
    let commentsPerDayMin: Int
    let commentsPerDayMax: Int
    let phantomCommentsMin: Int
    let phantomCommentsMax: Int
    let minDelaySec: Int
    let maxLikesPerDay: Int
}

struct ScheduleConfigUpdate: Codable, Sendable {
    var postsPerWeek: Int?
    var commentsPerDayMin: Int?
    var commentsPerDayMax: Int?
    var phantomCommentsMin: Int?
    var phantomCommentsMax: Int?
    var minDelaySec: Int?
    var maxLikesPerDay: Int?
}

struct PlanAction: Codable, Sendable {
    let type: String
    let contentStream: String?
    let window: String?
    let targetCategory: String?
    let count: Int?
}

struct WeeklyPlanDay: Codable, Sendable, Identifiable {
    var id: String { date }
    let date: String
    let day: String
    let isPostDay: Bool
    let actions: [PlanAction]
}
