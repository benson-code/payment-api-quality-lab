package lab.wallet.ui.components

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.interaction.MutableInteractionSource
import androidx.compose.foundation.interaction.collectIsFocusedAsState
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.BasicTextField
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.SolidColor
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.semantics.error
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import lab.wallet.ui.theme.WalletColors
import lab.wallet.ui.theme.WalletRadius
import lab.wallet.ui.theme.WalletSpacing
import lab.wallet.ui.theme.WalletType

/**
 * Figma: Amount field (State = Empty | Filled | Focus | Error). Hook "amount-input".
 *
 * A text field with the decimal keyboard; the value stays the String the user typed and is sent as
 * typed (SPEC R-01). [error] is the API's answer, shown under the field (hook "error-message").
 */
@Composable
fun AmountField(
    value: String,
    onValueChange: (String) -> Unit,
    modifier: Modifier = Modifier,
    label: String = "Amount",
    enabled: Boolean = true,
    error: String? = null,
) {
    val interaction = remember { MutableInteractionSource() }
    val focused by interaction.collectIsFocusedAsState()
    val shape = RoundedCornerShape(WalletRadius.lg)
    val border = when {
        error != null -> 2.dp to WalletColors.errorText
        focused -> 2.dp to WalletColors.borderFocus
        else -> 1.dp to WalletColors.borderDefault
    }
    Column(modifier = modifier.fillMaxWidth(), verticalArrangement = Arrangement.spacedBy(WalletSpacing.sm)) {
        Text(label, style = WalletType.label, color = WalletColors.textSecondary)
        BasicTextField(
            value = value,
            onValueChange = onValueChange,
            enabled = enabled,
            singleLine = true,
            textStyle = WalletType.amountLarge.copy(color = if (enabled) WalletColors.textPrimary else WalletColors.textSecondary),
            cursorBrush = SolidColor(WalletColors.borderFocus),
            interactionSource = interaction,
            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Decimal, imeAction = ImeAction.Done),
            modifier = Modifier
                .fillMaxWidth()
                .testTag("amount-input")
                .semantics { if (error != null) error(error) },
            decorationBox = { inner ->
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(WalletSpacing.sm),
                    modifier = Modifier
                        .fillMaxWidth()
                        .heightIn(min = 72.dp)
                        .background(WalletColors.bgSurface, shape)
                        .border(border.first, border.second, shape)
                        .padding(horizontal = WalletSpacing.lg, vertical = WalletSpacing.md),
                ) {
                    Box(Modifier.weight(1f)) {
                        if (value.isEmpty()) Text("0.00", style = WalletType.amountLarge, color = WalletColors.textSecondary)
                        inner()
                    }
                    Text("TWD", style = WalletType.bodyStrong, color = WalletColors.textSecondary)
                }
            },
        )
        if (error != null) {
            Text(error, style = WalletType.caption, color = WalletColors.errorText, modifier = Modifier.testTag("error-message"))
        }
    }
}
