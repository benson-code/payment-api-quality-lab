import Foundation

/// Where the app finds the payment API.
///
/// The API runs on the developer's machine. The iOS simulator shares the Mac's network, so the app
/// reaches it at 127.0.0.1 directly: no forwarding, unlike Android's `adb reverse` (SPEC.md §2). Tests
/// point debug builds elsewhere, for example at the test proxy, with the launch argument
/// `-apiBaseUrl <url>`, the same name as the Android launch extra. Release builds ignore it.
struct ApiConfig: Equatable {
    static let argument = "-apiBaseUrl"
    static let defaultBaseUrl = "http://127.0.0.1:8400"

    let baseUrl: String

    /// [override] is the launch argument's value, or nil. Anything that is not an http(s) URL is ignored.
    static func resolve(_ override: String?, debugBuild: Bool) -> ApiConfig {
        var url = override?.trimmingCharacters(in: .whitespaces)
        while url?.hasSuffix("/") == true { url?.removeLast() }
        let usable = debugBuild && url.map { $0.range(of: #"\Ahttps?://[^/\s]+\z"#, options: .regularExpression) != nil } == true
        return ApiConfig(baseUrl: usable ? url! : defaultBaseUrl)
    }

    /// The configuration this process was launched with.
    static func fromLaunch(_ arguments: [String] = ProcessInfo.processInfo.arguments) -> ApiConfig {
        let value = arguments.firstIndex(of: argument).flatMap { i in i + 1 < arguments.count ? arguments[i + 1] : nil }
        #if DEBUG
        return resolve(value, debugBuild: true)
        #else
        return resolve(value, debugBuild: false)
        #endif
    }
}
