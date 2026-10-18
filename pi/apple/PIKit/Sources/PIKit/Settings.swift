import Foundation
import Security

/// Where the bearer token lives. The real app uses `KeychainTokenStore`; tests use `MemoryTokenStore`.
public protocol TokenStore: Sendable {
    func read() -> String?
    func write(_ token: String?) throws
}

public struct KeychainError: Error, Equatable { public let status: OSStatus }

/// Generic-password Keychain item, readable after first unlock, never synced to iCloud.
public struct KeychainTokenStore: TokenStore {
    public let service: String
    public let account: String

    public init(service: String = "ai.polstar.pi.gateway", account: String = "bearer-token") {
        self.service = service; self.account = account
    }

    private var baseQuery: [String: Any] {
        [kSecClass as String: kSecClassGenericPassword,
         kSecAttrService as String: service,
         kSecAttrAccount as String: account]
    }

    public func read() -> String? {
        var q = baseQuery
        q[kSecReturnData as String] = true
        q[kSecMatchLimit as String] = kSecMatchLimitOne
        var out: AnyObject?
        guard SecItemCopyMatching(q as CFDictionary, &out) == errSecSuccess, let d = out as? Data else { return nil }
        return String(data: d, encoding: .utf8)
    }

    public func write(_ token: String?) throws {
        let del = SecItemDelete(baseQuery as CFDictionary)
        guard del == errSecSuccess || del == errSecItemNotFound else { throw KeychainError(status: del) }
        guard let token, !token.isEmpty else { return }
        var q = baseQuery
        q[kSecValueData as String] = Data(token.utf8)
        q[kSecAttrAccessible as String] = kSecAttrAccessibleAfterFirstUnlockThisDeviceOnly
        let st = SecItemAdd(q as CFDictionary, nil)
        guard st == errSecSuccess else { throw KeychainError(status: st) }
    }
}

public final class MemoryTokenStore: TokenStore, @unchecked Sendable {
    private let lock = NSLock()
    private var value: String?
    public init(_ value: String? = nil) { self.value = value }
    public func read() -> String? { lock.lock(); defer { lock.unlock() }; return value }
    public func write(_ token: String?) throws { lock.lock(); value = token; lock.unlock() }
}

/// Non-secret settings in UserDefaults. Launch arguments override them
/// (e.g. `-PIGatewayURL http://127.0.0.1:8784`), which is how the simulator screenshots are pointed at a local gateway.
public struct GatewaySettings: @unchecked Sendable { // UserDefaults is thread-safe
    public static let urlKey = "PIGatewayURL"
    public static let modelKey = "PIModel"

    public let defaults: UserDefaults
    public init(defaults: UserDefaults = .standard) { self.defaults = defaults }

    public var urlString: String {
        get { defaults.string(forKey: Self.urlKey) ?? GatewayClient.defaultURL.absoluteString }
        nonmutating set { defaults.set(newValue, forKey: Self.urlKey) }
    }

    public var model: String {
        get { defaults.string(forKey: Self.modelKey) ?? GatewayClient.defaultModel }
        nonmutating set { defaults.set(newValue, forKey: Self.modelKey) }
    }

    /// nil if the string is not an http(s) URL with a host.
    public static func validatedURL(_ s: String) -> URL? {
        let t = s.trimmingCharacters(in: .whitespacesAndNewlines)
        guard let u = URL(string: t), let scheme = u.scheme?.lowercased(), ["http", "https"].contains(scheme),
              let host = u.host, !host.isEmpty else { return nil }
        return u
    }
}
