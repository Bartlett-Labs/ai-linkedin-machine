import SwiftUI

struct EngineConfigView: View {
    @Environment(APIClient.self) private var apiClient
    @State private var engine: EngineControl?
    @State private var killSwitch: KillSwitchStatus?
    @State private var isLoading = false
    @State private var isSaving = false

    var body: some View {
        ScrollView {
            VStack(spacing: DesignTokens.Spacing.lg) {
                if let ks = killSwitch {
                    killSwitchCard(ks)
                }
                if let engine {
                    engineControls(engine)
                }
            }
            .padding(DesignTokens.Spacing.lg)
        }
        .background(Color.appBackground)
        .task { await load() }
    }

    private func load() async {
        isLoading = true
        do {
            async let e = apiClient.getEngine()
            async let k = apiClient.getKillSwitch()
            engine = try await e
            killSwitch = try await k
        } catch {}
        isLoading = false
    }

    private func killSwitchCard(_ ks: KillSwitchStatus) -> some View {
        GlassCard {
            HStack {
                VStack(alignment: .leading, spacing: 4) {
                    Text("Kill Switch")
                        .font(.headline)
                        .foregroundStyle(Color.textPrimary)
                    Text(ks.active ? "System is STOPPED" : "System is operational")
                        .font(.caption)
                        .foregroundStyle(ks.active ? Color.danger : Color.success)
                }
                Spacer()
                Button {
                    Task {
                        if ks.active {
                            killSwitch = try? await apiClient.deactivateKillSwitch()
                        } else {
                            killSwitch = try? await apiClient.activateKillSwitch()
                        }
                    }
                } label: {
                    Text(ks.active ? "Deactivate" : "Activate")
                        .font(.system(size: 13, weight: .semibold))
                        .foregroundStyle(.white)
                        .padding(.horizontal, 16)
                        .padding(.vertical, 8)
                        .background(ks.active ? Color.success : Color.danger)
                        .clipShape(Capsule())
                }
            }
        }
    }

    private func engineControls(_ eng: EngineControl) -> some View {
        GlassCard {
            VStack(alignment: .leading, spacing: DesignTokens.Spacing.md) {
                Text("Engine Configuration")
                    .font(.headline)
                    .foregroundStyle(Color.textPrimary)

                configRow("Mode", value: eng.mode)
                configRow("Phase", value: eng.phase)
                configRow("Last Run", value: eng.lastRun?.toDate()?.shortDisplay() ?? "Never")

                Divider().overlay(Color.appBorder)

                toggleItem("Main User Posting", isOn: eng.mainUserPosting) {
                    _ = try? await apiClient.updateEngine(EngineUpdate(mainUserPosting: !eng.mainUserPosting))
                    await load()
                }
                toggleItem("Phantom Engagement", isOn: eng.phantomEngagement) {
                    _ = try? await apiClient.updateEngine(EngineUpdate(phantomEngagement: !eng.phantomEngagement))
                    await load()
                }
                toggleItem("Commenting", isOn: eng.commenting) {
                    _ = try? await apiClient.updateEngine(EngineUpdate(commenting: !eng.commenting))
                    await load()
                }
                toggleItem("Replying", isOn: eng.replying) {
                    _ = try? await apiClient.updateEngine(EngineUpdate(replying: !eng.replying))
                    await load()
                }
            }
        }
    }

    private func configRow(_ label: String, value: String) -> some View {
        HStack {
            Text(label)
                .font(.system(size: 13))
                .foregroundStyle(Color.textMuted)
            Spacer()
            Text(value)
                .font(.system(size: 13, weight: .medium, design: .monospaced))
                .foregroundStyle(Color.textSecondary)
        }
    }

    private func toggleItem(_ label: String, isOn: Bool, action: @escaping () async -> Void) -> some View {
        HStack {
            Text(label)
                .font(.system(size: 13))
                .foregroundStyle(Color.textPrimary)
            Spacer()
            Button {
                Task { await action() }
            } label: {
                Image(systemName: isOn ? "checkmark.circle.fill" : "circle")
                    .foregroundStyle(isOn ? Color.success : Color.textMuted)
                    .font(.system(size: 20))
            }
        }
    }
}
