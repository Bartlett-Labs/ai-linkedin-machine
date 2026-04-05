import SwiftUI

@Observable
final class AlertsViewModel {
    var alerts: [EngagementAlert] = []
    var isLoading = false
    var error: Error?

    private var apiClient: APIClient?

    func bind(_ client: APIClient) {
        self.apiClient = client
    }

    @MainActor
    func load() async {
        guard let api = apiClient else { return }
        isLoading = true
        error = nil
        do {
            alerts = try await api.getAlerts(limit: 50)
        } catch {
            self.error = error
        }
        isLoading = false
    }

    @MainActor
    func markResponded(_ alert: EngagementAlert) async {
        guard let api = apiClient else { return }
        do {
            try await api.markAlertResponded(id: alert.alertId)
            await load()
        } catch {
            self.error = error
        }
    }

    @MainActor
    func dismiss(_ alert: EngagementAlert) async {
        guard let api = apiClient else { return }
        do {
            try await api.dismissAlert(id: alert.alertId)
            await load()
        } catch {
            self.error = error
        }
    }

    var unrespondedCount: Int {
        alerts.filter { !$0.responded }.count
    }
}
