import Foundation

#if canImport(Speech) && !os(watchOS)
import Speech
import AVFoundation

/// Voice-to-text on SFSpeechRecognizer. Uses on-device recognition when the device supports it
/// (`isOnDevice` tells you which). Needs NSSpeechRecognitionUsageDescription + NSMicrophoneUsageDescription.
@MainActor
public final class VoiceInput: ObservableObject {
    public static let isSupported = true

    @Published public private(set) var transcript = ""
    @Published public private(set) var isListening = false
    @Published public private(set) var isOnDevice = false
    @Published public private(set) var lastError: String?

    private let recognizer: SFSpeechRecognizer?
    private let engine = AVAudioEngine()
    private var request: SFSpeechAudioBufferRecognitionRequest?
    private var task: SFSpeechRecognitionTask?

    public init(locale: Locale = .current) {
        recognizer = SFSpeechRecognizer(locale: locale) ?? SFSpeechRecognizer()
    }

    /// Asks for speech-recognition and microphone permission. Returns true only if both are granted.
    public func requestPermissions() async -> Bool {
        let speech: SFSpeechRecognizerAuthorizationStatus = await withCheckedContinuation { c in
            SFSpeechRecognizer.requestAuthorization { c.resume(returning: $0) }
        }
        guard speech == .authorized else {
            lastError = "Speech recognition permission is off. Turn it on in Settings, Privacy, Speech Recognition."
            return false
        }
        let mic = await AVAudioApplication.requestRecordPermission()
        guard mic else {
            lastError = "Microphone permission is off. Turn it on in Settings, Privacy, Microphone."
            return false
        }
        return true
    }

    public func start() async {
        guard !isListening else { return }
        lastError = nil
        transcript = ""
        guard await requestPermissions() else { return }
        guard let recognizer, recognizer.isAvailable else {
            lastError = "Speech recognition is not available right now."
            return
        }
        do {
            #if os(iOS) || os(visionOS)
            let session = AVAudioSession.sharedInstance()
            try session.setCategory(.record, mode: .measurement, options: .duckOthers)
            try session.setActive(true, options: .notifyOthersOnDeactivation)
            #endif
            let req = SFSpeechAudioBufferRecognitionRequest()
            req.shouldReportPartialResults = true
            if recognizer.supportsOnDeviceRecognition {
                req.requiresOnDeviceRecognition = true
            }
            isOnDevice = req.requiresOnDeviceRecognition
            request = req
            try Self.installTap(on: engine, feeding: req)
            engine.prepare()
            try engine.start()
            isListening = true
            task = Self.startTask(recognizer, req) { [weak self] text, final, err in
                Task { @MainActor in
                    guard let self else { return }
                    if let text { self.transcript = text }
                    if let err, self.isListening, !final { self.lastError = err }
                    if final { self.finish() }
                }
            }
        } catch {
            lastError = "Could not start listening: \(error.localizedDescription)"
            finish()
        }
    }

    /// Stops listening and returns the transcript so far.
    @discardableResult
    public func stop() -> String {
        request?.endAudio()
        finish()
        return transcript
    }

    private func finish() {
        if engine.isRunning { engine.stop() }
        engine.inputNode.removeTap(onBus: 0)
        task?.cancel()
        task = nil
        request = nil
        isListening = false
        #if os(iOS) || os(visionOS)
        try? AVAudioSession.sharedInstance().setActive(false, options: .notifyOthersOnDeactivation)
        #endif
    }

    // Non-isolated so the audio-thread / recognizer callbacks are not main-actor closures.
    nonisolated private static func installTap(on engine: AVAudioEngine, feeding req: SFSpeechAudioBufferRecognitionRequest) throws {
        let input = engine.inputNode
        let format = input.outputFormat(forBus: 0)
        guard format.sampleRate > 0, format.channelCount > 0 else {
            throw NSError(domain: "VoiceInput", code: 1, userInfo: [NSLocalizedDescriptionKey: "No microphone input available."])
        }
        input.installTap(onBus: 0, bufferSize: 1024, format: format) { buffer, _ in req.append(buffer) }
    }

    nonisolated private static func startTask(_ recognizer: SFSpeechRecognizer, _ req: SFSpeechAudioBufferRecognitionRequest,
                                              _ update: @escaping @Sendable (String?, Bool, String?) -> Void) -> SFSpeechRecognitionTask {
        recognizer.recognitionTask(with: req) { result, error in
            update(result?.bestTranscription.formattedString, result?.isFinal ?? (error != nil), error?.localizedDescription)
        }
    }
}

#else

/// watchOS has no Speech framework. On watchOS, voice input goes through the system dictation
/// that every TextField / TextFieldLink offers; this stub keeps the API shape the same.
@MainActor
public final class VoiceInput: ObservableObject {
    public static let isSupported = false
    @Published public private(set) var transcript = ""
    @Published public private(set) var isListening = false
    @Published public private(set) var isOnDevice = false
    @Published public private(set) var lastError: String?
    public init(locale: Locale = .current) {}
    public func requestPermissions() async -> Bool { false }
    public func start() async { lastError = "Use the system dictation button on this device." }
    @discardableResult public func stop() -> String { transcript }
}

#endif
