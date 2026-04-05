import SwiftUI

struct ScheduleConfigView: View {
    @Environment(APIClient.self) private var apiClient
    @State private var configs: [ScheduleConfig] = []
    @State private var windows: [ActivityWindow] = []
    @State private var weeklyPlan: [WeeklyPlanDay] = []

    var body: some View {
        ScrollView {
            VStack(spacing: DesignTokens.Spacing.lg) {
                ForEach(configs) { config in
                    scheduleCard(config)
                }
                if !weeklyPlan.isEmpty {
                    weeklyPlanCard
                }
            }
            .padding(DesignTokens.Spacing.lg)
        }
        .background(Color.appBackground)
        .task {
            do {
                async let c = apiClient.getScheduleConfigs()
                async let w = apiClient.getActivityWindows()
                async let p = apiClient.getWeeklyPlan()
                configs = try await c
                windows = try await w
                weeklyPlan = try await p
            } catch {}
        }
    }

    private func scheduleCard(_ config: ScheduleConfig) -> some View {
        GlassCard {
            VStack(alignment: .leading, spacing: DesignTokens.Spacing.md) {
                HStack {
                    StatusBadge(text: config.mode)
                    Spacer()
                }

                LazyVGrid(columns: [GridItem(.flexible()), GridItem(.flexible())], spacing: DesignTokens.Spacing.sm) {
                    scheduleStat("Posts/Week", value: "\(config.postsPerWeek)")
                    scheduleStat("Comments/Day", value: "\(config.commentsPerDayMin)-\(config.commentsPerDayMax)")
                    scheduleStat("Phantom/Post", value: "\(config.phantomCommentsMin)-\(config.phantomCommentsMax)")
                    scheduleStat("Min Delay", value: "\(config.minDelaySec)s")
                }
            }
        }
    }

    private func scheduleStat(_ label: String, value: String) -> some View {
        VStack(alignment: .leading, spacing: 2) {
            Text(label.uppercased())
                .font(.system(size: 9, weight: .semibold))
                .foregroundStyle(Color.textMuted)
            Text(value)
                .font(.system(size: 14, weight: .medium, design: .monospaced))
                .foregroundStyle(Color.textSecondary)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
    }

    private var weeklyPlanCard: some View {
        GlassCard {
            VStack(alignment: .leading, spacing: DesignTokens.Spacing.md) {
                Text("Weekly Plan")
                    .font(.headline)
                    .foregroundStyle(Color.textPrimary)

                ForEach(weeklyPlan) { day in
                    HStack {
                        Text(day.day)
                            .font(.system(size: 12, weight: .medium))
                            .foregroundStyle(Color.textPrimary)
                            .frame(width: 40, alignment: .leading)

                        if day.isPostDay {
                            StatusBadge(text: "POST", color: Color.success)
                        }

                        Text("\(day.actions.count) actions")
                            .font(.system(size: 11, design: .monospaced))
                            .foregroundStyle(Color.textMuted)

                        Spacer()

                        Text(day.date)
                            .font(.system(size: 10, design: .monospaced))
                            .foregroundStyle(Color.textMuted)
                    }
                }
            }
        }
    }
}
