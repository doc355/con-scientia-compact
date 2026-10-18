import SwiftUI
import PIKit

/// Launch screen on every platform: calm summary of PI + one large Talk button.
public struct CasualView: View {
    @EnvironmentObject var model: PIAppModel
    @Environment(\.accessibilityReduceMotion) private var reduceMotion

    public init() {}

    public var body: some View {
        List {
            Section {
                TalkButton()
            }
            Section {
                HealthRow()
                if model.pendingCount > 0 {
                    Label("\(model.pendingCount) waiting to send (offline queue)", systemImage: "tray.full")
                        .accessibilityLabel("\(model.pendingCount) requests waiting in the offline queue")
                }
            } header: { SectionHeader("PI status") }
            .headerProminence(.increased)
            Section {
                if let a = model.latestAnswer, !a.isEmpty {
                    if let q = model.latestQuestion {
                        Text("You asked: \(q)")
                            .fixedSize(horizontal: false, vertical: true)
                            .accessibilityLabel("You asked: \(q)")
                    }
                    Text(a)
                        .fixedSize(horizontal: false, vertical: true)
                        .accessibilityLabel("Latest answer: \(a)")
                } else {
                    Text("No answers yet. Tap Talk to ask PI something.")
                        .fixedSize(horizontal: false, vertical: true)
                }
            } header: { SectionHeader("Latest answer") }
            .headerProminence(.increased)
            Section {
                if model.jobs.isEmpty {
                    Text(model.jobsError ?? "No jobs yet.")
                } else {
                    ForEach(model.jobs.prefix(3)) { job in JobRow(job: job) }
                }
            } header: { SectionHeader("Recent jobs") }
            .headerProminence(.increased)
            Section {
                NavigationLink { ChatView() } label: { Label("Chat", systemImage: "bubble.left.and.bubble.right").largeHitTarget() }
                    .accessibilityHint("Opens the full conversation.")
                    .accessibilityIdentifier("nav.chat")
                NavigationLink { JobsView() } label: { Label("Jobs", systemImage: "list.bullet.rectangle").largeHitTarget() }
                    .accessibilityHint("Opens all jobs and lets you add one.")
                    .accessibilityIdentifier("nav.jobs")
                NavigationLink { SettingsView() } label: { Label("Settings", systemImage: "gearshape").largeHitTarget() }
                    .accessibilityHint("Gateway address, token and model.")
                    .accessibilityIdentifier("nav.settings")
            } header: { SectionHeader("More") }
            .headerProminence(.increased)
        }
        .navigationTitle("PI")
        .refreshable { await model.refresh() }
        .task { await model.refresh() }
    }
}

struct HealthRow: View {
    @EnvironmentObject var model: PIAppModel

    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            if let h = model.health {
                Label("Gateway online (v\(h.version))", systemImage: "checkmark.circle")
                    .font(.headline)
                Text(h.backends.keys.sorted().map { "\($0): \(h.backends[$0]!)" }.joined(separator: ", "))
                    .font(.footnote)
            } else if let e = model.healthError {
                Label("Gateway offline", systemImage: "xmark.octagon").font(.headline)
                Text(e).font(.footnote)
            } else {
                Label("Checking gateway…", systemImage: "hourglass").font(.headline)
            }
            if let r = model.lastRefresh {
                Text("Checked \(relative(r))").font(.caption)
            }
        }
        .accessibilityElement(children: .combine)
        .accessibilityHint("Pull down to check again.")
    }
}

struct JobRow: View {
    let job: Job
    var body: some View {
        HStack(alignment: .firstTextBaseline) {
            Image(systemName: StateStyle.symbol(job.state)).accessibilityHidden(true)
            VStack(alignment: .leading) {
                Text(job.kind).font(.body)
                Text("\(job.state.capitalized) · \(relative(job.createdDate))").font(.footnote)
            }
        }
        .accessibilityElement(children: .combine)
        .accessibilityLabel("Job \(job.kind), state \(job.state), created \(relative(job.createdDate))")
    }
}

/// The one big button: listen → ask → show and speak the answer.
struct TalkButton: View {
    @EnvironmentObject var model: PIAppModel
    @StateObject private var voice = VoiceInput()
    @StateObject private var speaker = Speaker()
    @State private var typed = ""

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            #if os(watchOS)
            TextFieldLink(prompt: Text("Ask PI")) {
                talkLabel(title: model.isThinking ? "Thinking…" : "Talk", symbol: "mic.fill")
            } onSubmit: { spoken in
                Task { await send(spoken) }
            }
            .disabled(model.isThinking)
            .accessibilityLabel(model.isThinking ? "PI is thinking" : "Talk to PI")
            .accessibilityHint("Opens dictation. PI answers and reads the answer aloud.")
            #else
            Button {
                Task { await toggle() }
            } label: {
                talkLabel(title: title, symbol: voice.isListening ? "stop.fill" : "mic.fill")
            }
            .buttonStyle(.borderedProminent)
            .controlSize(.large)
            .disabled(model.isThinking)
            .accessibilityLabel(title)
            .accessibilityHint(voice.isListening ? "Stops listening and sends what you said to PI."
                                                 : "Starts listening. Tap again to send. PI answers and reads the answer aloud.")
            if voice.isListening || !voice.transcript.isEmpty {
                Text(voice.transcript.isEmpty ? "Listening…" : "“\(voice.transcript)”")
                    .font(.body)
                    .accessibilityLabel(voice.transcript.isEmpty ? "Listening" : "Heard: \(voice.transcript)")
            }
            if let e = voice.lastError {
                Text(e).font(.footnote)
                VoiceTextField("Type a question instead", text: $typed, hint: "Then press return to send.") {
                    let t = typed; typed = ""
                    Task { await send(t) }
                }
            }
            #endif
            if model.isThinking {
                ProgressView("Thinking…").accessibilityLabel("PI is thinking")
            }
            if let e = model.chatError {
                Label(e, systemImage: "exclamationmark.triangle").font(.footnote)
            }
            if speaker.isSpeaking {
                Button { speaker.stop() } label: { Label("Stop reading aloud", systemImage: "speaker.slash").largeHitTarget() }
                    .accessibilityHint("Stops the spoken answer.")
            }
        }
    }

    private var title: String {
        if model.isThinking { return "Thinking…" }
        return voice.isListening ? "Stop and send" : "Talk"
    }

    private func talkLabel(title: String, symbol: String) -> some View {
        Label(title, systemImage: symbol)
            .font(.title2.bold())
            .frame(maxWidth: .infinity, minHeight: 72)
            .contentShape(Rectangle())
    }

    private func toggle() async {
        if voice.isListening {
            let text = voice.stop()
            await send(text)
        } else {
            speaker.stop()
            await voice.start()
        }
    }

    private func send(_ text: String) async {
        if let answer = await model.ask(text) { speaker.speak(answer) }
    }
}
