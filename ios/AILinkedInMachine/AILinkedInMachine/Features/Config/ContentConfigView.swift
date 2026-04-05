import SwiftUI

struct ContentConfigView: View {
    @Environment(APIClient.self) private var apiClient
    @State private var items: [ContentBankItem] = []

    var body: some View {
        List {
            ForEach(items) { item in
                VStack(alignment: .leading, spacing: DesignTokens.Spacing.sm) {
                    HStack {
                        StatusBadge(text: item.category, color: .accent)
                        StatusBadge(text: item.postType, color: .textMuted)
                        Spacer()
                        if item.ready {
                            StatusBadge(text: "READY", color: .success)
                        } else {
                            StatusBadge(text: "DRAFT", color: .warning)
                        }
                    }
                    Text(item.draft)
                        .font(.system(size: 13))
                        .foregroundStyle(.textSecondary)
                        .lineLimit(4)
                    if let notes = item.notes, !notes.isEmpty {
                        Text(notes)
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
            do { items = try await apiClient.getContentBank() } catch {}
        }
    }
}
