import SwiftUI
import PIUI

@main
struct PIVisionApp: App {
    var body: some Scene {
        WindowGroup { PIRootView() }
            .defaultSize(width: 700, height: 900)
    }
}
