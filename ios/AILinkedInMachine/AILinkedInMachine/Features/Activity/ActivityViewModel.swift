import SwiftUI

@Observable
final class ActivityViewModel {
    var trends: [EngagementTrend] = []
    var personaStats: [PersonaStats] = []
    var history: [HistoryEntry] = []
    var historyTotal = 0
    var runs: [PipelineRun] = []
    var pipelineErrors: [PipelineError] = []
    var systemErrors: [PipelineError] = []
    var isLoading = false
    var error: Error?

    private var apiClient: APIClient?

    func bind(_ client: APIClient) {
        self.apiClient = client
    }

    @MainActor
    func loadAnalytics() async {
        guard let api = apiClient else { return }
        isLoading = true
        error = nil
        do {
            async let t = api.getTrends(days: 30)
            async let p = api.getPersonaAnalytics(days: 30)
            trends = try await t
            personaStats = try await p
        } catch {
            self.error = error
        }
        isLoading = false
    }

    @MainActor
    func loadHistory() async {
        guard let api = apiClient else { return }
        isLoading = true
        error = nil
        do {
            let response = try await api.getHistory(limit: 100)
            history = response.entries
            historyTotal = response.total
        } catch {
            self.error = error
        }
        isLoading = false
    }

    @MainActor
    func loadRuns() async {
        guard let api = apiClient else { return }
        isLoading = true
        error = nil
        do {
            let response = try await api.getPipelineRuns(limit: 50)
            runs = response.runs
        } catch {
            self.error = error
        }
        isLoading = false
    }

    @MainActor
    func loadErrors() async {
        guard let api = apiClient else { return }
        isLoading = true
        error = nil
        do {
            let response = try await api.getPipelineErrors(limit: 50)
            pipelineErrors = response.pipelineErrors
            systemErrors = response.systemErrors
        } catch {
            self.error = error
        }
        isLoading = false
    }
}
