import SwiftUI

// MARK: - Design Tokens
// Matches the web dashboard's Premium Operator Console design system.

enum DesignTokens {

    // MARK: - Spacing

    enum Spacing {
        static let xs: CGFloat = 4
        static let sm: CGFloat = 8
        static let md: CGFloat = 12
        static let lg: CGFloat = 16
        static let xl: CGFloat = 24
        static let xxl: CGFloat = 32
        static let xxxl: CGFloat = 48
    }

    // MARK: - Corner Radius

    enum Radius {
        static let control: CGFloat = 10
        static let card: CGFloat = 14
        static let modal: CGFloat = 16
        static let pill: CGFloat = 100
    }

    // MARK: - Font Sizes

    enum FontSize {
        static let caption: CGFloat = 10
        static let footnote: CGFloat = 11
        static let subheadline: CGFloat = 13
        static let body: CGFloat = 15
        static let title3: CGFloat = 18
        static let title2: CGFloat = 22
        static let title1: CGFloat = 28
        static let largeTitle: CGFloat = 34
        static let hero: CGFloat = 42
    }

    // MARK: - Animation

    enum Animation {
        static let fast: SwiftUI.Animation = .easeInOut(duration: 0.2)
        static let standard: SwiftUI.Animation = .easeInOut(duration: 0.35)
        static let slow: SwiftUI.Animation = .easeInOut(duration: 0.6)
        static let spring: SwiftUI.Animation = .spring(response: 0.4, dampingFraction: 0.75)
        static let pulse: SwiftUI.Animation = .easeInOut(duration: 1.5).repeatForever(autoreverses: true)
        static let breathe: SwiftUI.Animation = .easeInOut(duration: 2.0).repeatForever(autoreverses: true)
    }

    // MARK: - Status Colors

    static func statusColor(for status: String) -> Color {
        switch status.uppercased() {
        case "READY", "PENDING":      return .warning
        case "IN_PROGRESS", "RUNNING": return .accent
        case "DONE", "COMPLETED", "OK": return .success
        case "FAILED", "ERROR":       return .danger
        case "SKIPPED":               return .textMuted
        case "LIVE":                  return .accent
        case "DRYRUN", "DRY_RUN":     return .warning
        case "PAUSED":                return .danger
        default:                      return .textMuted
        }
    }

    static func urgencyColor(for urgency: String) -> Color {
        switch urgency.lowercased() {
        case "critical": return .danger
        case "high":     return .warning
        case "normal":   return .accent
        case "low":      return .textMuted
        default:         return .textMuted
        }
    }
}

// MARK: - View Modifiers

/// Subtle inner glow effect for cards
struct GlowBorder: ViewModifier {
    let color: Color
    let radius: CGFloat

    func body(content: Content) -> some View {
        content
            .shadow(color: color.opacity(0.15), radius: radius, x: 0, y: 0)
            .shadow(color: color.opacity(0.05), radius: radius * 2, x: 0, y: 4)
    }
}

/// Pulsing glow animation for active/critical states
struct PulsingGlow: ViewModifier {
    let color: Color
    let isActive: Bool
    @State private var isPulsing = false

    func body(content: Content) -> some View {
        content
            .shadow(
                color: isActive ? color.opacity(isPulsing ? 0.4 : 0.15) : .clear,
                radius: isPulsing ? 12 : 6
            )
            .onAppear {
                guard isActive else { return }
                withAnimation(DesignTokens.Animation.pulse) {
                    isPulsing = true
                }
            }
            .onChange(of: isActive) { _, newValue in
                if newValue {
                    withAnimation(DesignTokens.Animation.pulse) {
                        isPulsing = true
                    }
                } else {
                    isPulsing = false
                }
            }
    }
}

extension View {
    func glowBorder(_ color: Color, radius: CGFloat = 8) -> some View {
        modifier(GlowBorder(color: color, radius: radius))
    }

    func pulsingGlow(_ color: Color, isActive: Bool = true) -> some View {
        modifier(PulsingGlow(color: color, isActive: isActive))
    }
}
