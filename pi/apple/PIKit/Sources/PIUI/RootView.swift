import SwiftUI
import PIKit

/// What each app's WindowGroup shows: Casual View inside a navigation stack.
public struct PIRootView: View {
    @StateObject private var model = PIAppModel()

    public init() {}

    public var body: some View {
        NavigationStack {
            CasualView()
        }
        .environmentObject(model)
    }
}
