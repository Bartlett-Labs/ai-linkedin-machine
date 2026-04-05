import SwiftUI

@Observable
final class LeadsViewModel {
    var leads: [Lead] = []
    var total = 0
    var isLoading = false
    var error: Error?

    private var apiClient: APIClient?

    func bind(_ client: APIClient) {
        self.apiClient = client
    }

    @MainActor
    func load(status: String? = nil) async {
        guard let api = apiClient else { return }
        isLoading = true
        error = nil
        do {
            let response = try await api.getLeads(status: status)
            leads = response.leads
            total = response.total
        } catch {
            self.error = error
        }
        isLoading = false
    }
}
