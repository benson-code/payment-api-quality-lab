package lab.wallet.ui.components

import androidx.annotation.DrawableRes
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.interaction.MutableInteractionSource
import androidx.compose.foundation.interaction.collectIsPressedAsState
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Text
import androidx.compose.material3.ripple
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.unit.dp
import lab.wallet.ui.theme.MinTouchTarget
import lab.wallet.ui.theme.WalletColors
import lab.wallet.ui.theme.WalletRadius
import lab.wallet.ui.theme.WalletSpacing
import lab.wallet.ui.theme.WalletType

enum class ButtonStyle { Primary, Secondary, Ghost }

/**
 * Figma: Button (Style = Primary | Secondary | Ghost, State = Default | Disabled | Loading).
 * Full width, 52 dp. Loading shows "Processing…" and does not react to taps (K-02).
 */
@Composable
fun WalletButton(
    text: String,
    onClick: () -> Unit,
    testTag: String,
    modifier: Modifier = Modifier,
    style: ButtonStyle = ButtonStyle.Primary,
    enabled: Boolean = true,
    loading: Boolean = false,
) {
    val interaction = remember { MutableInteractionSource() }
    val pressed by interaction.collectIsPressedAsState()
    val active = enabled && !loading
    val background = when (style) {
        ButtonStyle.Primary -> if (pressed) WalletColors.actionPrimaryPressed else WalletColors.actionPrimary
        ButtonStyle.Secondary -> WalletColors.actionSecondary
        ButtonStyle.Ghost -> Color.Transparent
    }
    val content = when (style) {
        ButtonStyle.Primary -> WalletColors.textOnPrimary
        ButtonStyle.Secondary -> WalletColors.actionOnSecondary
        ButtonStyle.Ghost -> WalletColors.textLink
    }
    val shape = RoundedCornerShape(WalletRadius.md)
    Box(
        contentAlignment = Alignment.Center,
        modifier = modifier
            .fillMaxWidth()
            .heightIn(min = 52.dp)
            .testTag(testTag)
            .alpha(if (enabled) 1f else 0.4f)
            .clip(shape)
            .background(background, shape)
            .clickable(
                enabled = active,
                role = Role.Button,
                interactionSource = interaction,
                indication = ripple(),
                onClick = onClick,
            )
            .padding(horizontal = WalletSpacing.xl, vertical = WalletSpacing.md),
    ) {
        Text(text = if (loading) "Processing…" else text, style = WalletType.bodyStrong, color = content)
    }
}

/** An icon-only button: a 48 dp touch target with an accessible [label] (SPEC L-02, L-03). */
@Composable
fun IconButton(
    @DrawableRes icon: Int,
    label: String,
    testTag: String,
    onClick: () -> Unit,
    enabled: Boolean = true,
    tint: Color = WalletColors.iconDefault,
) {
    Box(
        contentAlignment = Alignment.Center,
        modifier = Modifier
            .size(MinTouchTarget)
            .testTag(testTag)
            .alpha(if (enabled) 1f else 0.4f)
            .clip(CircleShape)
            .clickable(enabled = enabled, role = Role.Button, onClick = onClick)
            .semantics { contentDescription = label },
    ) {
        WalletIcon(icon, tint)
    }
}
