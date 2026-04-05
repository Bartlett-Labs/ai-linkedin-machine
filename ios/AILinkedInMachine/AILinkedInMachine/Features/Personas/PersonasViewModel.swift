import SwiftUI

@Observable
final class PersonasViewModel {
    var heartbeats: [PersonaHeartbeatStatus] = []
    var personas: [PersonaSummary] = []
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
            async let h = api.getHeartbeatStatus()
            async let p = api.getPersonas()
            heartbeats = try await h
            personas = try await p
        } catch {
            self.error = error
        }
        isLoading = false
    }

    @MainActor
    func triggerHeartbeat(name: String) async {
        guard let api = apiClient else { return }
        do {
            _ = try await api.triggerHeartbeat(name: name)
            await load()
        } catch {
            self.error = error
        }
    }

    @MainActor
    func triggerAll() async {
        guard let api = apiClient else { return }
        do {
            _ = try await api.triggerAllHeartbeats()
            await load()
        } catch {
            self.error = error
        }
    }
}
