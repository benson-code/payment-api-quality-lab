import Observation
import SwiftUI

/// History tab: the ledger, newest first, grouped by day (SPEC.md §7.3, D-03, D-05). Same behaviour
/// as web/src/screens/History.jsx and the Android HistoryScreen.kt.
@Observable
final class HistoryModel {
    private(set) var entries: [Entry]?
    private(set) var error: String?
    private let api: ApiClient
    private let walletId: String

    init(api: ApiClient, walletId: String) {
        self.api = api
        self.walletId = walletId
    }

    /// Called each time the screen is shown, so a refund just made appears on return.
    func load() async {
        switch await api.transactions(walletId) {
        case .ok(let rows, _): entries = rows.reversed(); error = nil
        case .refused(_, let code, _): error = Messages.forCode(code)
        case .noAnswer: error = Messages.noAnswer
        }
    }
}

struct HistoryView: View {
    let onHome: () -> Void
    let onPay: () -> Void
    let onOpenPayment: (_ paymentId: String) -> Void
    @State private var model: HistoryModel

    init(api: ApiClient, walletId: String, onHome: @escaping () -> Void, onPay: @escaping () -> Void,
         onOpenPayment: @escaping (String) -> Void) {
        self.onHome = onHome
        self.onPay = onPay
        self.onOpenPayment = onOpenPayment
        _model = State(initialValue: HistoryModel(api: api, walletId: walletId))
    }

    var body: some View {
        Screen(title: "History", tabBar: TabBar(active: .history) { tab in
            switch tab {
            case .home: onHome
            case .pay: onPay
            case .history: nil
            }
        }) {
            if let error = model.error {
                Message(kind: .error, text: error, testTag: "error-message")
            }
            if let entries = model.entries {
                if entries.isEmpty {
                    WalletCard {
                        Text("No transactions yet.").walletText(WalletType.body).foregroundStyle(WalletColors.textSecondary)
                            .frame(maxWidth: .infinity)
                            .accessibilityIdentifier("empty")
                    }
                }
                ForEach(Formats.groupByDay(entries) { $0.createdAt }, id: \.label) { group in
                    VStack(alignment: .leading, spacing: WalletSpacing.sm) {
                        SectionHeader(text: group.label)
                        EntryList(entries: group.items, rowTag: "history-item", onOpenPayment: onOpenPayment)
                    }
                }
            }
        }
        .task { await model.load() }
    }
}
