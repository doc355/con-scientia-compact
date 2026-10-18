import XCTest
@testable import PIKit

final class GatewayClientTests: XCTestCase {
    let base = URL(string: "http://pi.test:8784")!
    var queueURL: URL!

    override func setUp() {
        queueURL = FileManager.default.temporaryDirectory.appendingPathComponent("piq-\(UUID().uuidString).json")
    }
    override func tearDown() {
        MockURLProtocol.handler = nil
        try? FileManager.default.removeItem(at: queueURL)
    }

    func client(token: String? = "secret-token", queue: OfflineQueue? = nil) -> GatewayClient {
        GatewayClient(baseURL: base, token: token, session: MockURLProtocol.session(), queue: queue)
    }

    // Shapes copied from pi_gateway.py responses.
    let healthJSON = #"{"status":"ok","version":"0.1.0","time":1760800000.5,"backends":{"ollama":"up","exo":"down(502)","moonshot":"not_configured","openrouter":"configured","anthropic":"not_configured"}}"#
    let jobJSON = #"{"id":"abc123","kind":"plaud","payload":{"file":"note.m4a","n":3,"ok":true},"created":1760800000.0,"state":"running","events":[{"state":"queued","detail":"","at":1760800000.0},{"state":"running","detail":"transcribing","at":1760800001.0}]}"#

    // MARK: decoding

    func testHealthDecodesAndSendsNoAuth() async throws {
        MockURLProtocol.handler = { _ in (200, json(self.healthJSON)) }
        let h = try await client().health()
        XCTAssertEqual(h.status, "ok")
        XCTAssertEqual(h.version, "0.1.0")
        XCTAssertEqual(h.backends["exo"], "down(502)")
        XCTAssertEqual(MockURLProtocol.requests.first?.url?.absoluteString, "http://pi.test:8784/health")
        XCTAssertNil(MockURLProtocol.requests.first?.value(forHTTPHeaderField: "Authorization"))
    }

