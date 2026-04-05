import SwiftUI

/// Premium card component with angular gradient border and Liquid Glass.
/// The accent color tint creates a subtle brand presence on each card.
struct GlassCard<Content: View>: View {
    var accentColor: Color = .accent
    var showAccentBorder: Bool = false
    let content: Content

    init(
        accentColor: Color = .accent,
        showAccentBorder: Bool = false,
        @ViewBuilder content: () -> Content
    ) {
        self.accentColor = accentColor
        self.showAccentBorder = showAccentBorder
        self.content = content()
    }

    var body: some View {
        content
            .padding(DesignTokens.Spacing.lg)
            .background(
                ZStack {
                    // Base surface
                    Color.surface1
                    // Subtle directional gradient for depth
                    LinearGradient(
                        colors: [
                            accentColor.opacity(0.03),
                            .clear,
                            .clear
                        ],
                        startPoint: .topLeading,
                        endPoint: .bottomTrailing
                    )
                }
            )
            .clipShape(RoundedRectangle(cornerRadius: DesignTokens.Radius.card))
            .overlay(
                RoundedRectangle(cornerRadius: DesignTokens.Radius.card)
                    .strokeBorder(
                        showAccentBorder
                            ? AnyShapeStyle(AngularGradient.cardBorder)
                            : AnyShapeStyle(Color.appBorder.opacity(0.6)),
                        lineWidth: showAccentBorder ? 1.5 : 1
                    )
            )
            .shadow(color: .black.opacity(0.2), radius: 8, y: 4)
            .shadow(color: accentColor.opacity(0.04), radius: 12, y: 2)
            .glassEffect(.regular.interactive())
    }
}

/// Highlighted variant for important/actionable cards
struct HighlightCard<Content: View>: View {
    let color: Color
    let content: Content

    init(color: Color = .accent, @ViewBuilder content: () -> Content) {
        self.color = color
        self.content = content()
    }

    var body: some View {
        content
            .padding(DesignTokens.Spacing.lg)
            .background(
                ZStack {
                    Color.surface1
                    LinearGradient(
                        colors: [color.opacity(0.08), color.opacity(0.02)],
                        startPoint: .topLeading,
                        endPoint: .bottomTrailing
                    )
                }
            )
            .clipShape(RoundedRectangle(cornerRadius: DesignTokens.Radius.card))
            .overlay(
                RoundedRectangle(cornerRadius: DesignTokens.Radius.card)
                    .strokeBorder(color.opacity(0.3), lineWidth: 1.5)
            )
            .shadow(color: color.opacity(0.15), radius: 12, y: 4)
            .glassEffect(.regular.interactive())
    }
}

#Preview {
    VStack(spacing: 16) {
        GlassCard {
            VStack(alignment: .leading) {
                Text("Standard Card")
                    .font(.headline)
                    .foregroundStyle(.textPrimary)
                Text("Subtle depth with glass effect")
                    .font(.caption)
                    .foregroundStyle(.textMuted)
            }
        }

        GlassCard(showAccentBorder: true) {
            VStack(alignment: .leading) {
                Text("Accent Border Card")
                    .font(.headline)
                    .foregroundStyle(.textPrimary)
                Text("Angular gradient border for emphasis")
                    .font(.caption)
                    .foregroundStyle(.textMuted)
            }
        }

        HighlightCard(color: .danger) {
            VStack(alignment: .leading) {
                Text("Highlighted Card")
                    .font(.headline)
                    .foregroundStyle(.textPrimary)
                Text("For critical/actionable content")
                    .font(.caption)
                    .foregroundStyle(.textMuted)
            }
        }
    }
    .padding()
    .background(Color.appBackground)
}
