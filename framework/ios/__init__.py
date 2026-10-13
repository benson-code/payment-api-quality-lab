"""iOS App 的 Page Object：每個畫面一個類別，測試案例只呼叫這裡，不直接找元素。

元素一律用 accessibility id 找：SwiftUI 的 accessibilityIdentifier，和網頁的 data-testid、Android 的
testTag 同名（SPEC.md §7）。類別和方法的名字也和 framework/app/ 的 Android 版相同，同一個案例在
兩個平台讀起來一樣。
"""
