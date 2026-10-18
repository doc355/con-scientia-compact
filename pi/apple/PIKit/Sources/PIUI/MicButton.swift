import SwiftUI
import PIKit

/// Text field + mic button. Every text input in PI uses this, so voice-to-text is everywhere.
/// iPhone/iPad/Vision Pro: SFSpeechRecognizer via VoiceInput. Watch: system dictation (TextFieldLink).
public struct VoiceTextField: View {
    let title: String
    @Binding var text: String
    var hint: String
    var onSubmit: (() -> Void)?

    public init(_ title: String, text: Binding<String>, hint: String = "", onSubmit: (() -> Void)? = nil) {
        self.title = title; self._text = text; self.hint = hint; self.onSubmit = onSubmit
    }

    public var body: some View {
        HStack(spacing: 8) {
            TextField(title, text: $text, axis: .vertical)
                .accessibilityLabel(title)
                .accessibilityHint(hint)
                .onSubmit { onSubmit?() }
            MicButton(text: $text, fieldName: title)
        }
    }
}

public struct MicButton: View {
    @Binding var text: String
    let fieldName: String

    #if os(watchOS)
    public var body: some View {
        TextFieldLink(prompt: Text("Speak")) {
            Image(systemName: "mic")
                .imageScale(.large)
                .largeHitTarget()
        } onSubmit: { spoken in
            text = text.isEmpty ? spoken : text + " " + spoken
        }
        .accessibilityLabel("Dictate into \(fieldName)")
        .accessibilityHint("Opens dictation. What you say is added to \(fieldName).")
    }
    #else
    @StateObject private var voice = VoiceInput()
    @State private var before = ""

    public var body: some View {
        Button {
            Task {
                if voice.isListening {
                    voice.stop()
                } else {
                    before = text
                    await voice.start()
                }
            }
        } label: {
            Label(voice.isListening ? "Stop dictation" : "Dictate",
                  systemImage: voice.isListening ? "stop.circle" : "mic")
                .labelStyle(.iconOnly)
                .imageScale(.large)
                .largeHitTarget()
        }
        .buttonStyle(.borderless)
        .accessibilityLabel(voice.isListening ? "Stop dictation into \(fieldName)" : "Dictate into \(fieldName)")
        .accessibilityHint(voice.isListening ? "Stops listening and keeps the text." : "Starts listening. What you say is added to \(fieldName).")
        .onChange(of: voice.transcript) { _, t in
            guard voice.isListening, !t.isEmpty else { return }
            text = before.isEmpty ? t : before + " " + t
        }
        .help(voice.lastError ?? "Dictate")
    }
    #endif
}
