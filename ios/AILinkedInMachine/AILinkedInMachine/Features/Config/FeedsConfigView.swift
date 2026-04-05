import SwiftUI

struct FeedsConfigView: View {
    @Environment(APIClient.self) private var apiClient
    @State private var feeds: [FeedSource] = []
    @State private var isLoading = false

    var body: some View {
        Group {
            if isLoading && feeds.isEmpty {
                LoadingView(message: "Loading feeds...")
            } else if feeds.isEmpty {
                ContentUnavailableView("No Feeds", systemImage: "antenna.radiowaves.left.and.right", description: Text("No feed sources configured"))
            } else {
                List {
                    ForEach(feeds) { feed in
                        feedRow(feed)
                    }
                }
                .listStyle(.plain)
                .scrollContentBackground(.hidden)
            }
        }
        .background(Color.appBackground)
        .task { await load() }
        .refreshable { await load() }
    }

    private func load() async {
        isLoading = true
        do {
            let response = try await apiClient.getFeeds()
            feeds = response.feeds
        } catch {}
        isLoading = false
    }

    private func feedRow(_ feed: FeedSource) -> some View {
        VStack(alignment: .leading, spacing: DesignTokens.Spacing.sm) {
            HStack {
                Circle()
                    .fill(feed.active ? Color.success : Color.textMuted.opacity(0.4))
                    .frame(width: 8, height: 8)
                Text(feed.name)
                    .font(.system(size: 14, weight: .medium))
                    .foregroundStyle(Color.textPrimary)
                Spacer()
                StatusBadge(text: feed.type, color: Color.textMuted)
                if !feed.category.isEmpty {
                    StatusBadge(text: feed.category, color: Color.accent)
                }
            }
            Text(feed.url)
                .font(.system(size: 11, design: .monospaced))
                .foregroundStyle(Color.textMuted)
                .lineLimit(1)
            if let lastFetched = feed.lastFetched {
                Text("Last fetched: \(lastFetched.toDate()?.relativeDisplay() ?? lastFetched)")
                    .font(.system(size: 10, design: .monospaced))
                    .foregroundStyle(Color.textMuted)
            }
        }
        .padding(.vertical, 4)
        .listRowBackground(Color.surface1)
        .listRowSeparatorTint(.appBorder)
        .opacity(feed.active ? 1.0 : 0.6)
    }
}
