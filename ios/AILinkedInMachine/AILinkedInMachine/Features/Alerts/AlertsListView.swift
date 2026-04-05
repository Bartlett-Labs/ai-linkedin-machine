import SwiftUI

struct AlertsListView: View {
    @Environment(APIClient.self) private var apiClient
    @State private var vm = AlertsViewModel()

    var body: some View {
        NavigationStack {
            Group {
                if vm.isLoading && vm.alerts.isEmpty {
                    LoadingView(message: "Loading alerts...")
                } else if vm.alerts.isEmpty {
                    ContentUnavailableView(
                        "No Alerts",
                        systemImage: "bell.slash",
                        description: Text("No engagement alerts to show")
                    )
                } else {
                    List {
                        ForEach(vm.alerts) { alert in
                            AlertRow(alert: alert)
                                .listRowBackground(Color.surface1)
                                .listRowSeparatorTint(.appBorder)
                                .swipeActions(edge: .trailing) {
                                    Button("Dismiss") {
                                        Task { await vm.dismiss(alert) }
                                    }
                                    .tint(.textMuted)
                                }
                                .swipeActions(edge: .leading) {
                                    if !alert.responded {
                                        Button("Responded") {
                                            Task { await vm.markResponded(alert) }
                                        }
                                        .tint(.success)
                                    }
                                }
                        }
                    }
                    .listStyle(.plain)
                    .scrollContentBackground(.hidden)
                }
            }
            .background(Color.appBackground)
            .navigationTitle("Alerts")
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    if vm.unrespondedCount > 0 {
                        Text("\(vm.unrespondedCount) new")
                            .font(.system(size: 12, weight: .medium, design: .monospaced))
                            .foregroundStyle(.warning)
                    }
                }
            }
            .refreshable { await vm.load() }
            .task {
                vm.bind(apiClient)
                await vm.load()
            }
        }
    }
}

struct AlertRow: View {
    let alert: EngagementAlert

    var body: some View {
        VStack(alignment: .leading, spacing: DesignTokens.Spacing.sm) {
            HStack {
                StatusBadge(text: alert.urgency, color: DesignTokens.urgencyColor(for: alert.urgency))

                Spacer()

                HStack(spacing: 4) {
                    Image(systemName: "clock")
                        .font(.system(size: 10))
                    Text(elapsedText)
                        .font(.system(size: 10, design: .monospaced))
                }
                .foregroundStyle(.textMuted)

                if alert.responded {
                    Image(systemName: "checkmark.circle.fill")
                        .font(.system(size: 14))
                        .foregroundStyle(.success)
                }
            }

            Text(alert.commentText)
                .font(.system(size: 13))
                .foregroundStyle(.textPrimary)
                .lineLimit(3)

            HStack(spacing: DesignTokens.Spacing.sm) {
                Label(alert.commenterName, systemImage: "person.fill")
                    .font(.system(size: 11))
                    .foregroundStyle(.accent.opacity(0.8))

                Spacer()

                if !alert.postTitle.isEmpty {
                    Text(alert.postTitle)
                        .font(.system(size: 10))
                        .foregroundStyle(.textMuted)
                        .lineLimit(1)
                }
            }

            if let url = URL(string: alert.postUrl), !alert.postUrl.isEmpty {
                Link(destination: url) {
                    HStack(spacing: 4) {
                        Image(systemName: "arrow.up.right.square")
                            .font(.system(size: 10))
                        Text("Open on LinkedIn")
                            .font(.system(size: 11, weight: .medium))
                    }
                    .foregroundStyle(.accent)
                }
            }
        }
        .padding(.vertical, 4)
        .opacity(alert.responded ? 0.6 : 1.0)
    }

    private var elapsedText: String {
        let mins = alert.elapsedMinutes
        if mins < 60 { return "\(mins)m ago" }
        if mins < 1440 { return "\(mins / 60)h ago" }
        return "\(mins / 1440)d ago"
    }
}

#Preview {
    AlertsListView()
        .environment(APIClient())
        .preferredColorScheme(.dark)
}
