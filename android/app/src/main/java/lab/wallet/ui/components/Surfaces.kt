package lab.wallet.ui.components

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ColumnScope
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Text
import androidx.compose.foundation.relocation.BringIntoViewRequester
import androidx.compose.foundation.relocation.bringIntoViewRequester
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.semantics.LiveRegionMode
import androidx.compose.ui.semantics.liveRegion
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import lab.wallet.R
import lab.wallet.ui.theme.WalletColors
import lab.wallet.ui.theme.WalletRadius
import lab.wallet.ui.theme.WalletSpacing
import lab.wallet.ui.theme.WalletType

/** A surface with a hairline border, the web's `.card`: no shadow, radius 16, padding 20. */
@Composable
fun WalletCard(
    modifier: Modifier = Modifier,
    spacing: Dp = WalletSpacing.md,
    padding: PaddingValues = PaddingValues(WalletSpacing.xl),
    content: @Composable ColumnScope.() -> Unit,
) {
    val shape = RoundedCornerShape(WalletRadius.xl)
    Column(
        verticalArrangement = Arrangement.spacedBy(spacing),
        modifier = modifier
            .fillMaxWidth()
            .background(WalletColors.bgSurface, shape)
            .border(1.dp, WalletColors.borderDefault, shape)
            .padding(padding),
        content = content,
    )
}

enum class MessageKind { Error, Warning, Success }

/**
 * Figma: Message (Kind = Error | Warning | Success). Error: refused, nothing charged. Warning: no
 * answer, outcome unknown. Success: a confirmation. Announced by screen readers when it appears.
 *
 * The hook ([testTag]) is on the text itself, so a test reads the message from the hook's element (a
 * merged container node reports no text to UiAutomator). It scrolls itself into view when it appears
 * (SPEC L-04): on a 360 x 640 dp phone the Start screen's message landed below the visible area, and
 * the user saw nothing happen.
 */
@Composable
fun Message(kind: MessageKind, text: String, testTag: String, modifier: Modifier = Modifier) {
    val requester = remember { BringIntoViewRequester() }
    LaunchedEffect(text) { requester.bringIntoView() }
    val (bg, fg, icon) = when (kind) {
        MessageKind.Error -> Triple(WalletColors.errorBg, WalletColors.errorText, R.drawable.ic_alert_circle)
        MessageKind.Warning -> Triple(WalletColors.warningBg, WalletColors.warningText, R.drawable.ic_alert_circle)
        MessageKind.Success -> Triple(WalletColors.successBg, WalletColors.successText, R.drawable.ic_check_circle)
    }
    Row(
        horizontalArrangement = Arrangement.spacedBy(WalletSpacing.md),
        verticalAlignment = Alignment.Top,
        modifier = modifier
            .fillMaxWidth()
            .bringIntoViewRequester(requester)
            .semantics {
                liveRegion = if (kind == MessageKind.Error) LiveRegionMode.Assertive else LiveRegionMode.Polite
            }
            .background(bg, RoundedCornerShape(WalletRadius.lg))
            .padding(horizontal = WalletSpacing.lg, vertical = WalletSpacing.md),
    ) {
        WalletIcon(icon, fg)
        Text(text, style = WalletType.body, color = fg, modifier = Modifier.testTag(testTag))
    }
}
