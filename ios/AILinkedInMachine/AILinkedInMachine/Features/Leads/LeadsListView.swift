import SwiftUI

struct LeadsListView: View {
    @Environment(APIClient.self) private var apiClient
    @State private var leads: [Lead] = []

    var body: some View {
        List {
            ForEach(leads) { lead in
                VStack(alignment: .leading, spacing: DesignTokens.Spacing.sm) {
                    HStack {
                        Text(lead.name)
                            .font(.system(size: 14, weight: .medium))
                            .foregroundStyle(.textPrimary)
                        Spacer()
                        scoreBadge(lead.score)
                    }
                    Text("\(lead.title) at \(lead.company)")
                        .font(.system(size: 12))
                        .foregroundStyle(.textSecondary)
                    HStack {
                        StatusBadge(text: lead.status)
                        Text("\(lead.interactionCount) interactions")
                            .font(.system(size: 10, design: .monospaced))
                            .foregroundStyle(.textMuted)
                        Spacer()
                        Text(lead.discoveredAt.toDate()?.relativeDisplay() ?? "")
                            .font(.system(size: 10, design: .monospaced))
                            .foregroundStyle(.textMuted)
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
            do {
                let response = try await apiClient.getLeads()
                leads = response.leads
            } catch {}
        }
    }

    private func scoreBadge(_ score: Int) -> some View {
        let color: Color = score >= 50 ? .success : score >= 30 ? .warning : .textMuted
        return Text("\(score)")
            .font(.system(size: 12, weight: .bold, design: .monospaced))
            .foregroundStyle(color)
            .padding(.horizontal, 8)
            .padding(.vertical, 2)
            .background(color.opacity(0.15))
            .clipShape(Capsule())
    }
}
