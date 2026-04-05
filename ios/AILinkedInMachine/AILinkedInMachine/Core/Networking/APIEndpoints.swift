import Foundation

// MARK: - API Endpoint Definitions
// Extension on APIClient providing typed methods for every backend endpoint.
// Mirrors dashboard/src/lib/api.ts exactly.

extension APIClient {

    // MARK: - Engine

    func getEngine() async throws -> EngineControl {
        try await get("/engine")
    }

    func updateEngine(_ data: EngineUpdate) async throws -> EngineControl {
        try await put("/engine", body: data)
    }

    func getKillSwitch() async throws -> KillSwitchStatus {
        try await get("/kill-switch")
    }

    func activateKillSwitch() async throws -> KillSwitchStatus {
        try await post("/kill-switch/activate")
    }

    func deactivateKillSwitch() async throws -> KillSwitchStatus {
        try await post("/kill-switch/deactivate")
    }

    // MARK: - Schedule

    func getActivityWindows() async throws -> [ActivityWindow] {
        try await get("/schedule/windows")
    }

    func getScheduleConfigs() async throws -> [ScheduleConfig] {
        try await get("/schedule/configs")
    }

    func updateScheduleConfig(mode: String, data: ScheduleConfigUpdate) async throws -> ScheduleConfig {
        try await put("/schedule/configs/\(mode)", body: data)
    }

    func getWeeklyPlan() async throws -> [WeeklyPlanDay] {
        try await get("/schedule/weekly-plan")
    }

    // MARK: - Content

    func getContentBank() async throws -> [ContentBankItem] {
        try await get("/content/bank?ready_only=false")
    }

    func createContentItem(_ data: ContentBankItemCreate) async throws -> ContentBankItem {
        try await post("/content/bank", body: data)
    }

    func updateContentItem(id: Int, data: ContentBankItemUpdate) async throws -> ContentBankItem {
        try await put("/content/bank/\(id)", body: data)
    }

    func deleteContentItem(id: Int) async throws {
        let _: EmptyBody = try await delete("/content/bank/\(id)")
    }

    func getRepostBank() async throws -> [RepostBankItem] {
        try await get("/content/reposts")
    }

    func createRepostItem(_ data: RepostBankItemCreate) async throws -> RepostBankItem {
        try await post("/content/reposts", body: data)
    }

    // MARK: - Targets

    func getTargets(category: String? = nil) async throws -> [CommentTarget] {
        let path = category.map { "/targets?category=\($0)" } ?? "/targets"
        return try await get(path)
    }

    func createTarget(_ data: CommentTargetCreate) async throws -> CommentTarget {
        try await post("/targets", body: data)
    }

    func updateTarget(name: String, data: CommentTargetUpdate) async throws -> CommentTarget {
        try await put("/targets/\(name.urlEncoded)", body: data)
    }

    func deleteTarget(name: String) async throws {
        let _: EmptyBody = try await delete("/targets/\(name.urlEncoded)")
    }

    // MARK: - Templates

    func getTemplates(persona: String? = nil) async throws -> [CommentTemplate] {
        let path = persona.map { "/templates?persona=\($0)" } ?? "/templates"
        return try await get(path)
    }

    func createTemplate(_ data: CommentTemplateCreate) async throws -> CommentTemplate {
        try await post("/templates", body: data)
    }

    func deleteTemplate(id: String) async throws {
        let _: EmptyBody = try await delete("/templates/\(id)")
    }

    // MARK: - Rules

    func getReplyRules() async throws -> [ReplyRule] {
        try await get("/rules/reply")
    }

    func createReplyRule(_ data: ReplyRuleCreate) async throws -> ReplyRule {
        try await post("/rules/reply", body: data)
    }

    func deleteReplyRule(trigger: String) async throws {
        let _: EmptyBody = try await delete("/rules/reply/\(trigger.urlEncoded)")
    }

    func getSafetyTerms() async throws -> [SafetyTerm] {
        try await get("/rules/safety")
    }

    func createSafetyTerm(_ data: SafetyTerm) async throws -> SafetyTerm {
        try await post("/rules/safety", body: data)
    }

    func deleteSafetyTerm(term: String) async throws {
        let _: EmptyBody = try await delete("/rules/safety/\(term.urlEncoded)")
    }

    // MARK: - Personas

    func getPersonas() async throws -> [PersonaSummary] {
        try await get("/personas")
    }

    func getPersonaDetail(name: String) async throws -> PersonaDetail {
        try await get("/personas/\(name.urlEncoded)")
    }

    func updatePersona(name: String, data: PersonaUpdate) async throws -> PersonaSummary {
        try await put("/personas/\(name.urlEncoded)", body: data)
    }

    // MARK: - Analytics

    func getTodaySummary() async throws -> DailySummary {
        try await get("/analytics/today")
    }

    func getTrends(days: Int = 30) async throws -> [EngagementTrend] {
        try await get("/analytics/trends?days=\(days)")
    }

    func getPersonaAnalytics(days: Int = 30) async throws -> [PersonaStats] {
        try await get("/analytics/personas?days=\(days)")
    }

    // MARK: - History

    func getHistory(limit: Int = 50, offset: Int = 0, action: String? = nil, module: String? = nil) async throws -> HistoryResponse {
        var params = "limit=\(limit)&offset=\(offset)"
        if let action { params += "&action=\(action)" }
        if let module { params += "&module=\(module)" }
        return try await get("/history?\(params)")
    }

    // MARK: - Alerts

    func getAlerts(limit: Int = 20) async throws -> [EngagementAlert] {
        try await get("/alerts?limit=\(limit)")
    }

