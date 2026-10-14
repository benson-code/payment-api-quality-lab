import Observation
import SwiftUI

/// Home tab: balance, the three actions and the latest ledger entries (SPEC.md §7.2). Same behaviour
/// as web/src/screens/Wallet.jsx and the Android HomeScreen.kt.
@Observable
final class HomeModel {
    private(set) var wallet: Wallet?
    private(set) var recent: [Entry]?
    private(set) var error: String?
    private let api: ApiClient
    private let walletId: String

    init(api: ApiClient, walletId: String) {
        self.api = api
        self.walletId = walletId
    }

    /// Called each time the screen is shown, so a top-up or payment just made appears on return.
    func load() async {
        async let wallet = api.getWallet(walletId)
        async let ledger = api.transactions(walletId)
        switch await wallet {
        case .ok(let w, _): self.wallet = w; error = nil
        case .refused(_, let code, _): error = Messages.forCode(code)
        case .noAnswer: error = Messages.noAnswer
        }
        if case .ok(let rows, _) = await ledger { recent = Array(rows.reversed().prefix(3)) }
    }
}

struct HomeView: View {
    let onTopUp: () -> Void
    let onPay: () -> Void
    let onHistory: () -> Void
    let onOpenPayment: (_ paymentId: String) -> Void
    let onSwitchWallet: () -> Void
    @State private var model: HomeModel

    init(api: ApiClient, walletId: String, onTopUp: @escaping () -> Void, onPay: @escaping () -> Void,
         onHistory: @escaping () -> Void, onOpenPayment: @escaping (String) -> Void, onSwitchWallet: @escaping () -> Void) {
        self.onTopUp = onTopUp
        self.onPay = onPay
        self.onHistory = onHistory
        self.onOpenPayment = onOpenPayment
        self.onSwitchWallet = onSwitchWallet
        _model = State(initialValue: HomeModel(api: api, walletId: walletId))
    }

    var body: some View {
        Screen(title: "Wallet", tabBar: TabBar(active: .home) { tab in
            switch tab {
            case .home: nil
            case .pay: onPay
            case .history: onHistory
            }
        }) {
            if let error = model.error {
                Message(kind: .error, text: error, testTag: "error-message")
            }
            if let wallet = model.wallet {
                BalanceCard(wallet: wallet)
                WalletCard(spacing: WalletSpacing.sm, padding: EdgeInsets(top: WalletSpacing.sm, leading: WalletSpacing.sm,
                                                                         bottom: WalletSpacing.sm, trailing: WalletSpacing.sm)) {
                    HStack(spacing: 0) {
                        QuickAction(label: "Top up", systemName: "plus", testTag: "go-topup", action: onTopUp)
                        QuickAction(label: "Pay", systemName: "paperplane", testTag: "go-pay", action: onPay)
                        QuickAction(label: "History", systemName: "clock.arrow.circlepath", testTag: "go-history", action: onHistory)
                    }
                }
                if let recent = model.recent {
                    VStack(alignment: .leading, spacing: WalletSpacing.sm) {
                        SectionHeader(text: "Recent activity")
                        if recent.isEmpty {
                            WalletCard {
                                Text("No transactions yet.").walletText(WalletType.body).foregroundStyle(WalletColors.textSecondary)
                                    .frame(maxWidth: .infinity)
                                    .accessibilityIdentifier("recent-empty")
                            }
                        } else {
                            EntryList(entries: recent, rowTag: "recent-item", onOpenPayment: onOpenPayment)
                        }
                    }
                }
                WalletButton(text: "Use another wallet", testTag: "switch-wallet", kind: .ghost, action: onSwitchWallet)
            }
        }
        .task { await model.load() }
    }
}
