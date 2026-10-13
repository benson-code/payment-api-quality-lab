import Foundation

/// Dates, IDs and entry types as the screens show them. Same behaviour as web/src/format.js and the
/// Android Formats.kt. The API returns UTC timestamps ("2026-10-10T06:31:12.345+00:00"); they are
/// shown in the device's time zone (SPEC D-03).
enum Formats {
    private static let iso: ISO8601DateFormatter = {
        let f = ISO8601DateFormatter()
        f.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        return f
    }()

    private static func formatter(_ pattern: String) -> DateFormatter {
        let f = DateFormatter()
        f.locale = Locale(identifier: "en_GB")
        f.dateFormat = pattern
        return f
    }

    private static let clock = formatter("HH:mm")
    private static let dayYear = formatter("d MMM yyyy")

    private static func date(_ iso: String) -> Date? { Self.iso.date(from: iso) }

    /// "14:31"
    static func time(_ iso: String) -> String {
        date(iso).map { clock.string(from: $0) } ?? iso
    }

    /// "10 Oct 2026, 14:31"
    static func dateTime(_ iso: String) -> String {
        date(iso).map { dayYear.string(from: $0) + ", " + clock.string(from: $0) } ?? iso
    }

    /// "w_beeb1c2d3e4f4385" -> "w_beeb •••• 4385", as banking apps show account numbers (SPEC D-04).
    static func maskId(_ id: String) -> String {
        id.count > 12 ? "\(id.prefix(6)) •••• \(id.suffix(4))" : id
    }

    private static let types = [
        "TOPUP": "Top-up",
        "PAYMENT": "Payment",
        "REFUND": "Refund",
        "TRANSFER_IN": "Transfer in",
        "TRANSFER_OUT": "Transfer out",
    ]

    /// The ledger's entry types, as the user reads them.
    static func typeLabel(_ type: String) -> String { types[type] ?? type }
}
