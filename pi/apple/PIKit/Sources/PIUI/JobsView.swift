import SwiftUI
import PIKit

public struct JobsView: View {
    @EnvironmentObject var model: PIAppModel
    @State private var kind = ""
    @State private var note = ""
    @State private var message: String?

    public init() {}

    public var body: some View {
        List {
            Section("Jobs") {
                if let e = model.jobsError { Label(e, systemImage: "exclamationmark.triangle").font(.footnote) }
                if model.jobs.isEmpty { Text("No jobs.") }
                ForEach(model.jobs) { job in
                    NavigationLink { JobDetailView(job: job) } label: { JobRow(job: job) }
                }
            }
            Section("New job") {
                VoiceTextField("Kind (for example: note)", text: $kind, hint: "The job kind.")
                VoiceTextField("Note (optional)", text: $note, hint: "Stored in the job payload.")
                Button {
                    Task {
                        message = await model.createJob(kind: kind.trimmingCharacters(in: .whitespaces), note: note) ?? "Job created."
                        if message == "Job created." { kind = ""; note = "" }
                    }
                } label: { Label("Create job", systemImage: "plus.circle").largeHitTarget() }
                    .disabled(kind.trimmingCharacters(in: .whitespaces).isEmpty)
                if let message { Text(message).font(.footnote) }
            }
        }
        .navigationTitle("Jobs")
        .refreshable { await model.refresh() }
    }
}

struct JobDetailView: View {
    @EnvironmentObject var model: PIAppModel
    let job: Job
    @State private var state = ""
    @State private var detail = ""
    @State private var message: String?

    var body: some View {
        List {
            Section("Job") {
                LabeledContent("Kind", value: job.kind)
                LabeledContent("State", value: job.state)
                LabeledContent("Created", value: job.createdDate.formatted(date: .abbreviated, time: .shortened))
                LabeledContent("Payload", value: job.payload.summary)
                LabeledContent("ID", value: job.id)
            }
            Section("Events (append-only)") {
                ForEach(Array(job.events.enumerated()), id: \.offset) { _, e in
                    HStack(alignment: .firstTextBaseline) {
                        Image(systemName: StateStyle.symbol(e.state)).accessibilityHidden(true)
                        VStack(alignment: .leading) {
                            Text(e.state.capitalized)
                            if !e.detail.isEmpty { Text(e.detail).font(.footnote) }
                            Text(Date(timeIntervalSince1970: e.at).formatted(date: .omitted, time: .standard))
                                .font(.caption)
                        }
                    }
                    .accessibilityElement(children: .combine)
                }
            }
            Section("Add event") {
                VoiceTextField("State (for example: done)", text: $state, hint: "New state for this job.")
                VoiceTextField("Detail (optional)", text: $detail, hint: "Free text.")
                Button {
                    Task { message = await model.addEvent(job: job, state: state, detail: detail) ?? "Event added." }
                } label: { Label("Add event", systemImage: "plus.circle").largeHitTarget() }
                    .disabled(state.trimmingCharacters(in: .whitespaces).isEmpty)
                if let message { Text(message).font(.footnote) }
            }
        }
        .navigationTitle(job.kind)
    }
}
