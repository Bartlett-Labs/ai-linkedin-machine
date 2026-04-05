import SwiftUI

struct RulesConfigView: View {
    @Environment(APIClient.self) private var apiClient
    @State private var rules: [ReplyRule] = []
    @State private var safetyTerms: [SafetyTerm] = []
    @State private var selectedTab = 0

    var body: some View {
        VStack(spacing: 0) {
            Picker("", selection: $selectedTab) {
                Text("Reply Rules").tag(0)
                Text("Safety Terms").tag(1)
            }
            .pickerStyle(.segmented)
            .padding(DesignTokens.Spacing.lg)

            if selectedTab == 0 {
                ruleslist
            } else {
                safetyList
            }
        }
        .background(Color.appBackground)
        .task {
            do {
                async let r = apiClient.getReplyRules()
                async let s = apiClient.getSafetyTerms()
                rules = try await r
                safetyTerms = try await s
            } catch {}
        }
    }

    private var ruleslist: some View {
        List {
            ForEach(rules) { rule in
                HStack {
                    VStack(alignment: .leading, spacing: 4) {
                        Text(rule.trigger)
                            .font(.system(size: 13))
                            .foregroundStyle(Color.textPrimary)
                        Text(rule.conditionType)
                            .font(.system(size: 10, design: .monospaced))
                            .foregroundStyle(Color.textMuted)
                    }
                    Spacer()
                    StatusBadge(text: rule.action, color: actionColor(rule.action))
                }
                .listRowBackground(Color.surface1)
                .listRowSeparatorTint(Color.appBorder)
            }
        }
        .listStyle(.plain)
        .scrollContentBackground(.hidden)
    }

    private var safetyList: some View {
        List {
            ForEach(safetyTerms) { term in
                HStack {
                    Text(term.term)
                        .font(.system(size: 13))
                        .foregroundStyle(Color.textPrimary)
                    Spacer()
                    StatusBadge(text: term.response, color: term.response == "BLOCK" ?Color.danger : Color.warning)
                }
                .listRowBackground(Color.surface1)
                .listRowSeparatorTint(Color.appBorder)
            }
        }
        .listStyle(.plain)
        .scrollContentBackground(.hidden)
    }

    private func actionColor(_ action: String) -> Color {
        switch action {
        case "BLOCK": return .danger
        case "REPLY": return .success
        default: return .textMuted
        }
    }
}
