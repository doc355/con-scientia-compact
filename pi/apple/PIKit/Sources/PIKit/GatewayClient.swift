import Foundation

/// async/await client for the PI Core Gateway (pi/gateway/pi_gateway.py).
public struct GatewayClient: Sendable {
    public static let defaultURL = URL(string: "http://project-iris-1:8784")!
    public static let defaultModel = "ollama/gpt-oss:20b"

    public let baseURL: URL
    public let token: String?
    public let session: URLSession
    public let queue: OfflineQueue?
    /// Chat on thinking models can take minutes; the gateway allows 600 s to the backend.
    public var chatTimeout: TimeInterval = 600
    public var defaultTimeout: TimeInterval = 30

    public init(baseURL: URL = GatewayClient.defaultURL, token: String?, session: URLSession = .shared, queue: OfflineQueue? = nil) {
        self.baseURL = baseURL; self.token = token; self.session = session; self.queue = queue
    }

    // MARK: Endpoints

    /// GET /health (no auth).
    public func health() async throws -> Health {
        try await get("/health", auth: false)
    }

    /// GET /v1/models
    public func models() async throws -> [ModelInfo] {
        let list: ModelList = try await get("/v1/models")
        return list.data
    }

    /// POST /v1/chat/completions. If the gateway is unreachable and `queueIfOffline`, the request is queued
    /// and `GatewayError.queuedOffline` is thrown; the answer arrives later via `flushQueue()`.
    public func chat(_ request: ChatRequest, queueIfOffline: Bool = true) async throws -> ChatResponse {
        try await post("/v1/chat/completions", body: request, timeout: chatTimeout, queueIfOffline: queueIfOffline)
    }

    /// Convenience: one question, one answer string.
    public func ask(_ text: String, model: String = GatewayClient.defaultModel, history: [ChatMessage] = []) async throws -> String {
        try await chat(ChatRequest(model: model, messages: history + [ChatMessage(role: "user", content: text)])).text
    }

    /// POST /jobs {kind, payload}
    public func createJob(kind: String, payload: JSONValue = .object([:]), queueIfOffline: Bool = true) async throws -> Job {
        try await post("/jobs", body: NewJob(kind: kind, payload: payload), queueIfOffline: queueIfOffline)
    }

    /// GET /jobs?kind=
    public func jobs(kind: String? = nil) async throws -> [Job] {
        var path = "/jobs"
        if let kind, !kind.isEmpty,
           let enc = kind.addingPercentEncoding(withAllowedCharacters: .urlQueryAllowed.subtracting(CharacterSet(charactersIn: "&=+"))) {
            path += "?kind=\(enc)"
        }
        let list: JobList = try await get(path)
        return list.jobs
    }

    /// GET /jobs/<id>
    public func job(id: String) async throws -> Job {
        try await get("/jobs/\(id)")
    }

    /// POST /jobs/<id>/events {state, detail}
    public func addEvent(jobID: String, state: String, detail: String = "", queueIfOffline: Bool = true) async throws -> Job {
        try await post("/jobs/\(jobID)/events", body: NewEvent(state: state, detail: detail), queueIfOffline: queueIfOffline)
    }

    /// Retries queued POSTs in order. Safe to call often (e.g. on launch, on network change, on refresh).
    public func flushQueue() async -> FlushResult {
        guard let queue else { return FlushResult() }
        let client = self
        return await queue.flush { item in
            let req = try client.makeRequest(path: item.path, method: "POST", body: item.body, auth: true,
                                             timeout: item.path.hasPrefix("/v1/chat") ? client.chatTimeout : client.defaultTimeout)
            let (data, resp) = try await client.session.data(for: req)
            return ((resp as? HTTPURLResponse)?.statusCode ?? 0, data)
        }
    }

    // MARK: Plumbing

    func makeRequest(path: String, method: String, body: Data?, auth: Bool, timeout: TimeInterval) throws -> URLRequest {
        guard let url = URL(string: path, relativeTo: baseURL)?.absoluteURL,
              let scheme = url.scheme, ["http", "https"].contains(scheme) else {
            throw GatewayError.invalidURL(baseURL.absoluteString + path)
        }
        var r = URLRequest(url: url, timeoutInterval: timeout)
        r.httpMethod = method
        r.setValue("application/json", forHTTPHeaderField: "Accept")
        if let body {
            r.httpBody = body
            r.setValue("application/json", forHTTPHeaderField: "Content-Type")
        }
        if auth, let token, !token.isEmpty {
            r.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }
        return r
    }

    func get<T: Decodable>(_ path: String, auth: Bool = true) async throws -> T {
        let req = try makeRequest(path: path, method: "GET", body: nil, auth: auth, timeout: defaultTimeout)
        let (data, status) = try await send(req)
        return try Self.decode(T.self, status: status, data: data)
    }

    func post<B: Encodable, T: Decodable>(_ path: String, body: B, timeout: TimeInterval? = nil, queueIfOffline: Bool) async throws -> T {
        let bodyData = try JSONEncoder().encode(body)
        let req = try makeRequest(path: path, method: "POST", body: bodyData, auth: true, timeout: timeout ?? defaultTimeout)
        do {
            let (data, status) = try await send(req)
            return try Self.decode(T.self, status: status, data: data)
        } catch GatewayError.offline(let why) {
            guard queueIfOffline, let queue else { throw GatewayError.offline(why) }
            let item = QueuedRequest(path: path, body: bodyData)
            await queue.enqueue(item)
            throw GatewayError.queuedOffline(item.id)
        }
    }

    func send(_ req: URLRequest) async throws -> (Data, Int) {
        do {
            let (data, resp) = try await session.data(for: req)
            return (data, (resp as? HTTPURLResponse)?.statusCode ?? 0)
        } catch where GatewayError.isUnreachable(error) {
            throw GatewayError.offline(error.localizedDescription)
        }
    }

    public static func decode<T: Decodable>(_ type: T.Type, status: Int, data: Data) throws -> T {
        guard (200..<300).contains(status) else { throw GatewayError.from(status: status, body: data) }
        do {
            return try JSONDecoder().decode(T.self, from: data)
        } catch {
            throw GatewayError.decoding(String(describing: error))
        }
    }
}
