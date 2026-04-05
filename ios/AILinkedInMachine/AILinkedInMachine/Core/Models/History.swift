import Foundation

struct HistoryEntry: Codable, Sendable, Identifiable {
    var id: String { "\(timestamp)-\(module)-\(action)" }
    let timestamp: String
    let module: String
    let action: String
    let target: String
    let result: String
    let safety: String
    let notes: String
}

struct HistoryResponse: Codable, Sendable {
    let entries: [HistoryEntry]
    let total: Int
    let limit: Int
    let offset: Int
}

struct CommentTarget: Codable, Sendable, Identifiable {
    var id: String { name }
    let name: String
    let linkedinUrl: String
    let category: String
    let priority: Int
    let lastCommentDate: String?
    let notes: String?
}

struct CommentTargetCreate: Codable, Sendable {
    let name: String
    let linkedinUrl: String
    let category: String
    let priority: Int
    let notes: String?
}

struct CommentTargetUpdate: Codable, Sendable {
    var name: String?
    var linkedinUrl: String?
    var category: String?
    var priority: Int?
    var notes: String?
}

struct CommentTemplate: Codable, Sendable, Identifiable {
    var id: String { templateId }
    let templateId: String
    let templateText: String
    let tone: String
    let category: String
    let safetyFlag: Int
    let exampleUse: String
    let persona: String
    let useCount: Int
}

struct CommentTemplateCreate: Codable, Sendable {
    let templateText: String
    let tone: String
    let category: String
    let persona: String
    let exampleUse: String
    let safetyFlag: Int
}

struct ReplyRule: Codable, Sendable, Identifiable {
    var id: String { trigger }
    let conditionType: String
    let trigger: String
    let action: String
    let notes: String?
}

struct ReplyRuleCreate: Codable, Sendable {
    let conditionType: String
    let trigger: String
    let action: String
    let notes: String?
}

struct SafetyTerm: Codable, Sendable, Identifiable {
    var id: String { term }
    let term: String
    let response: String
}
