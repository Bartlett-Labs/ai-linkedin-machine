import SwiftUI
import Charts

enum ActivitySection: String, CaseIterable {
    case analytics = "Analytics"
    case history = "History"
    case runs = "Runs"
    case errors = "Errors"
}

struct ActivityView: View {
    @Environment(APIClient.self) private var apiClient
    @State private var vm = ActivityViewModel()
    @State private var selectedSection: ActivitySection = .analytics

    var body: some View {
        NavigationStack {
            VStack(spacing: 0) {
                sectionPicker
                TabView(selection: $selectedSection) {
                    analyticsTab.tag(ActivitySection.analytics)
                    historyTab.tag(ActivitySection.history)
                    runsTab.tag(ActivitySection.runs)
                    errorsTab.tag(ActivitySection.errors)
                }
                .tabViewStyle(.page(indexDisplayMode: .never))
            }
            .background(Color.appBackground)
            .navigationTitle("Activity")
            .task {
                vm.bind(apiClient)
                await vm.loadAnalytics()
            }
            .onChange(of: selectedSection) { _, section in
                Task {
                    switch section {
                    case .analytics: await vm.loadAnalytics()
                    case .history: await vm.loadHistory()
                    case .runs: await vm.loadRuns()
                    case .errors: await vm.loadErrors()
                    }
                }
            }
        }
    }

    // MARK: - Section Picker

