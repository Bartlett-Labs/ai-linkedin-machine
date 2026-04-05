import SwiftUI

struct PersonaSchedulerView: View {
    @Environment(APIClient.self) private var apiClient
    @State private var vm = PersonasViewModel()

    var body: some View {
        ScrollView {
            VStack(spacing: DesignTokens.Spacing.md) {
                runAllButton

                ForEach(vm.heartbeats) { persona in
                    PersonaStatusCard(persona: persona) {
                        await vm.triggerHeartbeat(name: persona.name)
                    }
                }
            }
            .padding(DesignTokens.Spacing.lg)
        }
        .background(Color.appBackground)
        .refreshable { await vm.load() }
        .task {
            vm.bind(apiClient)
            await vm.load()
        }
    }

    private var runAllButton: some View {
        Button {
            Task { await vm.triggerAll() }
        } label: {
            HStack {
                Image(systemName: "play.fill")
                Text("Run All Personas")
                    .font(.system(size: 14, weight: .medium))
            }
            .foregroundStyle(.appBackground)
            .frame(maxWidth: .infinity)
            .padding(.vertical, 12)
            .background(.accent)
            .clipShape(RoundedRectangle(cornerRadius: DesignTokens.Radius.control))
        }
    }
}

struct PersonaStatusCard: View {
    let persona: PersonaHeartbeatStatus
    let onTrigger: () async -> Void

    var body: some View {
        GlassCard {
            VStack(alignment: .leading, spacing: DesignTokens.Spacing.md) {
                HStack {
                    statusDot
                    VStack(alignment: .leading, spacing: 2) {
                        Text(persona.displayName)
                            .font(.system(size: 15, weight: .medium))
                            .foregroundStyle(.textPrimary)
                        Text(persona.name)
                            .font(.system(size: 11, design: .monospaced))
                            .foregroundStyle(.textMuted)
                    }
                    Spacer()
                    statusBadge
                }

                if let hours = persona.activeHours {
                    HStack(spacing: DesignTokens.Spacing.md) {
                        if let start = hours["start"], let end = hours["end"] {
                            detailPill("Hours", value: "\(start) - \(end)")
                        }
                        if let tz = hours["timezone"] {
                            detailPill("TZ", value: tz)
                        }
                    }
                }

                if let schedule = persona.schedule {
                    HStack(spacing: DesignTokens.Spacing.md) {
                        if let cpc = schedule["comments_per_cycle"] {
                            detailPill("Comments/Cycle", value: "\(cpc.value)")
                        }
                        if let interval = schedule["cycle_interval_minutes"] {
                            detailPill("Interval", value: "\(interval.value)m")
                        }
                    }
                }

                Button {
                    Task { await onTrigger() }
                } label: {
                    HStack {
                        Image(systemName: "play.circle.fill")
                        Text("Run Cycle")
                            .font(.system(size: 12, weight: .medium))
                    }
                    .foregroundStyle(.accent)
                    .frame(maxWidth: .infinity)
                    .padding(.vertical, 8)
                    .background(.accent.opacity(0.1))
                    .clipShape(RoundedRectangle(cornerRadius: DesignTokens.Radius.control))
                    .overlay(
                        RoundedRectangle(cornerRadius: DesignTokens.Radius.control)
                            .strokeBorder(.accent.opacity(0.2), lineWidth: 1)
                    )
                }
            }
        }
    }

    private var statusDot: some View {
        Circle()
            .fill(dotColor)
            .frame(width: 10, height: 10)
            .shadow(color: persona.isRunning ? .accent.opacity(0.6) : .clear, radius: 4)
    }

    private var dotColor: Color {
        if persona.isRunning { return .accent }
        if persona.inActiveHours { return .success }
        return .textMuted.opacity(0.4)
    }

    @ViewBuilder
    private var statusBadge: some View {
        if persona.isRunning {
            StatusBadge(text: "RUNNING", color: .accent)
        } else if persona.inActiveHours {
            StatusBadge(text: "ACTIVE", color: .success)
        } else {
            StatusBadge(text: "INACTIVE", color: .textMuted)
        }
    }

    private func detailPill(_ label: String, value: String) -> some View {
        VStack(alignment: .leading, spacing: 1) {
            Text(label.uppercased())
                .font(.system(size: 9, weight: .semibold))
                .foregroundStyle(.textMuted)
            Text(value)
                .font(.system(size: 12, design: .monospaced))
                .foregroundStyle(.textSecondary)
        }
    }
}

#Preview {
    NavigationStack {
        PersonaSchedulerView()
            .environment(APIClient())
            .preferredColorScheme(.dark)
            .navigationTitle("Personas")
    }
}
