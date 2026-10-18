import Foundation

public enum GatewayError: Error, Equatable, LocalizedError, Sendable {
    case invalidURL(String)
    case unauthorized
    case badRequest(String)
    case notFound(String)
    /// 502: the gateway is up but the model backend (ollama, exo, ...) is unreachable.
    case backendUnreachable(String)
    /// 503: the backend is not configured on the gateway (missing API key).
    case backendNotConfigured(String)
    case http(Int, String)
    /// The gateway itself could not be reached (network / Tailscale down).
    case offline(String)
    /// A POST could not reach the gateway and was saved in the offline queue.
    case queuedOffline(UUID)
    case decoding(String)

    public var errorDescription: String? {
        switch self {
        case .invalidURL(let s): return "Gateway URL is not valid: \(s)"
        case .unauthorized: return "The gateway rejected the token (401). Check the token in Settings."
        case .badRequest(let m): return "Bad request (400): \(m)"
        case .notFound(let m): return "Not found (404): \(m)"
        case .backendUnreachable(let m): return "Gateway is up, but the model backend is unreachable (502): \(m)"
        case .backendNotConfigured(let m): return "Backend not configured on the gateway (503): \(m)"
        case .http(let c, let m): return "Gateway error \(c): \(m)"
        case .offline(let m): return "Gateway unreachable: \(m)"
        case .queuedOffline: return "Gateway unreachable. Saved to the offline queue; it will be sent when the gateway is back."
        case .decoding(let m): return "Could not read the gateway response: \(m)"
        }
    }

    static func from(status: Int, body: Data) -> GatewayError {
        let msg = (try? JSONDecoder().decode(ErrorBody.self, from: body))?.error
            ?? String(data: body, encoding: .utf8) ?? ""
        switch status {
        case 401: return .unauthorized
        case 400: return .badRequest(msg)
        case 404: return .notFound(msg)
        case 502: return .backendUnreachable(msg)
        case 503: return .backendNotConfigured(msg)
        default: return .http(status, msg)
        }
    }

    /// URL errors that mean "the gateway is not reachable right now" (worth queueing and retrying).
    static func isUnreachable(_ error: Error) -> Bool {
        guard let u = error as? URLError else { return false }
        switch u.code {
        case .notConnectedToInternet, .cannotConnectToHost, .cannotFindHost, .timedOut,
             .networkConnectionLost, .dnsLookupFailed, .internationalRoamingOff, .dataNotAllowed,
             .secureConnectionFailed, .callIsActive:
            return true
        default:
            return false
        }
    }
}
