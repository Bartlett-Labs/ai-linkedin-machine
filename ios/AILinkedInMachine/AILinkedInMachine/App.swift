import SwiftUI

@main
struct AILinkedInMachineApp: App {
    @State private var apiClient = APIClient()

    var body: some Scene {
        WindowGroup {
            ContentView()
                .environment(apiClient)
                .preferredColorScheme(.dark)
        }
    }
}

struct ContentView: View {
    var body: some View {
        TabView {
            Tab("Dashboard", systemImage: "gauge.with.dots.needle.bottom.50percent") {
                DashboardView()
            }

            Tab("Queue", systemImage: "tray.full.fill") {
                QueueListView()
            }

            Tab("Alerts", systemImage: "bell.badge.fill") {
                AlertsListView()
            }

            Tab("Activity", systemImage: "chart.bar.fill") {
                ActivityView()
            }

            Tab("Settings", systemImage: "gearshape.fill") {
                ConfigRootView()
            }
        }
        .tint(Color.accent)
    }
}

#Preview {
    ContentView()
        .environment(APIClient())
        .preferredColorScheme(.dark)
}
