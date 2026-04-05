import SwiftUI

struct PersonaActivityView: View {
    @Environment(APIClient.self) private var apiClient
    @State private var stats: [PersonaStats] = []
    @State private var isLoading = false

    var body: some View {
        ScrollView {
            VStack(spacing: DesignTokens.Spacing.md) {
                ForEach(stats) { stat in
                    GlassCard {
                        VStack(alignment: .leading, spacing: DesignTokens.Spacing.sm) {
                            HStack {
                                Text(stat.persona)
                                    .font(.system(size: 15, weight: .medium))
                                    .foregroundStyle(.textPrimary)
                                Spacer()
                                Text("\(stat.totalActions) total")
                                    .font(.system(size: 12, weight: .medium, design: .monospaced))
                                    .foregroundStyle(.accent)
                            }

                            HStack(spacing: DesignTokens.Spacing.lg) {
                                activityStat("Comments", value: stat.comments, color: .accent)
                                activityStat("Posts", value: stat.posts, color: .success)
                                activityStat("Replies", value: stat.replies, color: .warning)
                            }

                            // Activity bar
                            GeometryReader { geometry in
                                let total = max(stat.totalActions, 1)
                                HStack(spacing: 2) {
                                    Rectangle()
                                        .fill(Color.accent)
                                        .frame(width: geometry.size.width * Double(stat.comments) / Double(total))
                                    Rectangle()
                                        .fill(Color.success)
                                        .frame(width: geometry.size.width * Double(stat.posts) / Double(total))
                                    Rectangle()
                                        .fill(Color.warning)
                                        .frame(width: geometry.size.width * Double(stat.replies) / Double(total))
                                }
                                .frame(height: 4)
                                .clipShape(Capsule())
                            }
                            .frame(height: 4)
                        }
                    }
                }
            }
            .padding(DesignTokens.Spacing.lg)
        }
        .background(Color.appBackground)
        .task {
            isLoading = true
            do {
                stats = try await apiClient.getPersonaAnalytics(days: 30)
            } catch {}
            isLoading = false
        }
    }

    private func activityStat(_ label: String, value: Int, color: Color) -> some View {
        VStack(spacing: 1) {
            Text("\(value)")
                .font(.system(size: 16, weight: .semibold, design: .monospaced))
                .foregroundStyle(color)
            Text(label)
                .font(.system(size: 10))
                .foregroundStyle(.textMuted)
        }
        .frame(maxWidth: .infinity)
    }
}
