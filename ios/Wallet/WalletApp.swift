import SwiftUI

/// The screens of this first stage and how they lead to each other (SPEC.md §4): Start → Home → Pay
/// (amount, Confirm, receipt) → Home. Plain state, not a navigation stack: no edge swipe can take a
/// receipt back to Confirm, and there are no transition animations, as on the web and Android.
enum Route: Hashable {
    case start
    case home(walletId: String)
    case pay(walletId: String)
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
                             onPay: { route = .pay(walletId: walletId) },
                             onSwitchWallet: { route = .start })
                case .pay(let walletId):
                    PayView(api: api, walletId: walletId,
                            onBack: { route = .home(walletId: walletId) },
                            onDone: { route = .home(walletId: walletId) })
                }
            }
            .id(route)                     // each visit to a screen starts from a fresh model
        }
    }
}
