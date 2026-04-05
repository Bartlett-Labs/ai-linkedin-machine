import SwiftUI

struct StatCard: View {
    let title: String
    let value: String
    let icon: String
    var color: Color = .accent
    var subtitle: String? = nil

    var body: some View {
        HStack(spacing: 0) {
            // Left accent strip
            RoundedRectangle(cornerRadius: 2)
                .fill(color)
                .frame(width: 3)
                .padding(.vertical, DesignTokens.Spacing.sm)

            VStack(alignment: .leading, spacing: DesignTokens.Spacing.xs) {
                // Icon with glow
                ZStack {
                    Circle()
                        .fill(color.opacity(0.12))
                        .frame(width: 28, height: 28)
                    Image(systemName: icon)
                        .font(.system(size: 12, weight: .medium))
                        .foregroundStyle(color)
                }
                .shadow(color: color.opacity(0.3), radius: 6)

                Spacer(minLength: DesignTokens.Spacing.xs)

                // Value — large monospaced
                Text(value)
                    .font(.system(size: 26, weight: .bold, design: .monospaced))
                    .foregroundStyle(.textPrimary)
                    .contentTransition(.numericText())

                // Title
                Text(title.uppercased())
                    .font(.system(size: 9, weight: .semibold, design: .default))
                    .foregroundStyle(.textMuted)
                    .tracking(0.8)

                if let subtitle {
                    Text(subtitle)
                        .font(.system(size: 9, design: .monospaced))
                        .foregroundStyle(color.opacity(0.7))
                }
            }
            .padding(.leading, DesignTokens.Spacing.sm)
            .padding(.vertical, DesignTokens.Spacing.md)
            .padding(.trailing, DesignTokens.Spacing.md)
            .frame(maxWidth: .infinity, alignment: .leading)
        }
        .background(
            ZStack {
                Color.surface1
                // Subtle gradient wash from the accent color
                LinearGradient(
                    colors: [color.opacity(0.04), .clear],
                    startPoint: .topLeading,
                    endPoint: .bottomTrailing
                )
            }
        )
        .clipShape(RoundedRectangle(cornerRadius: DesignTokens.Radius.control))
        .overlay(
            RoundedRectangle(cornerRadius: DesignTokens.Radius.control)
                .strokeBorder(color.opacity(0.12), lineWidth: 1)
        )
        .glowBorder(color, radius: 4)
    }
}

#Preview {
    LazyVGrid(columns: [GridItem(.flexible()), GridItem(.flexible())], spacing: 8) {
        StatCard(title: "Comments", value: "12", icon: "bubble.left.fill", color: .accent, subtitle: "+3 today")
        StatCard(title: "Posts", value: "3", icon: "doc.text.fill", color: .success)
        StatCard(title: "Replies", value: "8", icon: "arrowshape.turn.up.left.fill", color: .warning)
        StatCard(title: "Likes", value: "24", icon: "heart.fill", color: .danger)
    }
    .padding()
    .background(Color.appBackground)
}
