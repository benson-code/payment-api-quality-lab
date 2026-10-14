import SwiftUI

enum WalletButtonKind { case primary, secondary, ghost }

/// Figma: Button (Style = Primary | Secondary | Ghost, State = Default | Disabled | Loading).
/// Full width, 52 pt. Loading reads "Processing…" and does not react to taps (K-02).
/// The hook is on the button; its text is the button's label.
struct WalletButton: View {
    let text: String
    let testTag: String
    var kind: WalletButtonKind = .primary
    var enabled = true
    var loading = false
    let action: () -> Void

    var body: some View {
        let active = enabled && !loading
        Button(action: action) {
            Text(loading ? "Processing…" : text)
                .walletText(WalletType.bodyStrong)
                .frame(maxWidth: .infinity, minHeight: 52)
        }
        .buttonStyle(FilledButtonStyle(kind: kind))
        .disabled(!active)
        .opacity(active ? 1 : 0.4)          // loading looks disabled too, as on the web and Android
        .accessibilityIdentifier(testTag)
    }
}

private struct FilledButtonStyle: ButtonStyle {
    let kind: WalletButtonKind

    func makeBody(configuration: Configuration) -> some View {
        let shape = RoundedRectangle(cornerRadius: WalletRadius.md)
        let (background, content): (Color, Color) = switch kind {
        case .primary: (configuration.isPressed ? WalletColors.actionPrimaryPressed : WalletColors.actionPrimary, WalletColors.textOnPrimary)
        case .secondary: (WalletColors.actionSecondary, WalletColors.actionOnSecondary)
        case .ghost: (.clear, WalletColors.textLink)
        }
        return configuration.label
            .padding(.horizontal, WalletSpacing.xl)
            .foregroundStyle(content)
            .background(background, in: shape)
            .contentShape(shape)
    }
}

/// An icon-only button: a 44 pt touch target with an accessible `label` (SPEC L-02, L-03).
struct IconButton: View {
    let systemName: String
    let label: String
    let testTag: String
    var enabled = true
    var tint = WalletColors.iconDefault
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            Image(systemName: systemName)
                .font(.system(size: 20))
                .foregroundStyle(tint)
                .frame(width: minTouchTarget, height: minTouchTarget)
                .contentShape(Circle())
        }
        .buttonStyle(.plain)
        .disabled(!enabled)
        .opacity(enabled ? 1 : 0.4)
        .accessibilityLabel(label)
        .accessibilityIdentifier(testTag)
    }
}

/// Figma: Quick action. Line icon in the primary colour over a label; the whole cell is the touch
/// target. Without an action it is shown but inactive.
struct QuickAction: View {
    let label: String
    let systemName: String
    let testTag: String
    let action: (() -> Void)?

    var body: some View {
        Button { action?() } label: {
            VStack(spacing: WalletSpacing.sm) {
                Image(systemName: systemName).font(.system(size: 22)).foregroundStyle(WalletColors.actionPrimary)
                Text(label).walletText(WalletType.label).foregroundStyle(WalletColors.textPrimary)
            }
            .frame(maxWidth: .infinity, minHeight: 76)
            .contentShape(Rectangle())
        }
        .buttonStyle(.plain)
        .disabled(action == nil)
        .opacity(action == nil ? 0.4 : 1)
        .accessibilityIdentifier(testTag)
    }
}
