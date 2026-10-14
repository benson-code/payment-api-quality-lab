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
    private static let day = formatter("d MMM")
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

    /// The heading a row is grouped under: "Today", "Yesterday", "9 Oct", or "9 Oct 2025" in another
    /// year, by the device's calendar and time zone. `now` decides "today".
    static func dayLabel(_ iso: String, now: Date = Date()) -> String {
        guard let d = date(iso) else { return iso }
        let calendar = Calendar.current
        if calendar.isDate(d, inSameDayAs: now) { return "Today" }
        if let yesterday = calendar.date(byAdding: .day, value: -1, to: now), calendar.isDate(d, inSameDayAs: yesterday) {
            return "Yesterday"
        }
        return calendar.component(.year, from: d) == calendar.component(.year, from: now)
            ? day.string(from: d) : dayYear.string(from: d)
    }

    /// Items grouped by day, keeping their order.
    static func groupByDay<T>(_ items: [T], now: Date = Date(), createdAt: (T) -> String) -> [(label: String, items: [T])] {
        var groups: [(label: String, items: [T])] = []
        for item in items {
            let label = dayLabel(createdAt(item), now: now)
            if let last = groups.last, last.label == label {
                groups[groups.count - 1].items.append(item)
            } else {
                groups.append((label, [item]))
            }
        }
        return groups
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
