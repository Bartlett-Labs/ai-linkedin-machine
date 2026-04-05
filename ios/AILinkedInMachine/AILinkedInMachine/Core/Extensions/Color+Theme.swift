import SwiftUI

extension Color {
    init(hex: String) {
        let hex = hex.trimmingCharacters(in: CharacterSet.alphanumerics.inverted)
        var int: UInt64 = 0
        Scanner(string: hex).scanHexInt64(&int)
        let r = Double((int >> 16) & 0xFF) / 255.0
        let g = Double((int >> 8) & 0xFF) / 255.0
        let b = Double(int & 0xFF) / 255.0
        self.init(red: r, green: g, blue: b)
    }
}

// MARK: - Design System Color Tokens

extension Color {
    // Surfaces
    static let appBackground    = Color(hex: "090A0B")
    static let surface1         = Color(hex: "111315")
    static let surface2         = Color(hex: "161A1D")
    static let surface3         = Color(hex: "1B2024")
    static let appBorder        = Color(hex: "2A3138")

    // Text
    static let textPrimary      = Color(hex: "F3F5F7")
    static let textSecondary    = Color(hex: "A7B0B8")
    static let textMuted        = Color(hex: "73808C")

    // Accent
    static let accent           = Color(hex: "06B6D4")
    static let accentHover      = Color(hex: "22D3EE")
    static let accentPressed    = Color(hex: "0891B2")
    static let accentDeep       = Color(hex: "0E7490")

    // Semantic
    static let success          = Color(hex: "22C55E")
    static let successDeep      = Color(hex: "16A34A")
    static let warning          = Color(hex: "F59E0B")
    static let warningDeep      = Color(hex: "D97706")
    static let danger           = Color(hex: "EF4444")
    static let dangerDeep       = Color(hex: "DC2626")

    // Glow variants (lower opacity base for shadow/glow effects)
    static let accentGlow       = Color(hex: "06B6D4")
    static let successGlow      = Color(hex: "22C55E")
    static let dangerGlow       = Color(hex: "EF4444")
}

// MARK: - Gradient Presets

extension LinearGradient {
    /// Subtle surface gradient for card backgrounds — adds depth
    static let surfaceGradient = LinearGradient(
        colors: [Color(hex: "131618"), Color(hex: "0F1113")],
        startPoint: .topLeading,
        endPoint: .bottomTrailing
    )

    /// Accent-tinted card border gradient
    static let accentBorderGradient = LinearGradient(
        colors: [
            Color.accent.opacity(0.4),
            Color.accent.opacity(0.08),
            Color.accent.opacity(0.2)
        ],
        startPoint: .topLeading,
        endPoint: .bottomTrailing
    )

    /// Danger glow gradient for kill switch
    static let dangerGradient = LinearGradient(
        colors: [Color.danger, Color.dangerDeep],
        startPoint: .topLeading,
        endPoint: .bottomTrailing
    )

    /// Success gradient for active states
    static let successGradient = LinearGradient(
        colors: [Color.success, Color.successDeep],
        startPoint: .topLeading,
        endPoint: .bottomTrailing
    )

    /// Accent button gradient
    static let accentGradient = LinearGradient(
        colors: [Color.accentHover, Color.accent],
        startPoint: .topLeading,
        endPoint: .bottomTrailing
    )

    /// Warning button gradient
    static let warningGradient = LinearGradient(
        colors: [Color.warning, Color.warningDeep],
        startPoint: .topLeading,
        endPoint: .bottomTrailing
    )
}

// MARK: - Angular Gradient for card borders

extension AngularGradient {
    static let cardBorder = AngularGradient(
        colors: [
            Color.accent.opacity(0.3),
            Color.appBorder.opacity(0.5),
            Color.accent.opacity(0.1),
            Color.appBorder.opacity(0.3),
            Color.accent.opacity(0.3)
        ],
        center: .center
    )
}