    func markAlertResponded(id: String) async throws {
        try await post("/alerts/\(id)/respond")
    }

    func dismissAlert(id: String) async throws {
        try await post("/alerts/\(id)/dismiss")
    }

    // MARK: - Queue

    func getQueue(status: String? = nil, limit: Int = 50, offset: Int = 0) async throws -> QueueResponse {
        var params = "limit=\(limit)&offset=\(offset)"
        if let status { params += "&status=\(status)" }
        return try await get("/queue?\(params)")
    }

    func getQueueStats() async throws -> QueueStats {
        try await get("/queue/stats")
    }

    func updateQueueItem(id: Int, data: QueueItemUpdate) async throws -> QueueItem {
        try await put("/queue/\(id)", body: data)
    }

    func createQueueItem(_ data: QueueItemCreate) async throws -> QueueItem {
        try await post("/queue", body: data)
    }

    // MARK: - Pipeline

    func getPipelineRuns(limit: Int = 20, offset: Int = 0) async throws -> PipelineRunsResponse {
        try await get("/pipeline/runs?limit=\(limit)&offset=\(offset)")
    }

    func getPipelineRun(id: Int) async throws -> PipelineRun {
        try await get("/pipeline/runs/\(id)")
    }

    func triggerPipelineRun(dryRun: Bool = false) async throws -> PipelineTriggerResponse {
        try await post("/pipeline/run", body: PipelineTriggerRequest(triggerType: "manual", dryRun: dryRun))
    }

    func getPipelineErrors(limit: Int = 20, offset: Int = 0) async throws -> ErrorsResponse {
        try await get("/pipeline/errors?limit=\(limit)&offset=\(offset)")
    }

    // MARK: - Feeds

    func getFeeds(activeOnly: Bool = false) async throws -> FeedsResponse {
        try await get("/feeds?active_only=\(activeOnly)")
    }

    func createFeed(_ data: FeedCreate) async throws -> FeedSource {
        try await post("/feeds", body: data)
    }

    func updateFeed(id: Int, data: FeedUpdate) async throws -> FeedSource {
        try await put("/feeds/\(id)", body: data)
    }

    func deleteFeed(id: Int) async throws {
        let _: EmptyBody = try await delete("/feeds/\(id)")
    }

    // MARK: - Heartbeat

    func getHeartbeatStatus() async throws -> [PersonaHeartbeatStatus] {
        try await get("/heartbeat/status")
    }

    func getPersonaSchedule(name: String) async throws -> PersonaScheduleDetail {
        try await get("/heartbeat/schedule/\(name.urlEncoded)")
    }

    func updatePersonaSchedule(name: String, data: ScheduleUpdate) async throws -> PersonaScheduleDetail {
        try await put("/heartbeat/schedule/\(name.urlEncoded)", body: data)
    }

    func triggerHeartbeat(name: String, dryRun: Bool = false) async throws -> HeartbeatTriggerResponse {
        try await post("/heartbeat/run/\(name.urlEncoded)", body: HeartbeatTriggerRequest(dryRun: dryRun))
    }

    func triggerAllHeartbeats(dryRun: Bool = false) async throws -> AllHeartbeatTriggerResponse {
        try await post("/heartbeat/run-all", body: HeartbeatTriggerRequest(dryRun: dryRun))
    }

    // MARK: - Leads

    func getLeads(status: String? = nil) async throws -> LeadsResponse {
        let path = status.map { "/leads?status=\($0)" } ?? "/leads"
        return try await get(path)
    }

    func updateLead(name: String, data: LeadUpdate) async throws -> Lead {
        try await put("/leads/\(name.urlEncoded)", body: data)
    }

    func deleteLead(name: String) async throws {
        let _: EmptyBody = try await delete("/leads/\(name.urlEncoded)")
    }

    // MARK: - Connector

    func getConnectorStatus() async throws -> ConnectorStatus {
        try await get("/connector/status")
    }

    func getConnectionRequests(source: String? = nil, limit: Int = 50, offset: Int = 0) async throws -> ConnectionRequestsResponse {
        var params = "limit=\(limit)&offset=\(offset)"
        if let source { params += "&source=\(source)" }
        return try await get("/connector/requests?\(params)")
    }

    func triggerConnector(dryRun: Bool = false) async throws -> ConnectorTriggerResponse {
        try await post("/connector/run", body: ConnectorTriggerRequest(dryRun: dryRun))
    }

    func getVoiceQueue() async throws -> VoiceQueueResponse {
        try await get("/connector/voice-queue")
    }

    // MARK: - DM Responder

    func getDmResponderStatus() async throws -> DmResponderStatus {
        try await get("/dm-responder/status")
    }

    func getDmReplies(limit: Int = 50, offset: Int = 0) async throws -> DmRepliesResponse {
        try await get("/dm-responder/replies?limit=\(limit)&offset=\(offset)")
    }

    func getDmQueue() async throws -> DmQueueResponse {
        try await get("/dm-responder/queue")
    }

    func triggerDmResponder(dryRun: Bool = false, maxReplies: Int? = nil) async throws -> DmTriggerResponse {
        try await post("/dm-responder/run", body: DmTriggerRequest(dryRun: dryRun, maxReplies: maxReplies))
    }

    // MARK: - Health

    func healthCheck() async throws -> HealthStatus {
        try await get("/health")
    }
}

// MARK: - Helpers

private struct EmptyBody: Decodable {}

extension String {
    var urlEncoded: String {
        addingPercentEncoding(withAllowedCharacters: .urlPathAllowed) ?? self
    }
}
