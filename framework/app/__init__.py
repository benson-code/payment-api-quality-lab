"""Android App 的 Page Object：每個畫面一個類別，測試案例只呼叫這裡，不直接找元素。

元素一律用 Compose 的 testTag 找（以 resource-id 呈現，清單在 SPEC.md §7），和網頁的
data-testid 同名：同一個案例在兩個平台用同一組名字。
"""
