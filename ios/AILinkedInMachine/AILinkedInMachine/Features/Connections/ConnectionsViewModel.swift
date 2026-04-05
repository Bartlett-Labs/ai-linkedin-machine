import SwiftUI

@Observable
final class ConnectionsViewModel {
    var status: ConnectorStatus?
    var requests: [ConnectionRequest] = []
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
            async let s = api.getConnectorStatus()
            async let r = api.getConnectionRequests()
            status = try await s
            requests = try await r.requests
        } catch {
            self.error = error
        }
        isLoading = false
    }
}
