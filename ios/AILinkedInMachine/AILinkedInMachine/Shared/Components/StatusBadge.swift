import SwiftUI

struct StatusBadge: View {
    let text: String
    var color: Color? = nil

    private var resolvedColor: Color {
        color ?? DesignTokens.statusColor(for: text)
    }

    private var isActive: Bool {
        let upper = text.uppercased()
        return upper == "RUNNING" || upper == "IN_PROGRESS" || upper == "LIVE"
    }

    var body: some View {
        Text(text.uppercased())
            .font(.system(size: 9, weight: .bold, design: .monospaced))
            .tracking(0.5)
            .foregroundStyle(resolvedColor)
            .padding(.horizontal, 8)
            .padding(.vertical, 4)
            .background(resolvedColor.opacity(0.12))
            .clipShape(Capsule())
            .overlay(
                Capsule().strokeBorder(resolvedColor.opacity(0.2), lineWidth: 1)
            )
            .shadow(color: isActive ? resolvedColor.opacity(0.3) : .clear, radius: isActive ? 6 : 0)
    }
}

#Preview {
    HStack {
        StatusBadge(text: "READY")
        StatusBadge(text: "DONE")
        StatusBadge(text: "FAILED")
        StatusBadge(text: "RUNNING")
        StatusBadge(text: "LIVE")
    }
    .padding()
    .background(Color.appBackground)
}
