import SwiftUI

/// Text field (code only; same specs as the Figma Amount field, 52 pt high). The label is always
/// visible above the box, and it is also the field's accessible name: a placeholder alone is not a
/// label (SPEC L-03). VoiceOver reads the field once, by that name. Focus: 2 pt border.
struct WalletTextField: View {
    let label: String
    @Binding var value: String
    let testTag: String
    var placeholder = ""

    @FocusState private var focused: Bool

    var body: some View {
        let shape = RoundedRectangle(cornerRadius: WalletRadius.lg)
        VStack(alignment: .leading, spacing: WalletSpacing.sm) {
            Text(label).walletText(WalletType.label).foregroundStyle(WalletColors.textSecondary)
                .accessibilityHidden(true)
            TextField("", text: $value, prompt: Text(placeholder).foregroundStyle(WalletColors.textSecondary))
                .walletText(WalletType.body)
                .foregroundStyle(WalletColors.textPrimary)
                .tint(WalletColors.borderFocus)
                .textInputAutocapitalization(.never)
                .autocorrectionDisabled()
                .focused($focused)
                .padding(.horizontal, WalletSpacing.lg)
                .frame(minHeight: 52)
                .background(WalletColors.bgSurface, in: shape)
                .overlay(shape.strokeBorder(focused ? WalletColors.borderFocus : WalletColors.borderDefault,
                                            lineWidth: focused ? 2 : 1))
                .accessibilityLabel(label)
                .accessibilityIdentifier(testTag)
        }
    }
}

/// Figma: Amount field (State = Empty | Filled | Focus | Error). Hook "amount-input".
///
/// The decimal keyboard; the value stays the String the user typed and is sent as typed (SPEC R-01).
struct AmountField: View {
    @Binding var value: String
    var label = "Amount"

    @FocusState private var focused: Bool

    var body: some View {
        let shape = RoundedRectangle(cornerRadius: WalletRadius.lg)
        VStack(alignment: .leading, spacing: WalletSpacing.sm) {
            Text(label).walletText(WalletType.label).foregroundStyle(WalletColors.textSecondary)
                .accessibilityHidden(true)
            HStack(spacing: WalletSpacing.sm) {
                TextField("", text: $value, prompt: Text("0.00").foregroundStyle(WalletColors.textSecondary))
                    .walletText(WalletType.amountLarge)
                    .foregroundStyle(WalletColors.textPrimary)
                    .tint(WalletColors.borderFocus)
                    .keyboardType(.decimalPad)
                    .focused($focused)
                    .accessibilityLabel(label)
                    .accessibilityIdentifier("amount-input")
                Text("TWD").walletText(WalletType.bodyStrong).foregroundStyle(WalletColors.textSecondary)
            }
            .padding(.horizontal, WalletSpacing.lg)
            .padding(.vertical, WalletSpacing.md)
            .frame(minHeight: 72)
            .background(WalletColors.bgSurface, in: shape)
            .overlay(shape.strokeBorder(focused ? WalletColors.borderFocus : WalletColors.borderDefault,
                                        lineWidth: focused ? 2 : 1))
        }
    }
}
