package lab.wallet.ui.components

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.interaction.MutableInteractionSource
import androidx.compose.foundation.interaction.collectIsFocusedAsState
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
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
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.unit.dp
import lab.wallet.ui.theme.WalletColors
import lab.wallet.ui.theme.WalletRadius
import lab.wallet.ui.theme.WalletSpacing
import lab.wallet.ui.theme.WalletType

/**
 * Text field (code only; same specs as the Figma Amount field, 52 dp high). The label is always
 * visible above the box: a placeholder alone is not a label (SPEC L-03). Focus: 2 dp border.
 */
@Composable
fun WalletTextField(
    label: String,
    value: String,
    onValueChange: (String) -> Unit,
    testTag: String,
    modifier: Modifier = Modifier,
    placeholder: String = "",
) {
    val interaction = remember { MutableInteractionSource() }
    val focused by interaction.collectIsFocusedAsState()
    val shape = RoundedCornerShape(WalletRadius.lg)
    Column(modifier = modifier.fillMaxWidth(), verticalArrangement = Arrangement.spacedBy(WalletSpacing.sm)) {
        Text(label, style = WalletType.label, color = WalletColors.textSecondary)
        BasicTextField(
            value = value,
            onValueChange = onValueChange,
            singleLine = true,
            textStyle = WalletType.body.copy(color = WalletColors.textPrimary),
            cursorBrush = SolidColor(WalletColors.borderFocus),
            interactionSource = interaction,
            keyboardOptions = KeyboardOptions(imeAction = ImeAction.Done),
            modifier = Modifier.fillMaxWidth().testTag(testTag),
            decorationBox = { inner ->
                Box(
                    contentAlignment = Alignment.CenterStart,
                    modifier = Modifier
                        .fillMaxWidth()
                        .heightIn(min = 52.dp)
                        .background(WalletColors.bgSurface, shape)
                        .border(if (focused) 2.dp else 1.dp, if (focused) WalletColors.borderFocus else WalletColors.borderDefault, shape)
                        .padding(horizontal = WalletSpacing.lg),
                ) {
                    if (value.isEmpty() && placeholder.isNotEmpty()) {
                        Text(placeholder, style = WalletType.body, color = WalletColors.textSecondary)
                    }
                    inner()
                }
            },
        )
    }
}
