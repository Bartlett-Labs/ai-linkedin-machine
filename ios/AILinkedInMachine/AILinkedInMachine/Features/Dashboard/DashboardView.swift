import SwiftUI

struct DashboardView: View {
    @Environment(APIClient.self) private var apiClient
    @State private var vm = DashboardViewModel()
    @State private var killSwitchPulse = false

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(spacing: DesignTokens.Spacing.lg) {
                    killSwitchBanner
                    greetingHeader
                    statsGrid
                    engineCard
                    pipelineCard
                    personasCard
                    quickActions
                }
                .padding(.horizontal, DesignTokens.Spacing.lg)
                .padding(.bottom, DesignTokens.Spacing.xxxl)
            }
            .background(dashboardBackground)
            .navigationTitle("Dashboard")
            .refreshable { await vm.loadAll() }
            .task {
                vm.bind(apiClient)
                await vm.loadAll()
            }
        }
    }

    // MARK: - Background

    private var dashboardBackground: some View {
        ZStack {
            Color.appBackground
            // Subtle radial accent glow at top
            RadialGradient(
                colors: [Color.accent.opacity(0.04), .clear],
                center: .top,
                startRadius: 0,
                endRadius: 500
            )
        }
        .ignoresSafeArea()
    }

    // MARK: - Greeting Header

    private var greetingHeader: some View {
        VStack(alignment: .leading, spacing: DesignTokens.Spacing.xs) {
            Text(greetingText)
                .font(.system(size: DesignTokens.FontSize.title2, weight: .bold))
                .foregroundStyle(Color.textPrimary)

            HStack(spacing: DesignTokens.Spacing.sm) {
                // Total actions today pill
                HStack(spacing: 4) {
                    Image(systemName: "bolt.fill")
                        .font(.system(size: 9))
                    Text("\(vm.totalActionsToday) actions today")
                        .font(.system(size: 11, weight: .medium, design: .monospaced))
                }
                .foregroundStyle(Color.accent)
                .padding(.horizontal, 10)
                .padding(.vertical, 4)
                .background(Color.accent.opacity(0.1))
                .clipShape(Capsule())

                // Active personas pill
                if vm.activePersonaCount > 0 {
                    HStack(spacing: 4) {
                        Circle()
                            .fill(Color.success)
                            .frame(width: 5, height: 5)
                        Text("\(vm.activePersonaCount) personas active")
                            .font(.system(size: 11, weight: .medium, design: .monospaced))
                    }
                    .foregroundStyle(Color.success)
                    .padding(.horizontal, 10)
                    .padding(.vertical, 4)
                    .background(Color.success.opacity(0.1))
                    .clipShape(Capsule())
                }
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(.top, DesignTokens.Spacing.xs)
    }

    private var greetingText: String {
        let hour = Calendar.current.component(.hour, from: Date())
        switch hour {
        case 0..<5:   return "Late Night Ops"
        case 5..<12:  return "Good Morning"
        case 12..<17: return "Good Afternoon"
        case 17..<21: return "Good Evening"
        default:      return "Night Mode"
        }
    }

    // MARK: - Kill Switch Banner

    @ViewBuilder
    private var killSwitchBanner: some View {
        if let ks = vm.killSwitch, ks.active {
            HStack(spacing: DesignTokens.Spacing.sm) {
                // Pulsing danger icon
                ZStack {
                    Circle()
                        .fill(.danger.opacity(killSwitchPulse ? 0.3 : 0.1))
                        .frame(width: 36, height: 36)
                    Image(systemName: "exclamationmark.octagon.fill")
                        .font(.system(size: 18))
                        .foregroundStyle(Color.danger)
                }
                .shadow(color: .danger.opacity(killSwitchPulse ? 0.5 : 0.2), radius: killSwitchPulse ? 12 : 4)

                VStack(alignment: .leading, spacing: 2) {
                    Text("KILL SWITCH ACTIVE")
                        .font(.system(size: 12, weight: .black, design: .monospaced))
                        .foregroundStyle(Color.danger)
                    Text(ks.message)
                        .font(.system(size: 11))
                        .foregroundStyle(Color.textMuted)
                        .lineLimit(1)
                }

                Spacer()

                Button {
                    Task { await vm.toggleKillSwitch() }
                } label: {
                    Text("DEACTIVATE")
                        .font(.system(size: 10, weight: .bold, design: .monospaced))
                        .foregroundStyle(.white)
                        .padding(.horizontal, 14)
                        .padding(.vertical, 8)
                        .background(LinearGradient.dangerGradient)
                        .clipShape(Capsule())
                }
            }
            .padding(DesignTokens.Spacing.md)
            .background(
                ZStack {
                    Color.surface1
                    Color.danger.opacity(0.06)
                }
            )
            .clipShape(RoundedRectangle(cornerRadius: DesignTokens.Radius.card))
            .overlay(
                RoundedRectangle(cornerRadius: DesignTokens.Radius.card)
                    .strokeBorder(.danger.opacity(killSwitchPulse ? 0.5 : 0.25), lineWidth: 1.5)
            )
            .shadow(color: .danger.opacity(0.2), radius: 12)
            .onAppear {
                withAnimation(DesignTokens.Animation.pulse) {
                    killSwitchPulse = true
                }
            }
            .onDisappear { killSwitchPulse = false }
        }
    }

    // MARK: - Stats Grid

    private var statsGrid: some View {
        LazyVGrid(columns: [
            GridItem(.flexible()), GridItem(.flexible())
        ], spacing: DesignTokens.Spacing.sm) {
            StatCard(
                title: "Comments",
                value: "\(vm.todaySummary?.commentsPosted ?? 0)",
                icon: "bubble.left.fill",
                color: .accent
            )
            StatCard(
                title: "Posts",
                value: "\(vm.todaySummary?.postsMade ?? 0)",
                icon: "doc.text.fill",
                color: .success
            )
            StatCard(
                title: "Replies",
                value: "\(vm.todaySummary?.repliesSent ?? 0)",
                icon: "arrowshape.turn.up.left.fill",
                color: .warning
            )
            StatCard(
                title: "Likes",
                value: "\(vm.todaySummary?.likesGiven ?? 0)",
                icon: "heart.fill",
                color: .danger
            )
        }
    }

    // MARK: - Engine Status Card

    private var engineCard: some View {
        GlassCard(showAccentBorder: true) {
            VStack(alignment: .leading, spacing: DesignTokens.Spacing.md) {
                // Header with animated status ring
                HStack(spacing: DesignTokens.Spacing.sm) {
                    engineStatusRing
                    VStack(alignment: .leading, spacing: 2) {
                        Text("Engine")
                            .font(.system(size: DesignTokens.FontSize.title3, weight: .semibold))
                            .foregroundStyle(Color.textPrimary)
                        if let engine = vm.engineControl {
                            Text(engine.lastRun?.toDate()?.relativeDisplay() ?? "No runs yet")
                                .font(.system(size: 10, design: .monospaced))
                                .foregroundStyle(Color.textMuted)
                        }
                    }
                    Spacer()
                    if let engine = vm.engineControl {
                        StatusBadge(text: engine.mode)
                    }
                }

                if let engine = vm.engineControl {
                    // Phase indicator
                    HStack(spacing: DesignTokens.Spacing.sm) {
                        phaseIndicator(engine.phase)
                        Spacer()
                    }

                    // Feature toggles — compact grid
                    Divider().overlay(Color.appBorder.opacity(0.5))

                    LazyVGrid(columns: [GridItem(.flexible()), GridItem(.flexible())], spacing: DesignTokens.Spacing.sm) {
                        featureToggle("Posting", isOn: engine.mainUserPosting, icon: "doc.text")
                        featureToggle("Phantoms", isOn: engine.phantomEngagement, icon: "person.2")
                        featureToggle("Comments", isOn: engine.commenting, icon: "bubble.left")
                        featureToggle("Replies", isOn: engine.replying, icon: "arrowshape.turn.up.left")
                    }
                }
            }
        }
    }

    private var engineStatusRing: some View {
        let isLive = vm.engineControl?.mode.uppercased() == "LIVE"
        let ringColor: Color = isLive ?Color.success : (vm.engineControl?.mode.uppercased() == "PAUSED" ?Color.danger : Color.warning)

        return ZStack {
            // Outer glow ring
            Circle()
                .stroke(ringColor.opacity(0.2), lineWidth: 2)
                .frame(width: 38, height: 38)

            // Animated ring
            Circle()
                .trim(from: 0, to: isLive ? 1.0 : 0.65)
                .stroke(ringColor, style: StrokeStyle(lineWidth: 2.5, lineCap: .round))
                .frame(width: 38, height: 38)
                .rotationEffect(.degrees(-90))

            // Center icon
            Image(systemName: "engine.combustion.fill")
                .font(.system(size: 14, weight: .medium))
                .foregroundStyle(ringColor)
        }
        .shadow(color: ringColor.opacity(0.3), radius: 6)
    }

    private func phaseIndicator(_ phase: String) -> some View {
        HStack(spacing: DesignTokens.Spacing.sm) {
            Text("PHASE")
                .font(.system(size: 9, weight: .bold, design: .monospaced))
                .foregroundStyle(Color.textMuted)
                .tracking(1)

            Text(phase.uppercased())
                .font(.system(size: 12, weight: .bold, design: .monospaced))
                .foregroundStyle(Color.accent)
                .padding(.horizontal, 10)
                .padding(.vertical, 4)
                .background(Color.accent.opacity(0.1))
                .clipShape(RoundedRectangle(cornerRadius: 6))
        }
    }

    private func featureToggle(_ label: String, isOn: Bool, icon: String) -> some View {
        HStack(spacing: 6) {
            Image(systemName: isOn ? "\(icon).fill" : icon)
                .font(.system(size: 10))
                .foregroundStyle(isOn ?Color.accent : .textMuted.opacity(0.5))
                .frame(width: 14)

            Text(label)
                .font(.system(size: 12))
                .foregroundStyle(isOn ?Color.textSecondary : .textMuted.opacity(0.5))

            Spacer()

            Circle()
                .fill(isOn ? Color.success : Color.textMuted.opacity(0.2))
                .frame(width: 6, height: 6)
                .shadow(color: isOn ? .success.opacity(0.5) : .clear, radius: 3)
        }
        .padding(.vertical, 2)
    }

    // MARK: - Pipeline Card

    private var pipelineCard: some View {
        GlassCard {
            VStack(alignment: .leading, spacing: DesignTokens.Spacing.md) {
                HStack {
                    ZStack {
                        Circle()
                            .fill(Color.accent.opacity(0.1))
                            .frame(width: 32, height: 32)
                        Image(systemName: "arrow.triangle.2.circlepath")
                            .font(.system(size: 14, weight: .medium))
                            .foregroundStyle(Color.accent)
                    }

                    Text("Pipeline")
                        .font(.system(size: DesignTokens.FontSize.title3, weight: .semibold))
                        .foregroundStyle(Color.textPrimary)

                    Spacer()

                    if let run = vm.latestRun {
                        StatusBadge(text: run.status)
                    }
                }

                if let run = vm.latestRun {
                    // Stats row with mini bars
                    HStack(spacing: 0) {
                        pipelineStatBar(label: "Posts", value: run.postsMade, color: Color.success)
                        pipelineStatBar(label: "Comments", value: run.commentsMade, color: Color.accent)
                        pipelineStatBar(label: "Replies", value: run.repliesMade, color: Color.warning)
                        pipelineStatBar(label: "Phantom", value: run.phantomActions, color: Color.textSecondary)
                    }

                    if let started = run.startedAt {
                        Text("Last run \(started.toDate()?.relativeDisplay() ?? started)")
                            .font(.system(size: 10, design: .monospaced))
                            .foregroundStyle(Color.textMuted)
                    }
                } else {
                    HStack(spacing: DesignTokens.Spacing.sm) {
                        Image(systemName: "clock")
                            .font(.system(size: 11))
                            .foregroundStyle(Color.textMuted)
                        Text("No pipeline runs yet")
                            .font(.system(size: 12))
                            .foregroundStyle(Color.textMuted)
                    }
                    .padding(.vertical, DesignTokens.Spacing.sm)
                }

                if let stats = vm.queueStats {
                    Divider().overlay(Color.appBorder.opacity(0.5))

                    HStack(spacing: 0) {
                        queueStatPill(label: "Total", value: stats.total, color: Color.textSecondary)
                        queueStatPill(label: "Ready", value: stats.ready ?? 0, color: Color.warning)
                        queueStatPill(label: "Failed", value: stats.failed ?? 0, color: Color.danger)
                    }
                }
            }
        }
    }

    private func pipelineStatBar(label: String, value: Int, color: Color) -> some View {
        VStack(spacing: 4) {
            Text("\(value)")
                .font(.system(size: 20, weight: .bold, design: .monospaced))
                .foregroundStyle(value > 0 ? color : .textMuted.opacity(0.4))
                .contentTransition(.numericText())

            // Mini bar
            RoundedRectangle(cornerRadius: 1.5)
                .fill(value > 0 ? color : Color.appBorder)
                .frame(height: 3)
                .padding(.horizontal, 8)

            Text(label)
                .font(.system(size: 9, weight: .medium))
                .foregroundStyle(Color.textMuted)
        }
        .frame(maxWidth: .infinity)
    }

    private func queueStatPill(label: String, value: Int, color: Color) -> some View {
        VStack(spacing: 2) {
            Text("\(value)")
                .font(.system(size: 14, weight: .semibold, design: .monospaced))
                .foregroundStyle(value > 0 ? color : .textMuted.opacity(0.4))
            Text(label)
                .font(.system(size: 9))
                .foregroundStyle(Color.textMuted)
        }
        .frame(maxWidth: .infinity)
    }

    // MARK: - Personas Card

    private var personasCard: some View {
        GlassCard {
            VStack(alignment: .leading, spacing: DesignTokens.Spacing.md) {
                HStack {
                    ZStack {
                        Circle()
                            .fill(Color.accent.opacity(0.1))
                            .frame(width: 32, height: 32)
                        Image(systemName: "person.3.fill")
                            .font(.system(size: 12, weight: .medium))
                            .foregroundStyle(Color.accent)
                    }

                    Text("Personas")
                        .font(.system(size: DesignTokens.FontSize.title3, weight: .semibold))
                        .foregroundStyle(Color.textPrimary)

                    Spacer()

                    // Compact active count
                    HStack(spacing: 4) {
                        Circle()
                            .fill(vm.activePersonaCount > 0 ? Color.success : Color.textMuted)
                            .frame(width: 6, height: 6)
                        Text("\(vm.activePersonaCount)/\(vm.heartbeatStatus.count)")
                            .font(.system(size: 12, weight: .medium, design: .monospaced))
                            .foregroundStyle(vm.activePersonaCount > 0 ?Color.success : Color.textMuted)
                    }
                }

                ForEach(vm.heartbeatStatus) { persona in
                    personaRow(persona)
                }
            }
        }
    }

    private func personaRow(_ persona: PersonaHeartbeatStatus) -> some View {
        let isRunning = persona.isRunning
        let isActive = persona.inActiveHours

        return HStack(spacing: DesignTokens.Spacing.sm) {
            // Animated status dot
            ZStack {
                if isRunning {
                    Circle()
                        .fill(Color.accent.opacity(0.2))
                        .frame(width: 16, height: 16)
                }
                Circle()
                    .fill(isRunning ?Color.accent : (isActive ?Color.success : .textMuted.opacity(0.3)))
                    .frame(width: 8, height: 8)
            }
            .shadow(color: isRunning ? .accent.opacity(0.5) : .clear, radius: 4)

            Text(persona.displayName)
                .font(.system(size: 13, weight: isRunning ? .semibold : .regular))
                .foregroundStyle(isActive ?Color.textPrimary : Color.textMuted)

            Spacer()

            if isRunning {
                HStack(spacing: 3) {
                    ProgressView()
                        .scaleEffect(0.5)
                        .tint(Color.accent)
                    Text("RUNNING")
                        .font(.system(size: 9, weight: .bold, design: .monospaced))
                        .foregroundStyle(Color.accent)
                }
            } else if isActive {
                Text("ACTIVE")
                    .font(.system(size: 9, weight: .bold, design: .monospaced))
                    .foregroundStyle(.success.opacity(0.8))
            } else {
                Text("IDLE")
                    .font(.system(size: 9, weight: .medium, design: .monospaced))
                    .foregroundStyle(.textMuted.opacity(0.5))
            }
        }
        .padding(.vertical, 2)
    }

    // MARK: - Quick Actions

    private var quickActions: some View {
        GlassCard(accentColor: .accentHover) {
            VStack(alignment: .leading, spacing: DesignTokens.Spacing.md) {
                HStack {
                    ZStack {
                        Circle()
                            .fill(Color.accent.opacity(0.1))
                            .frame(width: 32, height: 32)
                        Image(systemName: "bolt.fill")
                            .font(.system(size: 14, weight: .medium))
                            .foregroundStyle(Color.accent)
                    }
                    Text("Quick Actions")
                        .font(.system(size: DesignTokens.FontSize.title3, weight: .semibold))
                        .foregroundStyle(Color.textPrimary)
                }

                // Primary actions
                HStack(spacing: DesignTokens.Spacing.sm) {
                    gradientActionButton(
                        "Run Pipeline",
                        icon: "play.fill",
                        gradient: .accentGradient
                    ) {
                        await vm.triggerPipeline()
                    }
                    gradientActionButton(
                        "Dry Run",
                        icon: "eye.fill",
                        gradient: .warningGradient
                    ) {
                        await vm.triggerPipeline(dryRun: true)
                    }
                }

                // Secondary actions
                HStack(spacing: DesignTokens.Spacing.sm) {
                    gradientActionButton(
                        "All Personas",
                        icon: "person.3.fill",
                        gradient: .successGradient
                    ) {
                        await vm.triggerAllHeartbeats()
                    }

                    let ksActive = vm.killSwitch?.active ?? false
                    gradientActionButton(
                        ksActive ? "Deactivate" : "Kill Switch",
                        icon: ksActive ? "checkmark.shield.fill" : "exclamationmark.octagon.fill",
                        gradient: ksActive ? .successGradient : .dangerGradient
                    ) {
                        await vm.toggleKillSwitch()
                    }
                }
            }
        }
    }

    private func gradientActionButton(
        _ label: String,
        icon: String,
        gradient: LinearGradient,
        action: @escaping () async -> Void
    ) -> some View {
        Button {
            Task { await action() }
        } label: {
            HStack(spacing: 6) {
                Image(systemName: icon)
                    .font(.system(size: 11, weight: .semibold))
                Text(label)
                    .font(.system(size: 11, weight: .semibold))
            }
            .foregroundStyle(.white)
            .frame(maxWidth: .infinity)
            .padding(.vertical, 11)
            .background(gradient)
            .clipShape(RoundedRectangle(cornerRadius: DesignTokens.Radius.control))
            .shadow(color: .black.opacity(0.3), radius: 4, y: 2)
        }
    }
}

#Preview {
    DashboardView()
        .environment(APIClient())
        .preferredColorScheme(.dark)
}
