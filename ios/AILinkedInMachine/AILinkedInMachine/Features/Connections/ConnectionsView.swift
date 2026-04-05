import SwiftUI

struct ConnectionsView: View {
    @Environment(APIClient.self) private var apiClient
    @State private var status: ConnectorStatus?
    @State private var requests: [ConnectionRequest] = []

    var body: some View {
        ScrollView {
            VStack(spacing: DesignTokens.Spacing.lg) {
                if let status {
                    statsRow(status)
                }
                requestsList
            }
            .padding(DesignTokens.Spacing.lg)
        }
        .background(Color.appBackground)
        .task {
            do {
                async let s = apiClient.getConnectorStatus()
                async let r = apiClient.getConnectionRequests()
                status = try await s
                requests = try await r.requests
            } catch {}
        }
    }

    private func statsRow(_ s: ConnectorStatus) -> some View {
        LazyVGrid(columns: [GridItem(.flexible()), GridItem(.flexible()), GridItem(.flexible())], spacing: DesignTokens.Spacing.sm) {
            StatCard(title: "Sent Today", value: "\(s.sentToday)/\(s.dailyLimit)", icon: "paperplane.fill", color: .accent)
            StatCard(title: "Accepted", value: "\(s.totalAccepted)", icon: "checkmark.circle.fill", color: .success)
            StatCard(title: "Remaining", value: "\(s.remaining)", icon: "clock.fill", color: .warning)
        }
    }

    private var requestsList: some View {
        VStack(alignment: .leading, spacing: DesignTokens.Spacing.md) {
            Text("Recent Requests")
                .font(.headline)
                .foregroundStyle(.textPrimary)

            ForEach(requests) { req in
                GlassCard {
                    VStack(alignment: .leading, spacing: DesignTokens.Spacing.sm) {
                        HStack {
                            Text(req.name)
                                .font(.system(size: 14, weight: .medium))
                                .foregroundStyle(.textPrimary)
                            Spacer()
                            StatusBadge(text: req.source, color: .accent)
                        }
                        Text(req.headline)
                            .font(.system(size: 12))
                            .foregroundStyle(.textSecondary)
                            .lineLimit(2)
                        if !req.note.isEmpty {
                            Text(req.note)
                                .font(.system(size: 11))
                                .foregroundStyle(.textMuted)
                                .lineLimit(2)
                        }
                    }
                }
            }
        }
    }
}
