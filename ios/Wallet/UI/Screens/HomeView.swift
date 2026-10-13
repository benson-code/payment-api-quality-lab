import Observation
import SwiftUI

/// Home: balance, the actions and the latest ledger entries (SPEC.md §7.2). Top up and History are
/// shown inactive: this app does not have those screens yet (README, section 4).
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

    /// Called each time the screen is shown, so a payment just made appears on return.
    func load() async {
        async let wallet = api.getWallet(walletId)
        async let ledger = api.transactions(walletId)
        switch await wallet {
        case .ok(let w, _): self.wallet = w; error = nil
        case .refused(_, let code, _): error = Messages.forCode(code)
        case .noAnswer: error = Messages.noAnswerTryAgain
        }
        if case .ok(let rows, _) = await ledger { recent = Array(rows.reversed().prefix(3)) }
    }
}

struct HomeView: View {
    let onPay: () -> Void
    let onSwitchWallet: () -> Void
    @State private var model: HomeModel

    init(api: ApiClient, walletId: String, onPay: @escaping () -> Void, onSwitchWallet: @escaping () -> Void) {
        self.onPay = onPay
        self.onSwitchWallet = onSwitchWallet
        _model = State(initialValue: HomeModel(api: api, walletId: walletId))
    }

    var body: some View {
        Screen(title: "Wallet") {
            if let error = model.error {
                Message(kind: .error, text: error, testTag: "error-message")
            }
            if let wallet = model.wallet {
                BalanceCard(wallet: wallet)
                WalletCard(spacing: WalletSpacing.sm, padding: EdgeInsets(top: WalletSpacing.sm, leading: WalletSpacing.sm,
                                                                         bottom: WalletSpacing.sm, trailing: WalletSpacing.sm)) {
                    HStack(spacing: 0) {
                        QuickAction(label: "Top up", systemName: "plus", testTag: "go-topup", action: nil)
                        QuickAction(label: "Pay", systemName: "paperplane", testTag: "go-pay", action: onPay)
                        QuickAction(label: "History", systemName: "clock.arrow.circlepath", testTag: "go-history", action: nil)
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
                            WalletCard(spacing: 0, padding: EdgeInsets(top: WalletSpacing.xs, leading: WalletSpacing.lg,
                                                                       bottom: WalletSpacing.xs, trailing: WalletSpacing.lg)) {
                                ForEach(Array(recent.enumerated()), id: \.element.entryId) { i, e in
                                    if i > 0 { RowDivider() }
                                    TransactionRow(title: Formats.typeLabel(e.type), time: Formats.time(e.createdAt),
                                                   amount: e.amount, balanceAfter: e.balanceAfter, testTag: "recent-item")
                                }
                            }
                        }
                    }
                }
                WalletButton(text: "Use another wallet", testTag: "switch-wallet", kind: .ghost, action: onSwitchWallet)
            }
        }
        .task { await model.load() }
    }
}
