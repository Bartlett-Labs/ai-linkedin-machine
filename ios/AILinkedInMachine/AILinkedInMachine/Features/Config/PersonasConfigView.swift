import SwiftUI

struct PersonasConfigView: View {
    @Environment(APIClient.self) private var apiClient
    @State private var personas: [PersonaSummary] = []

    var body: some View {
        ScrollView {
            VStack(spacing: DesignTokens.Spacing.md) {
                ForEach(personas) { persona in
                    GlassCard {
                        VStack(alignment: .leading, spacing: DesignTokens.Spacing.sm) {
                            HStack {
                                Text(persona.displayName)
                                    .font(.system(size: 15, weight: .medium))
                                    .foregroundStyle(Color.textPrimary)
                                Spacer()
                            }
                            Text(persona.name)
                                .font(.system(size: 11, design: .monospaced))
                                .foregroundStyle(Color.textMuted)
                            Text(persona.persona)
                                .font(.system(size: 13))
                                .foregroundStyle(Color.textSecondary)
                            if let location = persona.location {
                                Label(location, systemImage: "mappin")
                                    .font(.system(size: 11))
                                    .foregroundStyle(Color.textMuted)
                            }
                        }
                    }
                }
            }
            .padding(DesignTokens.Spacing.lg)
        }
        .background(Color.appBackground)
        .task {
            do { personas = try await apiClient.getPersonas() } catch {}
        }
    }
}
