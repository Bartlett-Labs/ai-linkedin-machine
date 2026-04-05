import SwiftUI

struct TargetsConfigView: View {
    @Environment(APIClient.self) private var apiClient
    @State private var targets: [CommentTarget] = []

    private let catColors: [String: Color] = [
        "ai_leader": .accent, "ops_supply_chain": .success,
        "network": .textSecondary, "industry_analyst": .warning,
        "content_creator": .warning,
    ]

    var body: some View {
        List {
            ForEach(targets) { target in
                VStack(alignment: .leading, spacing: DesignTokens.Spacing.sm) {
                    HStack {
                        Text(target.name)
                            .font(.system(size: 14, weight: .medium))
                            .foregroundStyle(Color.textPrimary)
                        Spacer()
                        Text("P\(target.priority)")
                            .font(.system(size: 11, weight: .bold, design: .monospaced))
                            .foregroundStyle(Color.accent)
                    }
                    HStack {
                        StatusBadge(text: target.category, color: catColors[target.category] ?? Color.textMuted)
                        Spacer()
                        Text(target.lastCommentDate ?? "Never")
                            .font(.system(size: 10, design: .monospaced))
                            .foregroundStyle(Color.textMuted)
                    }
                    if let notes = target.notes, !notes.isEmpty {
                        Text(notes)
                            .font(.system(size: 11))
                            .foregroundStyle(Color.textMuted)
                    }
                }
                .padding(.vertical, 4)
                .listRowBackground(Color.surface1)
                .listRowSeparatorTint(.appBorder)
            }
        }
        .listStyle(.plain)
        .scrollContentBackground(.hidden)
        .background(Color.appBackground)
        .task {
            do { targets = try await apiClient.getTargets() } catch {}
        }
    }
}
