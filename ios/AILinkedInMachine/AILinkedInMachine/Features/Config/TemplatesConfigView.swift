import SwiftUI

struct TemplatesConfigView: View {
    @Environment(APIClient.self) private var apiClient
    @State private var templates: [CommentTemplate] = []

    var body: some View {
        List {
            ForEach(templates) { template in
                VStack(alignment: .leading, spacing: DesignTokens.Spacing.sm) {
                    HStack(spacing: 6) {
                        StatusBadge(text: template.persona, color: .accent)
                        if !template.tone.isEmpty {
                            StatusBadge(text: template.tone, color: .textMuted)
                        }
                        if !template.category.isEmpty {
                            StatusBadge(text: template.category, color: .textMuted)
                        }
                    }
                    Text(template.templateText)
                        .font(.system(size: 13))
                        .foregroundStyle(.textSecondary)
                        .lineLimit(3)
                    if !template.exampleUse.isEmpty {
                        Text("Example: \(template.exampleUse)")
                            .font(.system(size: 11))
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
            do { templates = try await apiClient.getTemplates() } catch {}
        }
    }
}
