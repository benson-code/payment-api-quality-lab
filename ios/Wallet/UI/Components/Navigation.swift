import SwiftUI

enum Tab: CaseIterable {
    case home, pay, history

    var label: String {
        switch self {
        case .home: "Home"
        case .pay: "Pay"
        case .history: "History"
        }
    }

    var systemName: String {
        switch self {
        case .home: "house"
        case .pay: "paperplane"
        case .history: "clock.arrow.circlepath"
        }
    }

    var testTag: String { "tab-\(label.lowercased())" }
}

/// Figma: Tab bar (Active = Home | Pay | History). 64 pt with its hairline, on a surface that runs on
/// under the home indicator, as the web's and Android's. The active tab is marked selected for
/// VoiceOver and does nothing when tapped; a tab with no action in `onSelect` is shown but inactive.
struct TabBar: View {
    let active: Tab
    let onSelect: (Tab) -> (() -> Void)?

    var body: some View {
        VStack(spacing: 0) {
            Rectangle().fill(WalletColors.borderDefault).frame(height: 1)
            HStack(spacing: 0) {
                ForEach(Tab.allCases, id: \.self) { tab in
                    let on = tab == active
                    let action = onSelect(tab)
                    Button { action?() } label: {
                        VStack(spacing: 2) {
                            Image(systemName: tab.systemName)
                                .font(.system(size: 22))
                                .foregroundStyle(on ? WalletColors.actionPrimary : WalletColors.iconMuted)
                                .frame(width: 24, height: 24)
                                .accessibilityHidden(true)          // the tab is named by its label
                            Text(tab.label)
                                .walletText(on ? WalletType.label : WalletType.caption)
                                .foregroundStyle(on ? WalletColors.textPrimary : WalletColors.textSecondary)
                        }
                        .frame(maxWidth: .infinity, maxHeight: .infinity)
                        .contentShape(Rectangle())
                    }
                    .buttonStyle(.plain)
                    .disabled(action == nil && !on)
                    .opacity(action == nil && !on ? 0.4 : 1)
                    .accessibilityAddTraits(on ? .isSelected : [])
                    .accessibilityIdentifier(tab.testTag)
                }
            }
            .frame(height: 63)
        }
        .background(WalletColors.bgSurface.ignoresSafeArea(edges: .bottom))
    }
}
