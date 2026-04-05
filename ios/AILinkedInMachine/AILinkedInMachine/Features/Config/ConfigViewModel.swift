import SwiftUI

// Shared config view model for config pages that need CRUD operations
@Observable
final class ConfigViewModel {
    var isLoading = false
    var error: Error?

    private var apiClient: APIClient?

    func bind(_ client: APIClient) {
        self.apiClient = client
    }

    var api: APIClient? { apiClient }
}