    private var sectionPicker: some View {
        HStack(spacing: 0) {
            ForEach(ActivitySection.allCases, id: \.self) { section in
                Button {
                    withAnimation(.easeInOut(duration: 0.2)) {
                        selectedSection = section
                    }
                } label: {
                    Text(section.rawValue)
                        .font(.system(size: 13, weight: selectedSection == section ? .semibold : .regular))
                        .foregroundStyle(selectedSection == section ? .accent : .textMuted)
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, 10)
                        .overlay(alignment: .bottom) {
                            if selectedSection == section {
                                Rectangle()
                                    .fill(.accent)
                                    .frame(height: 2)
                            }
                        }
                }
            }
        }
        .background(.surface1)
        .overlay(alignment: .bottom) {
            Rectangle().fill(.appBorder).frame(height: 1)
        }
    }

    // MARK: - Analytics Tab

    private var analyticsTab: some View {
        ScrollView {
            VStack(spacing: DesignTokens.Spacing.lg) {
                if !vm.trends.isEmpty {
                    trendChart
                }
                if !vm.personaStats.isEmpty {
                    personaBreakdown
                }
            }
            .padding(DesignTokens.Spacing.lg)
        }
        .refreshable { await vm.loadAnalytics() }
    }

    private var trendChart: some View {
        GlassCard {
            VStack(alignment: .leading, spacing: DesignTokens.Spacing.md) {
                Text("30-Day Engagement")
                    .font(.headline)
                    .foregroundStyle(.textPrimary)

                Chart(vm.trends) { trend in
                    LineMark(
                        x: .value("Date", trend.date),
                        y: .value("Count", trend.comments)
                    )
                    .foregroundStyle(.accent)
                    .interpolationMethod(.catmullRom)

                    LineMark(
                        x: .value("Date", trend.date),
                        y: .value("Count", trend.posts)
                    )
                    .foregroundStyle(.success)
                    .interpolationMethod(.catmullRom)
                }
                .chartYAxis {
                    AxisMarks { _ in
                        AxisGridLine(stroke: StrokeStyle(lineWidth: 0.5))
                            .foregroundStyle(.appBorder)
                        AxisValueLabel()
                            .foregroundStyle(.textMuted)
                    }
                }
                .chartXAxis {
                    AxisMarks(values: .automatic(desiredCount: 5)) { _ in
                        AxisValueLabel()
                            .foregroundStyle(.textMuted)
                    }
                }
                .frame(height: 200)

                HStack(spacing: DesignTokens.Spacing.lg) {
                    legendDot("Comments", color: .accent)
                    legendDot("Posts", color: .success)
                }
            }
        }
    }

    private func legendDot(_ label: String, color: Color) -> some View {
        HStack(spacing: 4) {
            Circle().fill(color).frame(width: 8, height: 8)
            Text(label).font(.caption).foregroundStyle(.textMuted)
        }
    }

    private var personaBreakdown: some View {
        GlassCard {
            VStack(alignment: .leading, spacing: DesignTokens.Spacing.md) {
                Text("Persona Breakdown")
                    .font(.headline)
                    .foregroundStyle(.textPrimary)

                ForEach(vm.personaStats) { stat in
                    HStack {
                        Text(stat.persona)
                            .font(.system(size: 13))
                            .foregroundStyle(.textPrimary)
                        Spacer()
                        Text("\(stat.totalActions)")
                            .font(.system(size: 13, weight: .semibold, design: .monospaced))
                            .foregroundStyle(.accent)
                    }
                }
            }
        }
    }

    // MARK: - History Tab

    private var historyTab: some View {
        Group {
            if vm.history.isEmpty && vm.isLoading {
                LoadingView(message: "Loading history...")
            } else if vm.history.isEmpty {
                ContentUnavailableView("No History", systemImage: "clock", description: Text("No activity recorded yet"))
            } else {
                List {
                    ForEach(vm.history) { entry in
                        VStack(alignment: .leading, spacing: 4) {
                            HStack {
                                StatusBadge(text: entry.result)
                                Text(entry.action)
                                    .font(.system(size: 12, weight: .medium))
                                    .foregroundStyle(.textPrimary)
                                Spacer()
                                Text(entry.timestamp.toDate()?.relativeDisplay() ?? "")
                                    .font(.system(size: 10, design: .monospaced))
                                    .foregroundStyle(.textMuted)
                            }
                            HStack {
                                Text(entry.module)
                                    .font(.system(size: 10, weight: .medium, design: .monospaced))
                                    .foregroundStyle(.accent.opacity(0.7))
                                if !entry.target.isEmpty {
                                    Text(entry.target)
                                        .font(.system(size: 10))
                                        .foregroundStyle(.textMuted)
                                        .lineLimit(1)
                                }
                            }
                        }
                        .padding(.vertical, 2)
                        .listRowBackground(Color.surface1)
                        .listRowSeparatorTint(.appBorder)
                    }
                }
                .listStyle(.plain)
                .scrollContentBackground(.hidden)
            }
        }
        .refreshable { await vm.loadHistory() }
    }

    // MARK: - Runs Tab

    private var runsTab: some View {
        Group {
            if vm.runs.isEmpty && vm.isLoading {
                LoadingView(message: "Loading runs...")
            } else if vm.runs.isEmpty {
                ContentUnavailableView("No Runs", systemImage: "arrow.triangle.2.circlepath", description: Text("No pipeline runs recorded"))
            } else {
                List {
                    ForEach(vm.runs) { run in
                        VStack(alignment: .leading, spacing: DesignTokens.Spacing.sm) {
                            HStack {
                                Text("#\(run.id)")
                                    .font(.system(size: 12, weight: .bold, design: .monospaced))
                                    .foregroundStyle(.textPrimary)
                                StatusBadge(text: run.status)
                                Spacer()
                                if let started = run.startedAt {
                                    Text(started.toDate()?.relativeDisplay() ?? "")
                                        .font(.system(size: 10, design: .monospaced))
                                        .foregroundStyle(.textMuted)
                                }
                            }
                            HStack(spacing: DesignTokens.Spacing.md) {
                                runStat("Posts", value: run.postsMade, color: .success)
                                runStat("Comments", value: run.commentsMade, color: .accent)
                                runStat("Replies", value: run.repliesMade, color: .warning)
                                runStat("Phantom", value: run.phantomActions, color: .textSecondary)
                            }
                            if !run.summary.isEmpty {
                                Text(run.summary)
                                    .font(.system(size: 11))
                                    .foregroundStyle(.textMuted)
                                    .lineLimit(2)
                            }
                        }
                        .padding(.vertical, 4)
                        .listRowBackground(Color.surface1)
                        .listRowSeparatorTint(.appBorder)
                    }
                }
                .listStyle(.plain)
                .scrollContentBackground(.hidden)
            }
        }
        .refreshable { await vm.loadRuns() }
    }

    private func runStat(_ label: String, value: Int, color: Color) -> some View {
        VStack(spacing: 1) {
            Text("\(value)")
                .font(.system(size: 14, weight: .semibold, design: .monospaced))
                .foregroundStyle(color)
            Text(label)
                .font(.system(size: 9))
                .foregroundStyle(.textMuted)
        }
    }

    // MARK: - Errors Tab

    private var errorsTab: some View {
        Group {
            let allErrors = vm.pipelineErrors + vm.systemErrors
            if allErrors.isEmpty && vm.isLoading {
                LoadingView(message: "Loading errors...")
            } else if allErrors.isEmpty {
                ContentUnavailableView("No Errors", systemImage: "checkmark.shield", description: Text("System is running clean"))
            } else {
                List {
                    if !vm.pipelineErrors.isEmpty {
                        Section {
                            ForEach(vm.pipelineErrors) { err in
                                errorRow(err)
                            }
                        } header: {
                            Text("Pipeline Errors (\(vm.pipelineErrors.count))")
                                .foregroundStyle(.danger)
                        }
                    }
                    if !vm.systemErrors.isEmpty {
                        Section {
                            ForEach(vm.systemErrors) { err in
                                errorRow(err)
                            }
                        } header: {
                            Text("System Errors (\(vm.systemErrors.count))")
                                .foregroundStyle(.warning)
                        }
                    }
                }
                .listStyle(.plain)
                .scrollContentBackground(.hidden)
            }
        }
        .refreshable { await vm.loadErrors() }
    }

    private func errorRow(_ err: PipelineError) -> some View {
        VStack(alignment: .leading, spacing: 4) {
            HStack {
                Text(err.source)
                    .font(.system(size: 12, weight: .medium, design: .monospaced))
                    .foregroundStyle(.danger)
                Spacer()
                if let ts = err.timestamp {
                    Text(ts.toDate()?.relativeDisplay() ?? "")
                        .font(.system(size: 10, design: .monospaced))
                        .foregroundStyle(.textMuted)
                }
            }
            if let summary = err.summary, !summary.isEmpty {
                Text(summary)
                    .font(.system(size: 11))
                    .foregroundStyle(.textSecondary)
                    .lineLimit(3)
            }
        }
        .padding(.vertical, 2)
        .listRowBackground(Color.surface1)
        .listRowSeparatorTint(.appBorder)
    }
}

#Preview {
    ActivityView()
        .environment(APIClient())
        .preferredColorScheme(.dark)
}
