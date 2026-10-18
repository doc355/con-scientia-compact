import Foundation

/// A POST that could not reach the gateway, saved to disk so it survives relaunch.
public struct QueuedRequest: Codable, Hashable, Sendable, Identifiable {
    public var id: UUID
    public var path: String
    public var body: Data
    public var createdAt: Date
    public var attempts: Int

    public init(id: UUID = UUID(), path: String, body: Data, createdAt: Date = Date(), attempts: Int = 0) {
        self.id = id; self.path = path; self.body = body; self.createdAt = createdAt; self.attempts = attempts
    }
}

/// Outcome of sending one queued request once the gateway is reachable again.
public struct FlushedRequest: Sendable {
    public var request: QueuedRequest
    public var status: Int
    public var body: Data
}

public struct FlushResult: Sendable {
    public var delivered: [FlushedRequest] = []
    public var remaining: Int = 0
    /// Why flushing stopped early, if it did (still offline, or 401).
    public var stoppedBy: GatewayError?
}

/// FIFO, file-backed. Items leave the queue only when the gateway answered them
/// (any HTTP status except 401). Network failures and 401 keep them, in order.
public actor OfflineQueue {
    public let fileURL: URL
    private var items: [QueuedRequest]

    public init(fileURL: URL = OfflineQueue.defaultURL) {
        self.fileURL = fileURL
        if let d = try? Data(contentsOf: fileURL), let decoded = try? JSONDecoder().decode([QueuedRequest].self, from: d) {
            items = decoded
        } else {
            items = []
        }
    }

    public static var defaultURL: URL {
        let base = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask).first
            ?? FileManager.default.temporaryDirectory
        return base.appendingPathComponent("PI", isDirectory: true).appendingPathComponent("offline-queue.json")
    }

    public var count: Int { items.count }
    public var all: [QueuedRequest] { items }

    public func enqueue(_ r: QueuedRequest) {
        items.append(r)
        save()
    }

    /// Sends queued items in order with `send`. `send` returns (status, body) or throws a transport error.
    public func flush(_ send: @Sendable (QueuedRequest) async throws -> (Int, Data)) async -> FlushResult {
        var result = FlushResult()
        while let next = items.first {
            items[0].attempts += 1
            do {
                let (status, body) = try await send(items[0])
                if status == 401 {
                    result.stoppedBy = .unauthorized
                    break
                }
                result.delivered.append(FlushedRequest(request: next, status: status, body: body))
                items.removeFirst()
            } catch {
                result.stoppedBy = .offline(error.localizedDescription)
                break
            }
        }
        save()
        result.remaining = items.count
        return result
    }

    private func save() {
        do {
            try FileManager.default.createDirectory(at: fileURL.deletingLastPathComponent(), withIntermediateDirectories: true)
            try JSONEncoder().encode(items).write(to: fileURL, options: .atomic)
        } catch {
            // Queue stays in memory; next save retries.
        }
    }
}
