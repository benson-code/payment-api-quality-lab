import Observation
import SwiftUI

/// Create a wallet, or open one by its ID. There is no login: the wallet ID is the only key, as in the
/// API (a known limitation of this practice project, SPEC.md §10).
@Observable
final class StartModel {
    enum Form { case new, existing }

    private(set) var busy = false
    private(set) var error: String?
    /// The form whose request failed; its message is shown under that form's button (SPEC L-04).
    private(set) var errorForm: Form?
    private let api: ApiClient

    init(api: ApiClient) { self.api = api }

    /// The wallet ID to open, or nil (the message says why).
    func create(_ owner: String) async -> String? { await run(.new) { await api.createWallet(owner) } }
    func open(_ walletId: String) async -> String? {
        await run(.existing) { await api.getWallet(walletId.trimmingCharacters(in: .whitespaces)) }
    }

    private func run(_ form: Form, _ call: () async -> ApiResult<Wallet>) async -> String? {
        if busy { return nil }
        busy = true
        error = nil
        errorForm = nil
        defer { busy = false }
        switch await call() {
        case .ok(let wallet, _):
            return wallet.walletId
        case .refused(_, let code, _):
            error = Messages.forCode(code)
        case .noAnswer:
            error = Messages.noAnswerTryAgain
        }
        errorForm = form
        return nil
    }
}

struct StartView: View {
    let onOpened: (_ walletId: String) -> Void
    @State private var model: StartModel
    @State private var owner = ""
    @State private var walletId = ""

    init(api: ApiClient, onOpened: @escaping (String) -> Void) {
        self.onOpened = onOpened
        _model = State(initialValue: StartModel(api: api))
    }

    var body: some View {
        Screen(title: "Wallet") {
            VStack(alignment: .leading, spacing: 0) {
                Text("Open your wallet").walletText(WalletType.titleLarge).foregroundStyle(WalletColors.textPrimary)
                Text("A practice wallet: no real money, no login.").walletText(WalletType.body)
                    .foregroundStyle(WalletColors.textSecondary)
            }
            WalletCard {
                Text("New wallet").walletText(WalletType.titleMedium).foregroundStyle(WalletColors.textPrimary)
                WalletTextField(label: "Your name", value: $owner, testTag: "owner-input", placeholder: "e.g. Alex")
                WalletButton(text: "Create wallet", testTag: "create-wallet", enabled: !model.busy) {
                    Task { if let id = await model.create(owner) { onOpened(id) } }
                }
                if model.errorForm == .new, let error = model.error {
                    Message(kind: .error, text: error, testTag: "error-message")
                }
            }
            Text("or").walletText(WalletType.caption).foregroundStyle(WalletColors.textSecondary)
                .frame(maxWidth: .infinity)
            WalletCard {
                Text("Existing wallet").walletText(WalletType.titleMedium).foregroundStyle(WalletColors.textPrimary)
                WalletTextField(label: "Wallet ID", value: $walletId, testTag: "wallet-id-input", placeholder: "w_…")
                WalletButton(text: "Open wallet", testTag: "open-wallet", kind: .secondary, enabled: !model.busy) {
                    Task { if let id = await model.open(walletId) { onOpened(id) } }
                }
                if model.errorForm == .existing, let error = model.error {
                    Message(kind: .error, text: error, testTag: "error-message")
                }
            }
        }
    }
}
