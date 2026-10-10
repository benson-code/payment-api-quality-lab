package lab.wallet.ui.components

import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import lab.wallet.R
import lab.wallet.ui.theme.MinTouchTarget
import lab.wallet.ui.theme.WalletColors
import lab.wallet.ui.theme.WalletSpacing
import lab.wallet.ui.theme.WalletType

/**
 * Figma: Top bar (Back = True | False). 56 dp, title centred. With [onBack] it shows a back button
 * (hook "back"), a 48 dp touch target; [backEnabled] = false while a request is in flight (K-02).
 */
@Composable
fun TopBar(title: String, onBack: (() -> Unit)? = null, backEnabled: Boolean = true) {
    Row(
        modifier = Modifier.fillMaxWidth().height(56.dp).padding(horizontal = WalletSpacing.xs),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Box(Modifier.size(MinTouchTarget), contentAlignment = Alignment.Center) {
            if (onBack != null) {
                IconButton(
                    icon = R.drawable.ic_arrow_left,
                    label = "Back",
                    testTag = "back",
                    enabled = backEnabled,
                    onClick = onBack,
                )
            }
        }
        Text(
            text = title,
            style = WalletType.titleMedium,
            color = WalletColors.textPrimary,
            textAlign = TextAlign.Center,
            modifier = Modifier.weight(1f).semantics { heading() },
        )
        Box(Modifier.size(MinTouchTarget))
    }
}
