package lab.wallet.ui.theme

import androidx.compose.foundation.text.selection.LocalTextSelectionColors
import androidx.compose.foundation.text.selection.TextSelectionColors
import androidx.compose.runtime.Composable
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.Font
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.LineHeightStyle
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.em
import androidx.compose.ui.unit.sp
import lab.wallet.R

/** Inter, bundled with the app: the device may have no Google Play services to download fonts. */
val Inter = FontFamily(
    Font(R.font.inter_regular, FontWeight.Normal),
    Font(R.font.inter_medium, FontWeight.Medium),
    Font(R.font.inter_semibold, FontWeight.SemiBold),
    Font(R.font.inter_bold, FontWeight.Bold),
)

private fun color(name: String) = Color(DesignTokens.colors.getValue(name))

/** The semantic colours, named after their Figma variables: color/bg/page -> bgPage. */
object WalletColors {
    val bgPage = color("color/bg/page")
    val bgSurface = color("color/bg/surface")
    val bgSubtle = color("color/bg/subtle")
    val textPrimary = color("color/text/primary")
    val textSecondary = color("color/text/secondary")
    val textOnPrimary = color("color/text/on-primary")
    val textLink = color("color/text/link")
    val borderDefault = color("color/border/default")
    val borderStrong = color("color/border/strong")
    val borderFocus = color("color/border/focus")
    val actionPrimary = color("color/action/primary")
    val actionPrimaryPressed = color("color/action/primary-pressed")
    val actionSecondary = color("color/action/secondary")
    val actionOnSecondary = color("color/action/on-secondary")
    val amountCredit = color("color/amount/credit")
    val amountDebit = color("color/amount/debit")
    val errorBg = color("color/feedback/error-bg")
    val errorText = color("color/feedback/error-text")
    val warningBg = color("color/feedback/warning-bg")
    val warningText = color("color/feedback/warning-text")
    val successBg = color("color/feedback/success-bg")
    val successText = color("color/feedback/success-text")
    val iconDefault = color("color/icon/default")
    val iconMuted = color("color/icon/muted")
    val iconOnPrimary = color("color/icon/on-primary")
}

private fun style(name: String): TextStyle {
    val t = DesignTokens.text.getValue(name)
    return TextStyle(
        fontFamily = Inter,
        fontWeight = FontWeight(t.weight),
        fontSize = t.sizeSp.sp,
        lineHeight = t.lineHeightSp.sp,
        letterSpacing = t.letterSpacingEm.em,
        // Centre the glyphs in the line height and keep it exact, as Figma and the web do
        lineHeightStyle = LineHeightStyle(LineHeightStyle.Alignment.Center, LineHeightStyle.Trim.None),
    )
}

/** The eight Figma text styles. Amount styles use tabular figures, so digits line up in lists. */
object WalletType {
    val displayBalance = style("Display/Balance").copy(fontFeatureSettings = "tnum")
    val amountLarge = style("Amount/Large").copy(fontFeatureSettings = "tnum")
    val titleLarge = style("Title/Large")
    val titleMedium = style("Title/Medium")
    val body = style("Body/Regular")
    val bodyStrong = style("Body/Strong")
    val label = style("Label")
    val caption = style("Caption")
}

private fun dp(map: Map<String, Int>, name: String): Dp = map.getValue(name).dp

object WalletSpacing {
    val xs = dp(DesignTokens.spacing, "spacing/xs")
    val sm = dp(DesignTokens.spacing, "spacing/sm")
    val md = dp(DesignTokens.spacing, "spacing/md")
    val lg = dp(DesignTokens.spacing, "spacing/lg")
    val xl = dp(DesignTokens.spacing, "spacing/xl")
    val xxl = dp(DesignTokens.spacing, "spacing/2xl")
    val xxxl = dp(DesignTokens.spacing, "spacing/3xl")
}

object WalletRadius {
    val sm = dp(DesignTokens.radius, "radius/sm")
    val md = dp(DesignTokens.radius, "radius/md")
    val lg = dp(DesignTokens.radius, "radius/lg")
    val xl = dp(DesignTokens.radius, "radius/xl")
}

/** Minimum touch target on Android (SPEC L-02). */
val MinTouchTarget = 48.dp

@Composable
fun WalletTheme(content: @Composable () -> Unit) {
    val selection = TextSelectionColors(handleColor = WalletColors.borderFocus, backgroundColor = WalletColors.actionSecondary)
    CompositionLocalProvider(LocalTextSelectionColors provides selection, content = content)
}
