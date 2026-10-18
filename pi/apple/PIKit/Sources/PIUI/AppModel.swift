import Foundation
import SwiftUI
import PIKit

/// Shared state for every PI app (iPhone/iPad, Watch, Vision Pro).
@MainActor
public final class PIAppModel: ObservableObject {
    @Published public var urlString: String { didSet { settings.urlString = urlString } }
    @Published public var model: String { didSet { settings.model = model } }
    @Published public private(set) var hasToken: Bool

    @Published public private(set) var health: Health?
    @Published public private(set) var healthError: String?
    @Published public private(set) var jobs: [Job] = []
    @Published public private(set) var jobsError: String?
    @Published public private(set) var models: [String] = []
    @Published public private(set) var modelsError: String?
    @Published public private(set) var pendingCount = 0
    @Published public private(set) var lastRefresh: Date?

    @Published public var chat: [ChatMessage] = []
    @Published public private(set) var isThinking = false
    @Published public private(set) var chatError: String?
    @Published public private(set) var latestQuestion: String?
    @Published public private(set) var latestAnswer: String?

    public let settings: GatewaySettings
    public let tokenStore: TokenStore
    public let queue: OfflineQueue
    private let session: URLSession
    private static let answerKey = "PILatestAnswer", questionKey = "PILatestQuestion"

    public init(settings: GatewaySettings = GatewaySettings(),
                tokenStore: TokenStore = KeychainTokenStore(),
                queue: OfflineQueue = OfflineQueue(),
                session: URLSession = .shared) {
        self.settings = settings
        self.tokenStore = tokenStore
        self.queue = queue
        self.session = session
        urlString = settings.urlString
        model = settings.model
        hasToken = !(tokenStore.read() ?? "").isEmpty
        latestAnswer = settings.defaults.string(forKey: Self.answerKey)
        latestQuestion = settings.defaults.string(forKey: Self.questionKey)
        #if DEBUG
        // Simulator/dev only: `-PISeedToken <token>` stores a token in the Keychain at launch.
        if let i = ProcessInfo.processInfo.arguments.firstIndex(of: "-PISeedToken"),
           i + 1 < ProcessInfo.processInfo.arguments.count {
            try? tokenStore.write(ProcessInfo.processInfo.arguments[i + 1])
            hasToken = true
        }
        #endif
    }

    public var client: GatewayClient? {
        guard let url = GatewaySettings.validatedURL(urlString) else { return nil }
        return GatewayClient(baseURL: url, token: tokenStore.read(), session: session, queue: queue)
    }

    public var isOnline: Bool { health?.status == "ok" }

    public func saveToken(_ token: String) {
        do {
            try tokenStore.write(token.trimmingCharacters(in: .whitespacesAndNewlines))
            hasToken = !(tokenStore.read() ?? "").isEmpty
        } catch {
            healthError = "Could not save the token to the Keychain: \(error)"
        }
    }

    /// Health, then queued POSTs, then jobs.
    public func refresh() async {
        guard let client else {
            healthError = "Gateway URL is not valid. Fix it in Settings."
            return
        }
        do {
            health = try await client.health()
            healthError = nil
        } catch {
            health = nil
            healthError = error.localizedDescription
        }
        if health != nil { await flush(client) }
        pendingCount = await queue.count
        do {
            jobs = try await client.jobs()
            jobsError = nil
        } catch {
            jobsError = error.localizedDescription
        }
        lastRefresh = Date()
    }

    private func flush(_ client: GatewayClient) async {
        let r = await client.flushQueue()
        for d in r.delivered where d.request.path == "/v1/chat/completions" {
            if let resp = try? GatewayClient.decode(ChatResponse.self, status: d.status, data: d.body) {
                setAnswer(resp.text, question: nil)
                chat.append(ChatMessage(role: "assistant", content: resp.text))
            }
        }
    }

    public func loadModels() async {
        guard let client else { return }
        do {
            models = try await client.models().map(\.id)
            modelsError = models.isEmpty ? "The gateway returned no models." : nil
        } catch {
            modelsError = error.localizedDescription
        }
    }

    /// Sends one user turn (with the chat history) and returns the answer, or nil on error/queued.
    @discardableResult
    public func ask(_ text: String) async -> String? {
        let q = text.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !q.isEmpty else { return nil }
        guard let client else { chatError = "Gateway URL is not valid. Fix it in Settings."; return nil }
        let history = chat
        chat.append(ChatMessage(role: "user", content: q))
        latestQuestion = q
        settings.defaults.set(q, forKey: Self.questionKey)
        isThinking = true
        chatError = nil
        defer { isThinking = false }
        do {
            let r = try await client.chat(ChatRequest(model: model, messages: history + [ChatMessage(role: "user", content: q)]))
            chat.append(ChatMessage(role: "assistant", content: r.text))
            setAnswer(r.text, question: q)
            return r.text
        } catch {
            chatError = error.localizedDescription
            pendingCount = await queue.count
            return nil
        }
    }

    private func setAnswer(_ a: String, question: String?) {
        latestAnswer = a
        settings.defaults.set(a, forKey: Self.answerKey)
        if let question { latestQuestion = question; settings.defaults.set(question, forKey: Self.questionKey) }
    }

    public func createJob(kind: String, note: String) async -> String? {
        guard let client else { return "Gateway URL is not valid." }
        do {
            _ = try await client.createJob(kind: kind, payload: .object(note.isEmpty ? [:] : ["note": .string(note)]))
            await refresh()
            return nil
        } catch {
            pendingCount = await queue.count
            return error.localizedDescription
        }
    }

    public func addEvent(job: Job, state: String, detail: String) async -> String? {
        guard let client else { return "Gateway URL is not valid." }
        do {
            _ = try await client.addEvent(jobID: job.id, state: state, detail: detail)
            await refresh()
            return nil
        } catch {
            pendingCount = await queue.count
            return error.localizedDescription
        }
    }
}