    func testChatEncodesOpenAIShapeAndDecodes() async throws {
        MockURLProtocol.handler = { _ in (200, json(#"{"id":"c1","object":"chat.completion","model":"ollama/gpt-oss:20b","choices":[{"index":0,"message":{"role":"assistant","content":"Hello Doc","reasoning":"..."},"finish_reason":"stop"}],"usage":{"prompt_tokens":5,"completion_tokens":null}}"#)) }
        let r = try await client().chat(ChatRequest(model: "ollama/gpt-oss:20b", messages: [ChatMessage(role: "user", content: "hi")], maxTokens: 16384))
        XCTAssertEqual(r.text, "Hello Doc")
        XCTAssertEqual(r.model, "ollama/gpt-oss:20b")
        XCTAssertEqual(r.usage?.promptTokens, 5)
        XCTAssertNil(r.usage?.completionTokens)
        let req = try XCTUnwrap(MockURLProtocol.requests.first)
        XCTAssertEqual(req.httpMethod, "POST")
        XCTAssertEqual(req.url?.path, "/v1/chat/completions")
        XCTAssertEqual(req.value(forHTTPHeaderField: "Content-Type"), "application/json")
        let body = try XCTUnwrap(JSONSerialization.jsonObject(with: req.httpBody ?? Data()) as? [String: Any])
        XCTAssertEqual(body["model"] as? String, "ollama/gpt-oss:20b")
        XCTAssertEqual(body["max_tokens"] as? Int, 16384)
        let msgs = try XCTUnwrap(body["messages"] as? [[String: Any]])
        XCTAssertEqual(msgs.first?["role"] as? String, "user")
        XCTAssertEqual(msgs.first?["content"] as? String, "hi")
        XCTAssertNil(msgs.first?["id"], "local UUID must not leak into the wire format")
    }

    func testNullContentDecodesAsEmpty() async throws {
        MockURLProtocol.handler = { _ in (200, json(#"{"choices":[{"message":{"role":"assistant","content":null}}]}"#)) }
        let r = try await client().chat(ChatRequest(model: "exo/x", messages: []))
        XCTAssertEqual(r.text, "")
    }

    func testModelsDecode() async throws {
        MockURLProtocol.handler = { _ in (200, json(#"{"object":"list","data":[{"id":"ollama/gpt-oss:20b","object":"model"},{"id":"exo/llama-3.2-1b","object":"model"}]}"#)) }
        let m = try await client().models()
        XCTAssertEqual(m.map(\.id), ["ollama/gpt-oss:20b", "exo/llama-3.2-1b"])
    }

    func testJobsListWithKindQuery() async throws {
        MockURLProtocol.handler = { _ in (200, json("{\"jobs\":[\(self.jobJSON)]}")) }
        let jobs = try await client().jobs(kind: "plaud")
        XCTAssertEqual(jobs.count, 1)
        XCTAssertEqual(jobs[0].state, "running")
        XCTAssertEqual(jobs[0].events.count, 2)
        XCTAssertEqual(jobs[0].payload, .object(["file": .string("note.m4a"), "n": .number(3), "ok": .bool(true)]))
        XCTAssertEqual(MockURLProtocol.requests.first?.url?.absoluteString, "http://pi.test:8784/jobs?kind=plaud")
    }

    func testGetJobCreateJobAddEvent() async throws {
        MockURLProtocol.handler = { req in
            switch (req.httpMethod, req.url?.path) {
            case ("GET", "/jobs/abc123"): return (200, json(self.jobJSON))
            case ("POST", "/jobs"): return (201, json(self.jobJSON))
            case ("POST", "/jobs/abc123/events"): return (200, json(self.jobJSON))
            default: return (404, json(#"{"error":"not found"}"#))
            }
        }
        let c = client()
        let j1 = try await c.job(id: "abc123")
        let j2 = try await c.createJob(kind: "plaud", payload: .object(["file": .string("note.m4a")]))
        let j3 = try await c.addEvent(jobID: "abc123", state: "done", detail: "ok")
        XCTAssertEqual([j1.id, j2.id, j3.id], ["abc123", "abc123", "abc123"])
        let created = try JSONSerialization.jsonObject(with: MockURLProtocol.requests[1].httpBody!) as! [String: Any]
        XCTAssertEqual(created["kind"] as? String, "plaud")
        let ev = try JSONSerialization.jsonObject(with: MockURLProtocol.requests[2].httpBody!) as! [String: Any]
        XCTAssertEqual(ev["state"] as? String, "done")
        XCTAssertEqual(ev["detail"] as? String, "ok")
    }

    func testMalformedJSONIsDecodingError() async {
        MockURLProtocol.handler = { _ in (200, json("not json")) }
        do { _ = try await client().health(); XCTFail("expected error") }
        catch GatewayError.decoding { } catch { XCTFail("wrong error \(error)") }
    }

    // MARK: auth header

    func testBearerTokenOnAuthedRoutes() async throws {
        MockURLProtocol.handler = { _ in (200, json(#"{"object":"list","data":[]}"#)) }
        _ = try await client(token: "tok-123").models()
        XCTAssertEqual(MockURLProtocol.requests.first?.value(forHTTPHeaderField: "Authorization"), "Bearer tok-123")
    }

    func testNoAuthHeaderWhenTokenEmpty() async throws {
        MockURLProtocol.handler = { _ in (200, json(#"{"object":"list","data":[]}"#)) }
        _ = try await client(token: "").models()
        XCTAssertNil(MockURLProtocol.requests.first?.value(forHTTPHeaderField: "Authorization"))
    }

    // MARK: error mapping

    func assertMaps(_ status: Int, _ body: String, to expected: GatewayError, file: StaticString = #filePath, line: UInt = #line) async {
        MockURLProtocol.handler = { _ in (status, json(body)) }
        do { _ = try await client().chat(ChatRequest(model: "ollama/x", messages: [])); XCTFail("expected throw", file: file, line: line) }
        catch let e as GatewayError { XCTAssertEqual(e, expected, file: file, line: line) }
        catch { XCTFail("wrong error \(error)", file: file, line: line) }
    }

    func testErrorMapping() async {
        await assertMaps(401, #"{"error":"unauthorized"}"#, to: .unauthorized)
        await assertMaps(502, #"{"error":"backend unreachable: <urlopen error [Errno 61] Connection refused>"}"#,
                         to: .backendUnreachable("backend unreachable: <urlopen error [Errno 61] Connection refused>"))
        await assertMaps(503, #"{"error":"moonshot not configured: set MOONSHOT_API_KEY on the gateway"}"#,
                         to: .backendNotConfigured("moonshot not configured: set MOONSHOT_API_KEY on the gateway"))
        await assertMaps(400, #"{"error":"model must be '<backend>/<model>'"}"#, to: .badRequest("model must be '<backend>/<model>'"))
        await assertMaps(404, #"{"error":"no such job"}"#, to: .notFound("no such job"))
        await assertMaps(500, "boom", to: .http(500, "boom"))
    }

    func test401OnGetIsUnauthorizedNotQueued() async {
        let q = OfflineQueue(fileURL: queueURL)
        MockURLProtocol.handler = { _ in (401, json(#"{"error":"unauthorized"}"#)) }
        do { _ = try await client(queue: q).jobs(); XCTFail() } catch { XCTAssertEqual(error as? GatewayError, .unauthorized) }
        let n = await q.count
        XCTAssertEqual(n, 0)
    }

    // MARK: offline queue

    func testPostQueuedWhenGatewayUnreachable() async throws {
        let q = OfflineQueue(fileURL: queueURL)
        MockURLProtocol.handler = { _ in throw URLError(.cannotConnectToHost) }
        do { _ = try await client(queue: q).createJob(kind: "note"); XCTFail("expected queuedOffline") }
        catch GatewayError.queuedOffline { } catch { XCTFail("wrong error \(error)") }
        let n = await q.count
        XCTAssertEqual(n, 1)
        let item = await q.all[0]
        XCTAssertEqual(item.path, "/jobs")
    }

    func testGetWhenUnreachableThrowsOfflineAndIsNotQueued() async {
        let q = OfflineQueue(fileURL: queueURL)
        MockURLProtocol.handler = { _ in throw URLError(.notConnectedToInternet) }
        do { _ = try await client(queue: q).health(); XCTFail() }
        catch GatewayError.offline { } catch { XCTFail("wrong error \(error)") }
        let n = await q.count
        XCTAssertEqual(n, 0)
    }

    func testBackend502IsNotQueued() async {
        let q = OfflineQueue(fileURL: queueURL)
        MockURLProtocol.handler = { _ in (502, json(#"{"error":"backend unreachable"}"#)) }
        do { _ = try await client(queue: q).chat(ChatRequest(model: "ollama/x", messages: [])); XCTFail() }
        catch { XCTAssertEqual(error as? GatewayError, .backendUnreachable("backend unreachable")) }
        let n = await q.count
        XCTAssertEqual(n, 0, "gateway answered, so it was reachable; nothing to retry")
    }

    func testNoQueueWhenOptedOut() async {
        let q = OfflineQueue(fileURL: queueURL)
        MockURLProtocol.handler = { _ in throw URLError(.timedOut) }
        do { _ = try await client(queue: q).createJob(kind: "x", queueIfOffline: false); XCTFail() }
        catch GatewayError.offline { } catch { XCTFail("wrong error \(error)") }
        let n = await q.count
        XCTAssertEqual(n, 0)
    }

    func testFlushDeliversInOrderWithAuthAndPersists() async throws {
        let q = OfflineQueue(fileURL: queueURL)
        let c = client(token: "tok", queue: q)
        MockURLProtocol.handler = { _ in throw URLError(.cannotFindHost) }
        _ = try? await c.createJob(kind: "first")
        _ = try? await c.addEvent(jobID: "abc123", state: "done")
        _ = try? await c.chat(ChatRequest(model: "ollama/x", messages: [ChatMessage(role: "user", content: "q")]))

        // Survives relaunch: a fresh queue on the same file sees all three.
        let reloaded = OfflineQueue(fileURL: queueURL)
        let n0 = await reloaded.count
        XCTAssertEqual(n0, 3)

        MockURLProtocol.handler = { req in
            req.url?.path == "/v1/chat/completions"
                ? (200, json(#"{"choices":[{"message":{"role":"assistant","content":"later answer"}}]}"#))
                : (201, json(self.jobJSON))
        }
        let result = await client(token: "tok", queue: reloaded).flushQueue()
        XCTAssertEqual(result.delivered.map(\.request.path), ["/jobs", "/jobs/abc123/events", "/v1/chat/completions"])
        XCTAssertEqual(result.remaining, 0)
        XCTAssertNil(result.stoppedBy)
        XCTAssertTrue(MockURLProtocol.requests.allSatisfy { $0.value(forHTTPHeaderField: "Authorization") == "Bearer tok" })
        let answer = try GatewayClient.decode(ChatResponse.self, status: result.delivered[2].status, data: result.delivered[2].body)
        XCTAssertEqual(answer.text, "later answer")
        let n1 = await OfflineQueue(fileURL: queueURL).count
        XCTAssertEqual(n1, 0)
    }

    func testFlushStopsAndKeepsOrderWhileStillOffline() async throws {
        let q = OfflineQueue(fileURL: queueURL)
        await q.enqueue(QueuedRequest(path: "/jobs", body: json(#"{"kind":"a"}"#)))
        await q.enqueue(QueuedRequest(path: "/jobs", body: json(#"{"kind":"b"}"#)))
        var calls = 0
        MockURLProtocol.handler = { _ in
            calls += 1
            if calls == 1 { return (201, json(self.jobJSON)) }
            throw URLError(.networkConnectionLost)
        }
        let r = await client(queue: q).flushQueue()
        XCTAssertEqual(r.delivered.count, 1)
        XCTAssertEqual(r.remaining, 1)
        guard case .offline = r.stoppedBy else { return XCTFail("expected offline, got \(String(describing: r.stoppedBy))") }
        let left = await q.all
        XCTAssertEqual(String(data: left[0].body, encoding: .utf8), #"{"kind":"b"}"#)
        XCTAssertEqual(left[0].attempts, 1)
    }

    func testFlushKeepsItemsOn401() async {
        let q = OfflineQueue(fileURL: queueURL)
        await q.enqueue(QueuedRequest(path: "/jobs", body: json(#"{"kind":"a"}"#)))
        MockURLProtocol.handler = { _ in (401, json(#"{"error":"unauthorized"}"#)) }
        let r = await client(queue: q).flushQueue()
        XCTAssertEqual(r.stoppedBy, .unauthorized)
        XCTAssertEqual(r.remaining, 1)
    }

    // MARK: settings / token store

    func testURLValidation() {
        XCTAssertEqual(GatewaySettings.validatedURL(" http://project-iris-1:8784 ")?.host, "project-iris-1")
        XCTAssertNil(GatewaySettings.validatedURL("project-iris-1:8784"))
        XCTAssertNil(GatewaySettings.validatedURL("ftp://x"))
        XCTAssertNil(GatewaySettings.validatedURL(""))
    }

    func testSettingsDefaultsAndOverride() {
        let d = UserDefaults(suiteName: "pikit-test-\(UUID().uuidString)")!
        let s = GatewaySettings(defaults: d)
        XCTAssertEqual(s.urlString, "http://project-iris-1:8784")
        XCTAssertEqual(s.model, "ollama/gpt-oss:20b")
        s.urlString = "http://127.0.0.1:8784"
        XCTAssertEqual(GatewaySettings(defaults: d).urlString, "http://127.0.0.1:8784")
    }

    func testMemoryTokenStore() throws {
        let s = MemoryTokenStore()
        XCTAssertNil(s.read())
        try s.write("abc")
        XCTAssertEqual(s.read(), "abc")
        try s.write(nil)
        XCTAssertNil(s.read())
    }

    func testKeychainTokenStoreRoundTrip() throws {
        let s = KeychainTokenStore(service: "ai.polstar.pi.tests.\(UUID().uuidString)", account: "t")
        try s.write("kc-secret")
        XCTAssertEqual(s.read(), "kc-secret")
        try s.write("kc-secret-2")
        XCTAssertEqual(s.read(), "kc-secret-2")
        try s.write(nil)
        XCTAssertNil(s.read())
    }
}
