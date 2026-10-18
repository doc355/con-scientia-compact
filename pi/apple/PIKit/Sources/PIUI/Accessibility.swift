import SwiftUI
import PIKit

/// Job states as words + a distinct symbol shape (never color alone).
public enum StateStyle {
    public static func symbol(_ state: String) -> String {
        switch state.lowercased() {
        case "queued": return "clock"
        case "running", "working", "transcribing": return "arrow.triangle.2.circlepath"
        case "done", "ok", "complete", "completed", "succeeded": return "checkmark.circle"
        case "failed", "error": return "xmark.octagon"
        case "cancelled", "canceled": return "minus.circle"
        default: return "info.circle"
        }
    }
}

struct LargeHitTarget: ViewModifier {
    func body(content: Content) -> some View {
        content.frame(minWidth: 44, minHeight: 44).contentShape(Rectangle())
    }
}

extension View {
    func largeHitTarget() -> some View { modifier(LargeHitTarget()) }
}

func relative(_ d: Date) -> String {
    let f = RelativeDateTimeFormatter()
    f.unitsStyle = .full
    return f.localizedString(for: d, relativeTo: Date())
}

/// Full-contrast section header (the default grey header failed the contrast audit).
struct SectionHeader: View {
    let title: String
    init(_ title: String) { self.title = title }
    var body: some View {
        Text(title).font(.headline).foregroundColor(.primary).textCase(nil).accessibilityAddTraits(.isHeader)
    }
}
