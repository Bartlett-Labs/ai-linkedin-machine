import SwiftUI

struct ConfigSection: Identifiable {
    let id = UUID()
    let title: String
    let icon: String
    let color: Color
    let destination: AnyView
}

struct ConfigRootView: View {
    @Environment(APIClient.self) private var apiClient

    private var sections: [ConfigSection] {
        [
            ConfigSection(title: "Engine", icon: "engine.combustion.fill", color: .accent, destination: AnyView(EngineConfigView())),
            ConfigSection(title: "Schedule", icon: "calendar.badge.clock", color: .success, destination: AnyView(ScheduleConfigView())),
            ConfigSection(title: "Feeds", icon: "antenna.radiowaves.left.and.right", color: .accent, destination: AnyView(FeedsConfigView())),
            ConfigSection(title: "Personas", icon: "person.3.fill", color: .warning, destination: AnyView(PersonasConfigView())),
            ConfigSection(title: "Targets", icon: "target", color: .danger, destination: AnyView(TargetsConfigView())),
            ConfigSection(title: "Templates", icon: "text.bubble.fill", color: .textSecondary, destination: AnyView(TemplatesConfigView())),
            ConfigSection(title: "Rules & Safety", icon: "shield.lefthalf.filled", color: .warning, destination: AnyView(RulesConfigView())),
            ConfigSection(title: "Content Bank", icon: "doc.text.fill", color: .success, destination: AnyView(ContentConfigView())),
            ConfigSection(title: "Persona Scheduler", icon: "clock.arrow.2.circlepath", color: .accent, destination: AnyView(PersonaSchedulerView())),
            ConfigSection(title: "Persona Activity", icon: "chart.bar.xaxis", color: .accent, destination: AnyView(PersonaActivityView())),
            ConfigSection(title: "Leads", icon: "person.crop.square.fill.and.at.rectangle", color: .success, destination: AnyView(LeadsListView())),
            ConfigSection(title: "Connections", icon: "link", color: .accent, destination: AnyView(ConnectionsView())),
        ]
    }

    var body: some View {
        NavigationStack {
            List {
                Section("Operations") {
                    ForEach(sections.prefix(4)) { section in
                        configRow(section)
                    }
                }
                Section("Engagement") {
                    ForEach(sections.dropFirst(4).prefix(4)) { section in
                        configRow(section)
                    }
                }
                Section("More") {
                    ForEach(sections.suffix(4)) { section in
                        configRow(section)
                    }
                }

                Section("System") {
                    serverConfigRow
                }
            }
            .listStyle(.insetGrouped)
            .scrollContentBackground(.hidden)
            .background(Color.appBackground)
            .navigationTitle("Settings")
        }
    }

    private func configRow(_ section: ConfigSection) -> some View {
        NavigationLink {
            section.destination
                .navigationTitle(section.title)
        } label: {
            Label {
                Text(section.title)
                    .foregroundStyle(.textPrimary)
            } icon: {
                Image(systemName: section.icon)
                    .foregroundStyle(section.color)
            }
        }
        .listRowBackground(Color.surface1)
    }

    @State private var serverURL = ""
    @State private var serverKey = ""

    private var serverConfigRow: some View {
        Group {
            VStack(alignment: .leading, spacing: DesignTokens.Spacing.sm) {
                Text("API Server")
                    .font(.system(size: 13, weight: .medium))
                    .foregroundStyle(.textPrimary)
                TextField("http://localhost:8000", text: $serverURL)
                    .font(.system(size: 12, design: .monospaced))
                    .textFieldStyle(.roundedBorder)
                    .onAppear { serverURL = apiClient.baseURL }
                    .onSubmit { apiClient.baseURL = serverURL }
            }
            VStack(alignment: .leading, spacing: DesignTokens.Spacing.sm) {
                Text("API Key")
                    .font(.system(size: 13, weight: .medium))
                    .foregroundStyle(.textPrimary)
                SecureField("Optional", text: $serverKey)
                    .font(.system(size: 12, design: .monospaced))
                    .textFieldStyle(.roundedBorder)
                    .onAppear { serverKey = apiClient.apiKey }
                    .onSubmit { apiClient.apiKey = serverKey }
            }
        }
        .listRowBackground(Color.surface1)
    }
}
