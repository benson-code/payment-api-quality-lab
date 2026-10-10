package lab.wallet.ui.theme

import java.io.File
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * The web and the app take their design tokens from the same Figma file (SPEC.md §3). This test reads
 * the web's web/src/tokens.css and requires the app's DesignTokens to hold exactly the same values,
 * so a change made on one client only fails the build.
 *
 * Figma names map to CSS names by rule: color/bg/page -> --color-bg-page. Text styles have short CSS
 * class names, listed in TEXT_CLASSES.
 */
class DesignTokenParityTest {

    private val css: String by lazy {
        val path = System.getProperty("tokensCss") ?: error("system property tokensCss is not set (see app/build.gradle.kts)")
        File(path).readText()
    }

    private fun cssName(figmaName: String) = figmaName.replace('/', '-')

    private fun hex(argb: Long) = "#%06X".format(argb and 0xFFFFFF)

    @Test
    fun coloursMatchTheWeb() {
        val web = Regex("""--(color-[a-z0-9-]+):\s*#([0-9a-fA-F]{6});""").findAll(css)
            .associate { it.groupValues[1] to "#" + it.groupValues[2].uppercase() }
        val app = DesignTokens.colors.entries.associate { cssName(it.key) to hex(it.value) }
        assertTrue("no colours found in tokens.css", web.isNotEmpty())
        assertEquals(web.toSortedMap(), app.toSortedMap())
    }

    @Test
    fun coloursAreOpaque() {
        // tokens.css has no alpha; an app colour with alpha would look different and slip past the hex check
        DesignTokens.colors.forEach { (name, argb) -> assertEquals("$name alpha", 0xFFL, argb ushr 24) }
    }

    @Test
    fun spacingAndRadiusMatchTheWeb() {
        for ((prefix, tokens) in listOf("spacing" to DesignTokens.spacing, "radius" to DesignTokens.radius)) {
            val web = Regex("""--($prefix-[a-z0-9]+):\s*(\d+)px;""").findAll(css)
                .associate { it.groupValues[1] to it.groupValues[2].toInt() }
            val app = tokens.mapKeys { cssName(it.key) }
            assertTrue("no $prefix tokens found in tokens.css", web.isNotEmpty())
            assertEquals(prefix, web.toSortedMap(), app.toSortedMap())
        }
    }

    @Test
    fun textStylesMatchTheWeb() {
        val web = Regex("""\.(t-[a-z-]+) \{ font: (\d+) (\d+)px/(\d+)px [^;]*;(?: letter-spacing: (-?[0-9.]+)em;)?""")
            .findAll(css)
            .associate { m ->
                val (cls, weight, size, lineHeight, spacing) = m.destructured
                cls to DesignTokens.TextToken(weight.toInt(), size.toInt(), lineHeight.toInt(), spacing.ifEmpty { "0" }.toDouble())
            }
        val app = DesignTokens.text.entries.associate { (figmaName, token) ->
            val cls = TEXT_CLASSES[figmaName] ?: error("no CSS class listed for text style $figmaName")
            cls to token
        }
        assertTrue("no text styles found in tokens.css", web.isNotEmpty())
        assertEquals(web.toSortedMap(), app.toSortedMap())
    }

    private companion object {
        val TEXT_CLASSES = mapOf(
            "Display/Balance" to "t-display",
            "Amount/Large" to "t-amount",
            "Title/Large" to "t-title-lg",
            "Title/Medium" to "t-title-md",
            "Body/Regular" to "t-body",
            "Body/Strong" to "t-body-strong",
            "Label" to "t-label",
            "Caption" to "t-caption",
        )
    }
}
