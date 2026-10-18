import Foundation

/// Arbitrary JSON (job payloads are free-form on the gateway).
public enum JSONValue: Codable, Hashable, Sendable {
    case string(String), number(Double), bool(Bool), object([String: JSONValue]), array([JSONValue]), null

    public init(from decoder: Decoder) throws {
        let c = try decoder.singleValueContainer()
        if c.decodeNil() { self = .null }
        else if let b = try? c.decode(Bool.self) { self = .bool(b) }
        else if let n = try? c.decode(Double.self) { self = .number(n) }
        else if let s = try? c.decode(String.self) { self = .string(s) }
        else if let a = try? c.decode([JSONValue].self) { self = .array(a) }
        else { self = .object(try c.decode([String: JSONValue].self)) }
    }

    public func encode(to encoder: Encoder) throws {
        var c = encoder.singleValueContainer()
        switch self {
        case .string(let s): try c.encode(s)
        case .number(let n): try c.encode(n)
        case .bool(let b): try c.encode(b)
        case .object(let o): try c.encode(o)
        case .array(let a): try c.encode(a)
        case .null: try c.encodeNil()
        }
    }

    /// Short human-readable rendering for lists and VoiceOver.
    public var summary: String {
        switch self {
        case .string(let s): return s
        case .number(let n): return n.rounded() == n ? String(Int(n)) : String(n)
        case .bool(let b): return b ? "true" : "false"
        case .null: return "null"
        case .array(let a): return a.map(\.summary).joined(separator: ", ")
        case .object(let o): return o.keys.sorted().map { "\($0): \(o[$0]!.summary)" }.joined(separator: "; ")
        }
    }
}

public struct Health: Codable, Hashable, Sendable {
    public var status: String
    public var version: String
    public var time: Double
    public var backends: [String: String]
}

public struct ChatMessage: Codable, Hashable, Sendable, Identifiable {
    public var id: UUID = UUID()
    public var role: String
    public var content: String

    public init(role: String, content: String) { self.role = role; self.content = content }

    enum CodingKeys: String, CodingKey { case role, content }

    public init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        role = try c.decode(String.self, forKey: .role)
        content = try c.decodeIfPresent(String.self, forKey: .content) ?? ""
    }

    public func encode(to encoder: Encoder) throws {
        var c = encoder.container(keyedBy: CodingKeys.self)
        try c.encode(role, forKey: .role)
        try c.encode(content, forKey: .content)
    }
}

public struct ChatRequest: Codable, Hashable, Sendable {
    public var model: String
    public var messages: [ChatMessage]
    public var maxTokens: Int?
    public var temperature: Double?

    public init(model: String, messages: [ChatMessage], maxTokens: Int? = nil, temperature: Double? = nil) {
        self.model = model; self.messages = messages; self.maxTokens = maxTokens; self.temperature = temperature
    }

    enum CodingKeys: String, CodingKey { case model, messages, temperature, maxTokens = "max_tokens" }
}

public struct ChatResponse: Codable, Hashable, Sendable {
    public struct Choice: Codable, Hashable, Sendable {
        public var index: Int?
        public var message: ChatMessage
        public var finishReason: String?
        enum CodingKeys: String, CodingKey { case index, message, finishReason = "finish_reason" }
    }
    public struct Usage: Codable, Hashable, Sendable {
        public var promptTokens: Int?
        public var completionTokens: Int?
        enum CodingKeys: String, CodingKey { case promptTokens = "prompt_tokens", completionTokens = "completion_tokens" }
    }
    public var id: String?
    public var model: String?
    public var choices: [Choice]
    public var usage: Usage?

    public var text: String { choices.first?.message.content ?? "" }
}

public struct ModelInfo: Codable, Hashable, Sendable, Identifiable {
    public var id: String
    public var object: String?
}

public struct ModelList: Codable, Hashable, Sendable {
    public var data: [ModelInfo]
}

public struct JobEvent: Codable, Hashable, Sendable {
    public var state: String
    public var detail: String
    public var at: Double
}

public struct Job: Codable, Hashable, Sendable, Identifiable {
    public var id: String
    public var kind: String
    public var payload: JSONValue
    public var created: Double
    public var state: String
    public var events: [JobEvent]

    public var createdDate: Date { Date(timeIntervalSince1970: created) }
}

public struct JobList: Codable, Hashable, Sendable {
    public var jobs: [Job]
}

public struct NewJob: Codable, Hashable, Sendable {
    public var kind: String
    public var payload: JSONValue
    public init(kind: String, payload: JSONValue) { self.kind = kind; self.payload = payload }
}

public struct NewEvent: Codable, Hashable, Sendable {
    public var state: String
    public var detail: String
    public init(state: String, detail: String) { self.state = state; self.detail = detail }
}

struct ErrorBody: Decodable { var error: String? }
