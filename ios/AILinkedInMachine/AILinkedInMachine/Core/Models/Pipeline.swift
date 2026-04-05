import Foundation

struct PipelineRun: Codable, Sendable, Identifiable {
    let id: Int
    let startedAt: String?
    let completedAt: String?
    let triggerType: String
    let status: String
    let phase: String
    let postsMade: Int
    let commentsMade: Int
    let repliesMade: Int
    let phantomActions: Int
    let errors: [String: AnyCodable]?
    let summary: String
}

struct PipelineRunsResponse: Codable, Sendable {
    let runs: [PipelineRun]
    let total: Int
    let limit: Int
    let offset: Int
}

struct PipelineError: Codable, Sendable, Identifiable {
    var id: String { "\(source)-\(timestamp ?? "unknown")" }
    let source: String
    let runId: Int?
    let logId: Int?
    let timestamp: String?
    let phase: String?
    let status: String?
    let errors: [String: AnyCodable]?
    let summary: String?
    let module: String?
    let action: String?
    let target: String?
    let result: String?
    let notes: String?
}

struct ErrorsResponse: Codable, Sendable {
    let pipelineErrors: [PipelineError]
    let systemErrors: [PipelineError]
    let pipelineErrorCount: Int
    let systemErrorCount: Int
}

struct PipelineTriggerRequest: Codable, Sendable {
    let triggerType: String
    let dryRun: Bool
}

struct PipelineTriggerResponse: Codable, Sendable {
    let status: String
    let runId: Int
    let phase: String
    let mode: String
    let dryRun: Bool
}

// Generic JSON value wrapper for untyped dictionaries
struct AnyCodable: Codable, Sendable {
    let value: Any

    init(_ value: Any) {
        self.value = value
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.singleValueContainer()
        if let string = try? container.decode(String.self) {
            value = string
        } else if let int = try? container.decode(Int.self) {
            value = int
        } else if let double = try? container.decode(Double.self) {
            value = double
        } else if let bool = try? container.decode(Bool.self) {
            value = bool
        } else {
            value = ""
        }
    }

    func encode(to encoder: Encoder) throws {
        var container = encoder.singleValueContainer()
        if let string = value as? String {
            try container.encode(string)
        } else if let int = value as? Int {
            try container.encode(int)
        } else if let double = value as? Double {
            try container.encode(double)
        } else if let bool = value as? Bool {
            try container.encode(bool)
        }
    }
}
