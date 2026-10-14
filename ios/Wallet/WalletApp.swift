import SwiftUI

/// The screens and how they lead to each other (SPEC.md §4): Start and Home; History, Top up and Pay
/// return to Home; Payment detail returns to History, wherever it was opened from (Home, History or a
/// receipt), as on the web and Android. Plain state, not a navigation stack: no edge swipe can take a
/// receipt back to Confirm, and there are no transition animations, as on the web and Android.
enum Route: Hashable {
    case start
    case home(walletId: String)
    case history(walletId: String)
    case topUp(walletId: String)
    case pay(walletId: String)
    case payment(walletId: String, paymentId: String)
}

@main
struct WalletApp: App {
    private let api = ApiClient(config: ApiConfig.fromLaunch())
    @State private var route = Route.start

    var body: some Scene {
        WindowGroup {
            ZStack {
                WalletColors.bgPage.ignoresSafeArea()
                switch route {
                case .start:
                    StartView(api: api) { route = .home(walletId: $0) }
                case .home(let walletId):
                    HomeView(api: api, walletId: walletId,
                             onTopUp: { route = .topUp(walletId: walletId) },
                             onPay: { route = .pay(walletId: walletId) },
                             onHistory: { route = .history(walletId: walletId) },
                             onOpenPayment: { route = .payment(walletId: walletId, paymentId: $0) },
                             onSwitchWallet: { route = .start })
                case .history(let walletId):
                    HistoryView(api: api, walletId: walletId,
                                onHome: { route = .home(walletId: walletId) },
                                onPay: { route = .pay(walletId: walletId) },
                                onOpenPayment: { route = .payment(walletId: walletId, paymentId: $0) })
                case .topUp(let walletId):
                    TopUpView(api: api, walletId: walletId,
                              onBack: { route = .home(walletId: walletId) },
                              onDone: { route = .home(walletId: walletId) })
                case .pay(let walletId):
                    PayView(api: api, walletId: walletId,
                            onBack: { route = .home(walletId: walletId) },
                            onDone: { route = .home(walletId: walletId) },
                            onViewPayment: { route = .payment(walletId: walletId, paymentId: $0) })
                case .payment(let walletId, let paymentId):
                    PaymentDetailView(api: api, paymentId: paymentId,
                                      onBack: { route = .history(walletId: walletId) })
                }
            }
            .id(route)                     // each visit to a screen starts from a fresh model
        }
    }
}
