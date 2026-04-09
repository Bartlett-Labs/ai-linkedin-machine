import SwiftUI

@MainActor @Observable
final class QueueViewModel {
    var items: [QueueItem] = []
    var stats: QueueStats?
    var total = 0
    var isLoading = false
    var error: Error?
    var activeFilter: String? = nil

    private var apiClient: APIClient?

    func bind(_ client: APIClient) {
        self.apiClient = client
    }

    func load() async {
        guard let api = apiClient else { return }
        isLoading = true
        error = nil

        do {
            async let queueResult = api.getQueue(status: activeFilter, limit: 100)
            async let statsResult = api.getQueueStats()

            let response = try await queueResult
            items = response.items
            total = response.total
            stats = try await statsResult
        } catch {
            self.error = error
        }

        isLoading = false
    }

    func approve(_ item: QueueItem) async {
        guard let api = apiClient else { return }
        do {
            _ = try await api.updateQueueItem(id: item.id, data: QueueItemUpdate(status: "READY"))
            await load()
        } catch {
            self.error = error
        }
    }

    func reject(_ item: QueueItem) async {
        guard let api = apiClient else { return }
        do {
            _ = try await api.updateQueueItem(id: item.id, data: QueueItemUpdate(status: "SKIPPED"))
            await load()
        } catch {
            self.error = error
        }
    }

    func updateDraft(_ item: QueueItem, newText: String) async {
        guard let api = apiClient else { return }
        do {
            _ = try await api.updateQueueItem(id: item.id, data: QueueItemUpdate(draftText: newText))
            await load()
        } catch {
            self.error = error
        }
    }

    func setFilter(_ filter: String?) {
        activeFilter = filter
        Task { await load() }
    }
}
