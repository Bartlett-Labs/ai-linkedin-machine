import SwiftUI

struct QueueListView: View {
    @Environment(APIClient.self) private var apiClient
    @State private var vm = QueueViewModel()
    @State private var selectedItem: QueueItem?

    private let filters: [(String?, String)] = [
        (nil, "All"),
        ("READY", "Ready"),
        ("IN_PROGRESS", "Active"),
        ("DONE", "Done"),
        ("FAILED", "Failed"),
    ]

    var body: some View {
        NavigationStack {
            VStack(spacing: 0) {
                filterBar
                queueList
            }
            .background(Color.appBackground)
            .navigationTitle("Queue")
            .refreshable { await vm.load() }
            .task {
                vm.bind(apiClient)
                await vm.load()
            }
            .sheet(item: $selectedItem) { item in
                QueueDetailView(item: item, vm: vm)
            }
        }
    }

    // MARK: - Filter Bar

    private var filterBar: some View {
        ScrollView(.horizontal, showsIndicators: false) {
            HStack(spacing: DesignTokens.Spacing.sm) {
                ForEach(filters, id: \.1) { filter in
                    let isActive = vm.activeFilter == filter.0
                    Button {
                        vm.setFilter(filter.0)
                    } label: {
                        HStack(spacing: 4) {
                            Text(filter.1)
                                .font(.system(size: 12, weight: .medium))
                            if let stats = vm.stats, let count = statCount(stats, for: filter.0) {
                                Text("\(count)")
                                    .font(.system(size: 10, weight: .bold, design: .monospaced))
                            }
                        }
                        .foregroundStyle(isActive ?Color.accent : Color.textMuted)
                        .padding(.horizontal, 12)
                        .padding(.vertical, 6)
                        .background(isActive ? Color.accent.opacity(0.1) : Color.surface2)
                        .clipShape(Capsule())
                        .overlay(
                            Capsule().strokeBorder(
                                isActive ? Color.accent.opacity(0.3) : Color.appBorder,
                                lineWidth: 1
                            )
                        )
                    }
                }
            }
            .padding(.horizontal, DesignTokens.Spacing.lg)
            .padding(.vertical, DesignTokens.Spacing.sm)
        }
    }

    private func statCount(_ stats: QueueStats, for filter: String?) -> Int? {
        switch filter {
        case nil: return stats.total
        case "READY": return stats.ready
        case "IN_PROGRESS": return stats.inProgress
        case "DONE": return stats.done
        case "FAILED": return stats.failed
        case "SKIPPED": return stats.skipped
        default: return nil
        }
    }

    // MARK: - Queue List

    private var queueList: some View {
        Group {
            if vm.isLoading && vm.items.isEmpty {
                LoadingView(message: "Loading queue...")
            } else if vm.items.isEmpty {
                ContentUnavailableView(
                    "No Queue Items",
                    systemImage: "tray",
                    description: Text("No items match the current filter")
                )
            } else {
                List {
                    ForEach(vm.items) { item in
                        QueueItemRow(item: item)
                            .listRowBackground(Color.surface1)
                            .listRowSeparatorTint(.appBorder)
                            .contentShape(Rectangle())
                            .onTapGesture { selectedItem = item }
                            .swipeActions(edge: .trailing) {
                                Button("Reject") { Task { await vm.reject(item) } }
                                    .tint(.danger)
                            }
                            .swipeActions(edge: .leading) {
                                Button("Approve") { Task { await vm.approve(item) } }
                                    .tint(.success)
                            }
                    }
                }
                .listStyle(.plain)
                .scrollContentBackground(.hidden)
            }
        }
    }
}

// MARK: - Queue Item Row

struct QueueItemRow: View {
    let item: QueueItem

    var body: some View {
        VStack(alignment: .leading, spacing: DesignTokens.Spacing.sm) {
            HStack {
                StatusBadge(text: item.status)

                Text(item.actionType)
                    .font(.system(size: 10, weight: .medium, design: .monospaced))
                    .foregroundStyle(Color.textMuted)

                Spacer()

                if let created = item.createdAt {
                    Text(created.toDate()?.relativeDisplay() ?? "")
                        .font(.system(size: 10, design: .monospaced))
                        .foregroundStyle(Color.textMuted)
                }
            }

            Text(item.draftText)
                .font(.system(size: 13))
                .foregroundStyle(Color.textSecondary)
                .lineLimit(3)

            HStack(spacing: DesignTokens.Spacing.sm) {
                if !item.persona.isEmpty {
                    Label(item.persona, systemImage: "person.fill")
                        .font(.system(size: 10))
                        .foregroundStyle(.accent.opacity(0.7))
                }
                if !item.targetName.isEmpty {
                    Label(item.targetName, systemImage: "at")
                        .font(.system(size: 10))
                        .foregroundStyle(Color.textMuted)
                }
            }
        }
        .padding(.vertical, 4)
    }
}

