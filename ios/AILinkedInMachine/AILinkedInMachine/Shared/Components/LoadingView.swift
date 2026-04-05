import SwiftUI

struct LoadingView: View {
    var message: String = "Loading..."

    var body: some View {
        VStack(spacing: DesignTokens.Spacing.md) {
            ProgressView()
                .tint(.accent)
            Text(message)
                .font(.caption)
                .foregroundStyle(Color.textMuted)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }
}

/// Displays content with pull-to-refresh and loading/error states.
struct AsyncContentView<T, Content: View>: View {
    let loadingMessage: String
    let error: Error?
    let data: T?
    let retry: () async -> Void
    @ViewBuilder let content: (T) -> Content

    init(
        _ data: T?,
        error: Error? = nil,
        loadingMessage: String = "Loading...",
        retry: @escaping () async -> Void,
        @ViewBuilder content: @escaping (T) -> Content
    ) {
        self.data = data
        self.error = error
        self.loadingMessage = loadingMessage
        self.retry = retry
        self.content = content
    }

    var body: some View {
        Group {
            if let error {
                VStack(spacing: DesignTokens.Spacing.md) {
                    Image(systemName: "exclamationmark.triangle")
                        .font(.largeTitle)
                        .foregroundStyle(Color.danger)
                    Text(error.localizedDescription)
                        .font(.caption)
                        .foregroundStyle(Color.textMuted)
                        .multilineTextAlignment(.center)
                    Button("Retry") {
                        Task { await retry() }
                    }
                    .buttonStyle(.borderedProminent)
                    .tint(.accent)
                }
                .frame(maxWidth: .infinity, maxHeight: .infinity)
            } else if let data {
                content(data)
            } else {
                LoadingView(message: loadingMessage)
            }
        }
    }
}

#Preview {
    LoadingView()
        .background(Color.appBackground)
}
