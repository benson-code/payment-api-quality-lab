package lab.wallet.ui.theme

/**
 * The design tokens of the Figma file "Wallet – UI Spec" (Foundations page), keyed by their Figma
 * names. The web declares the same values in web/src/tokens.css; DesignTokenParityTest fails when the
 * two disagree. A value is changed in Figma first, then here and in tokens.css.
 *
 * Plain Kotlin on purpose (no Compose types), so the parity test runs on the JVM without Android.
 * Theme.kt turns these into Compose colours, text styles and dimensions.
 */
object DesignTokens {

    /** Semantic colours (Figma collection "Color"), ARGB. Primitives are not exposed. */
    val colors: Map<String, Long> = linkedMapOf(
        "color/bg/page" to 0xFFF8F8F6,
        "color/bg/surface" to 0xFFFFFFFF,
        "color/bg/subtle" to 0xFFF1F1EE,
        "color/text/primary" to 0xFF16181C,
        "color/text/secondary" to 0xFF62666D,
        "color/text/on-primary" to 0xFFFFFFFF,
        "color/text/link" to 0xFF2E4366,
        "color/border/default" to 0xFFE6E6E2,
        "color/border/strong" to 0xFFC8C9C5,
        "color/border/focus" to 0xFF1B2A41,
        "color/action/primary" to 0xFF1B2A41,
        "color/action/primary-pressed" to 0xFF2E4366,
        "color/action/secondary" to 0xFFF0F3F8,
        "color/action/on-secondary" to 0xFF1B2A41,
        "color/amount/credit" to 0xFF12704C,
        "color/amount/debit" to 0xFFB42318,
        "color/feedback/error-bg" to 0xFFFDEEEC,
        "color/feedback/error-text" to 0xFFB42318,
        "color/feedback/warning-bg" to 0xFFFFF6E3,
        "color/feedback/warning-text" to 0xFF7A4E00,
        "color/feedback/success-bg" to 0xFFEAF5EF,
        "color/feedback/success-text" to 0xFF12704C,
        "color/icon/default" to 0xFF16181C,
        "color/icon/muted" to 0xFF62666D,
        "color/icon/on-primary" to 0xFFFFFFFF,
    )

    /** Spacing (Figma collection "Spacing"), in dp. */
    val spacing: Map<String, Int> = linkedMapOf(
        "spacing/xs" to 4,
        "spacing/sm" to 8,
        "spacing/md" to 12,
        "spacing/lg" to 16,
        "spacing/xl" to 20,
        "spacing/2xl" to 24,
        "spacing/3xl" to 32,
    )

    /** Corner radius (Figma collection "Radius"), in dp. */
    val radius: Map<String, Int> = linkedMapOf(
        "radius/sm" to 8,
        "radius/md" to 10,
        "radius/lg" to 12,
        "radius/xl" to 16,
        "radius/full" to 999,
    )

    /** One Figma text style. Sizes in sp, letter spacing in em (Figma's percent / 100). */
    data class TextToken(val weight: Int, val sizeSp: Int, val lineHeightSp: Int, val letterSpacingEm: Double)

    /** Text styles (Inter), under their Figma names. */
    val text: Map<String, TextToken> = linkedMapOf(
        "Display/Balance" to TextToken(700, 40, 48, -0.02),
        "Amount/Large" to TextToken(600, 28, 34, -0.01),
        "Title/Large" to TextToken(600, 22, 28, -0.005),
        "Title/Medium" to TextToken(600, 17, 24, 0.0),
        "Body/Regular" to TextToken(400, 15, 22, 0.0),
        "Body/Strong" to TextToken(500, 15, 22, 0.0),
        "Label" to TextToken(500, 13, 18, 0.0),
        "Caption" to TextToken(400, 13, 18, 0.0),
    )
}