// MARK: - Queue Detail View

struct QueueDetailView: View {
    let item: QueueItem
    let vm: QueueViewModel
    @Environment(\.dismiss) private var dismiss
    @State private var editedText: String

    init(item: QueueItem, vm: QueueViewModel) {
        self.item = item
        self.vm = vm
        self._editedText = State(initialValue: item.draftText)
    }

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: DesignTokens.Spacing.lg) {
                    HStack {
                        StatusBadge(text: item.status)
                        StatusBadge(text: item.actionType, color: Color.textMuted)
                        Spacer()
                    }

                    VStack(alignment: .leading, spacing: DesignTokens.Spacing.xs) {
                        Text("DRAFT")
                            .font(.system(size: 10, weight: .semibold))
                            .foregroundStyle(Color.textMuted)
                        TextEditor(text: $editedText)
                            .font(.system(size: 14))
                            .foregroundStyle(Color.textPrimary)
                            .scrollContentBackground(.hidden)
                            .frame(minHeight: 200)
                            .padding(DesignTokens.Spacing.sm)
                            .background(.surface2)
                            .clipShape(RoundedRectangle(cornerRadius: DesignTokens.Radius.control))
                            .overlay(
                                RoundedRectangle(cornerRadius: DesignTokens.Radius.control)
                                    .strokeBorder(Color.appBorder, lineWidth: 1)
                            )
                    }

                    detailRow("Persona", value: item.persona)
                    detailRow("Target", value: item.targetName)
                    if !item.targetUrl.isEmpty {
                        detailRow("URL", value: item.targetUrl)
                    }
                    if !item.notes.isEmpty {
                        detailRow("Notes", value: item.notes)
                    }
                }
                .padding(DesignTokens.Spacing.lg)
            }
            .background(Color.appBackground)
            .navigationTitle("Queue Item #\(item.id)")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Close") { dismiss() }
                }
                ToolbarItem(placement: .confirmationAction) {
                    if editedText != item.draftText {
                        Button("Save") {
                            Task {
                                await vm.updateDraft(item, newText: editedText)
                                dismiss()
                            }
                        }
                        .foregroundStyle(Color.accent)
                    }
                }
            }
            .safeAreaInset(edge: .bottom) {
                HStack(spacing: DesignTokens.Spacing.sm) {
                    Button {
                        Task {
                            await vm.reject(item)
                            dismiss()
                        }
                    } label: {
                        Text("Reject")
                            .font(.system(size: 14, weight: .medium))
                            .foregroundStyle(.white)
                            .frame(maxWidth: .infinity)
                            .padding(.vertical, 12)
                            .background(.danger)
                            .clipShape(RoundedRectangle(cornerRadius: DesignTokens.Radius.control))
                    }

                    Button {
                        Task {
                            await vm.approve(item)
                            dismiss()
                        }
                    } label: {
                        Text("Approve")
                            .font(.system(size: 14, weight: .medium))
                            .foregroundStyle(.appBackground)
                            .frame(maxWidth: .infinity)
                            .padding(.vertical, 12)
                            .background(.success)
                            .clipShape(RoundedRectangle(cornerRadius: DesignTokens.Radius.control))
                    }
                }
                .padding(DesignTokens.Spacing.lg)
                .background(.surface1)
            }
        }
    }

    private func detailRow(_ label: String, value: String) -> some View {
        VStack(alignment: .leading, spacing: 2) {
            Text(label.uppercased())
                .font(.system(size: 10, weight: .semibold))
                .foregroundStyle(Color.textMuted)
            Text(value)
                .font(.system(size: 13, design: .monospaced))
                .foregroundStyle(Color.textSecondary)
        }
    }
}

#Preview {
    QueueListView()
        .environment(APIClient())
        .preferredColorScheme(.dark)
}
