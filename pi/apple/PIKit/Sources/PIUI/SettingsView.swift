import SwiftUI
import PIKit

public struct SettingsView: View {
    @EnvironmentObject var model: PIAppModel
    @State private var token = ""
    @State private var tokenMessage: String?

    public init() {}

    public var body: some View {
        Form {
            Section("Gateway") {
                VoiceTextField("Gateway URL", text: $model.urlString, hint: "For example http://project-iris-1:8784")
                    #if os(iOS) || os(visionOS)
                    .keyboardType(.URL)
                    #endif
                    #if !os(macOS)
                    .textInputAutocapitalization(.never)
                    #endif
                    .autocorrectionDisabled()
                if GatewaySettings.validatedURL(model.urlString) == nil {
                    Label("Not a valid http or https URL.", systemImage: "exclamationmark.triangle").font(.footnote)
                }
                Button { Task { await model.refresh() } } label: {
                    Label("Check connection", systemImage: "arrow.clockwise").largeHitTarget()
                }
                HealthRow()
            }
            Section {
                // Deliberately no dictation on the token field: speaking a secret aloud is unsafe.
                SecureField("Paste token", text: $token)
                    .accessibilityLabel("Gateway token")
                    .accessibilityHint("Stored in the Keychain on this device. Not shown again.")
                Button {
                    model.saveToken(token)
                    token = ""
                    tokenMessage = model.hasToken ? "Token saved to Keychain." : "Token cleared."
                } label: { Label("Save token", systemImage: "key").largeHitTarget() }
                if let tokenMessage { Text(tokenMessage).font(.footnote) }
            } header: { Text("Token") } footer: {
                Text(model.hasToken ? "A token is stored in the Keychain." : "No token stored.")
            }
            Section("Model") {
                if model.models.isEmpty {
                    Text(model.modelsError ?? "Loading models from the gateway…").font(.footnote)
                } else {
                    Picker("Model", selection: $model.model) {
                        ForEach(pickerModels, id: \.self) { Text($0).tag($0) }
                    }
                    .accessibilityHint("Model used for Talk and Chat.")
                }
                VoiceTextField("Model ID", text: $model.model, hint: "backend/model, for example ollama/gpt-oss:20b")
                    .autocorrectionDisabled()
                Button { Task { await model.loadModels() } } label: {
                    Label("Reload models", systemImage: "arrow.clockwise").largeHitTarget()
                }
            }
        }
        .navigationTitle("Settings")
        .task { await model.loadModels() }
    }

    private var pickerModels: [String] {
        model.models.contains(model.model) ? model.models : [model.model] + model.models
    }
}
