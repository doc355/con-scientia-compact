import SwiftUI
import PIKit

public struct ChatView: View {
    @EnvironmentObject var model: PIAppModel
    @StateObject private var speaker = Speaker()
    @State private var draft = ""

    public init() {}

    public var body: some View {
        List {
            Section {
                if model.chat.isEmpty {
                    Text("No messages yet.")
                }
                ForEach(model.chat) { m in
                    VStack(alignment: .leading, spacing: 2) {
                        Text(m.role == "user" ? "You" : "PI").font(.caption.bold())
                        Text(m.content)
                    }
                    .accessibilityElement(children: .combine)
                    .accessibilityLabel("\(m.role == "user" ? "You said" : "PI said"): \(m.content)")
                    .accessibilityAction(named: "Read aloud") { speaker.speak(m.content) }
                }
                if model.isThinking { ProgressView("Thinking…") }
                if let e = model.chatError { Label(e, systemImage: "exclamationmark.triangle").font(.footnote) }
            }
            Section("Message") {
                VoiceTextField("Message PI", text: $draft, hint: "Type or dictate, then tap Send.") { send() }
                Button { send() } label: { Label("Send", systemImage: "paperplane").largeHitTarget() }
                    .disabled(draft.trimmingCharacters(in: .whitespaces).isEmpty || model.isThinking)
                    .accessibilityHint("Sends the message to \(model.model).")
                Text("Model: \(model.model)").font(.footnote)
            }
        }
        .navigationTitle("Chat")
    }

    private func send() {
        let t = draft
        draft = ""
        Task { if let a = await model.ask(t) { speaker.speak(a) } }
    }
}
