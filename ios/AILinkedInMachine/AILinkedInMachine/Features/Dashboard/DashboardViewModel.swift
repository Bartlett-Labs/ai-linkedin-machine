import SwiftUI

@Observable
final class DashboardViewModel {
    var todaySummary: DailySummary?
    var engineControl: EngineControl?
    var killSwitch: KillSwitchStatus?
    var queueStats: QueueStats?
    var latestRun: PipelineRun?
    var heartbeatStatus: [PersonaHeartbeatStatus] = []
    var isLoading = false
    var error: Error?

    private var apiClient: APIClient?

    func bind(_ client: APIClient) {
        self.apiClient = client
    }

    @MainActor
    func loadAll() async {
        guard let api = apiClient else { return }
        isLoading = true
        error = nil

        do {
            async let summary = api.getTodaySummary()
            async let engine = api.getEngine()
            async let kill = api.getKillSwitch()
            async let stats = api.getQueueStats()
            async let runs = api.getPipelineRuns(limit: 1)
            async let heartbeats = api.getHeartbeatStatus()

            todaySummary = try await summary
            engineControl = try await engine
            killSwitch = try await kill
            queueStats = try await stats
            let runsResponse = try await runs
            latestRun = runsResponse.runs.first
            heartbeatStatus = try await heartbeats
        } catch {
            self.error = error
        }

        isLoading = false
    }

    @MainActor
    func toggleKillSwitch() async {
        guard let api = apiClient, let current = killSwitch else { return }
        do {
            if current.active {
                killSwitch = try await api.deactivateKillSwitch()
            } else {
                killSwitch = try await api.activateKillSwitch()
            }
        } catch {
            self.error = error
        }
    }

    @MainActor
    func triggerPipeline(dryRun: Bool = false) async {
        guard let api = apiClient else { return }
        do {
            _ = try await api.triggerPipelineRun(dryRun: dryRun)
            await loadAll()
        } catch {
            self.error = error
        }
    }

    @MainActor
    func triggerAllHeartbeats(dryRun: Bool = false) async {
        guard let api = apiClient else { return }
        do {
            _ = try await api.triggerAllHeartbeats(dryRun: dryRun)
            await loadAll()
        } catch {
            self.error = error
        }
    }

    var totalActionsToday: Int {
        guard let s = todaySummary else { return 0 }
        return s.commentsPosted + s.postsMade + s.repliesSent + s.likesGiven
    }

    var activePersonaCount: Int {
        heartbeatStatus.filter { $0.inActiveHours }.count
    }

    var runningPersonaCount: Int {
        heartbeatStatus.filter { $0.isRunning }.count
    }
}
