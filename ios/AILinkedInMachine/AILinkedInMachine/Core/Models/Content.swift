import Foundation

struct ContentBankItem: Codable, Sendable, Identifiable {
    var id: Int { itemId }
    let itemId: Int
    let category: String
    let postType: String
    let draft: String
    let safetyFlag: Int
    let ready: Bool
    let lastUsed: String?
    let notes: String?
}

struct ContentBankItemCreate: Codable, Sendable {
    let category: String
    let postType: String
    let draft: String
    let safetyFlag: Int
    let ready: Bool
    let notes: String?
}

struct ContentBankItemUpdate: Codable, Sendable {
    var category: String?
    var postType: String?
    var draft: String?
    var safetyFlag: Int?
    var ready: Bool?
    var notes: String?
}

struct RepostBankItem: Codable, Sendable, Identifiable {
    var id: Int { itemId }
    let itemId: Int
    let sourceName: String
    let sourceUrl: String
    let summary: String
    let commentaryPrompt: String
    let safetyFlag: Int
    let lastUsed: String?
    let notes: String?
}

struct RepostBankItemCreate: Codable, Sendable {
    let sourceName: String
    let sourceUrl: String
    let summary: String
    let commentaryPrompt: String
    let safetyFlag: Int
    let notes: String?
}
