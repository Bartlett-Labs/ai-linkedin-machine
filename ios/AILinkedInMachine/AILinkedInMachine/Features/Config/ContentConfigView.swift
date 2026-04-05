import SwiftUI

struct ContentConfigView: View {
    @Environment(APIClient.self) private var apiClient
    @State private var items: [ContentBankItem] = []

    var body: some View {
        List {
            ForEach(items) { item in
                VStack(alignment: .leading, spacing: DesignTokens.Spacing.sm) {
                    HStack {
                        StatusBadge(text: item.category, color: Color.accent)
                        StatusBadge(text: item.postType, color: Color.textMuted)
                        Spacer()
                        if item.ready {
                            StatusBadge(text: "READY", color: Color.success)
                        } else {
                            StatusBadge(text: "DRAFT", color: Color.warning)
                        }
                    }
                    Text(item.draft)
                        .font(.system(size: 13))
                        .foregroundStyle(Color.textSecondary)
                        .lineLimit(4)
                    if let notes = item.notes, !notes.isEmpty {
                        Text(notes)
                            .font(.system(size: 11))
                            .foregroundStyle(Color.textMuted)
                    }
                }
                .padding(.vertical, 4)
                .listRowBackground(Color.surface1)
                .listRowSeparatorTint(Color.appBorder)
            }
        }
        .listStyle(.plain)
        .scrollContentBackground(.hidden)
        .background(Color.appBackground)
        .task {
            do { items = try await apiClient.getContentBank() } catch {}
        }
    }
}
