package lab.wallet.ui.components

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.RowScope
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.rememberTextMeasurer
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import lab.wallet.R
import lab.wallet.domain.Money
import lab.wallet.ui.theme.WalletColors
import lab.wallet.ui.theme.WalletRadius
import lab.wallet.ui.theme.WalletSpacing
import lab.wallet.ui.theme.WalletType

/** Figma: Section header. Groups rows by date ("Today", "9 Oct"). */
@Composable
fun SectionHeader(text: String) {
    Text(text, style = WalletType.label, color = WalletColors.textSecondary,
        modifier = Modifier.padding(top = WalletSpacing.xs).semantics { heading() })
}

/** A hairline between rows of a list card, as the web's `.tx-row + .tx-row`. */
@Composable
fun RowDivider() = HorizontalDivider(thickness = 1.dp, color = WalletColors.borderDefault)

/**
 * Figma: Transaction row (Direction = Credit | Debit; Show chevron). Credit amounts in green with "+",
 * debit amounts in the text colour with "−" (SPEC D-02).
 *
 * The title, amount and balance keep their own hooks ("item-title", "item-amount", "item-balance").
 * With [onOpen] (payments) the whole row is one button, hook "open-payment", with a chevron; its
 * children stay readable to UiAutomator, as a button's label does.
 */
@Composable
fun TransactionRow(
    title: String,
    time: String,
    amount: String,
    balanceAfter: String?,
    testTag: String,
    onOpen: (() -> Unit)? = null,
) {
    // Two levels, as on the web: the row carries [testTag]; a row that opens a detail holds a button
    // (hook "open-payment") with the content inside, so both hooks exist on separate nodes.
    Box(Modifier.fillMaxWidth().testTag(testTag)) {
        val inner = Modifier.fillMaxWidth()
        Row(
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(WalletSpacing.md),
            modifier = (if (onOpen == null) inner else inner
                .clip(RoundedCornerShape(WalletRadius.sm))
                .clickable(role = Role.Button, onClickLabel = "Open payment", onClick = onOpen)
                .testTag("open-payment"))
                .padding(vertical = WalletSpacing.md),
        ) {
            TransactionContent(title, time, amount, balanceAfter)
            if (onOpen != null) WalletIcon(R.drawable.ic_chevron_right, WalletColors.iconMuted)
        }
    }
}

@Composable
private fun RowScope.TransactionContent(title: String, time: String, amount: String, balanceAfter: String?) {
    val credit = !amount.startsWith("-")
    Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(2.dp)) {
        Text(title, style = WalletType.bodyStrong, color = WalletColors.textPrimary, modifier = Modifier.testTag("item-title"))
        Text(time, style = WalletType.caption, color = WalletColors.textSecondary)
    }
    Column(horizontalAlignment = Alignment.End, verticalArrangement = Arrangement.spacedBy(2.dp)) {
        Text(Money.signed(amount), style = WalletType.bodyStrong.copy(fontFeatureSettings = "tnum"),
            color = if (credit) WalletColors.amountCredit else WalletColors.textPrimary,
            textAlign = TextAlign.End, modifier = Modifier.testTag("item-amount"))
        if (balanceAfter != null) {
            Row {
                Text("Balance ", style = WalletType.caption, color = WalletColors.textSecondary)
                Text(Money.display(balanceAfter), style = WalletType.caption.copy(fontFeatureSettings = "tnum"),
                    color = WalletColors.textSecondary, modifier = Modifier.testTag("item-balance"))
            }
        }
    }
}

/**
 * Figma: Receipt row. Label left, value right. A hook on an amount wraps the number only, never the
 * currency (SPEC §7): pass the number as [value] and the currency as [suffix].
 */
@Composable
fun ReceiptRow(label: String, value: String, valueTestTag: String? = null, suffix: String? = null) {
    // The web's flex layout: the value keeps its width when it can, the label takes the rest and wraps
    // between words, but never narrower than its longest word. Compose has no such floor: with the label
    // simply weighted, a 50-character name crushed "From" to one letter per line, over the name (QA pass).
    val measurer = rememberTextMeasurer()
    val labelFloor = with(LocalDensity.current) {
        label.split(" ").maxOf { measurer.measure(it, WalletType.body).size.width }.toDp()
    }
    BoxWithConstraints(Modifier.fillMaxWidth().padding(vertical = WalletSpacing.md)) {
        val valueMax = maxWidth - labelFloor - WalletSpacing.lg
        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(WalletSpacing.lg)) {
            Text(label, style = WalletType.body, color = WalletColors.textSecondary, modifier = Modifier.weight(1f))
            Row(Modifier.widthIn(max = valueMax)) {
                Text(value, style = WalletType.bodyStrong.copy(fontFeatureSettings = "tnum"), color = WalletColors.textPrimary,
                    textAlign = TextAlign.End, modifier = if (valueTestTag != null) Modifier.testTag(valueTestTag) else Modifier)
                if (suffix != null) Text(" $suffix", style = WalletType.bodyStrong, color = WalletColors.textPrimary, softWrap = false)
            }
        }
    }
}
