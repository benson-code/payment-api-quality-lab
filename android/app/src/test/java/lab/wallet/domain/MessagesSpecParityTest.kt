package lab.wallet.domain

import java.io.File
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * The error texts are part of the specification (SPEC.md §6.6) and must read the same on both clients.
 * This test reads the table in SPEC.md and requires Messages to match it, row by row.
 */
class MessagesSpecParityTest {
    private val spec: String by lazy {
        File(System.getProperty("specMd") ?: error("system property specMd is not set (see app/build.gradle.kts)")).readText()
    }

    @Test
    fun everyErrorTextMatchesTheSpecification() {
        val rows = Regex("""^\| E-0\d \| `([A-Z_]+)` \| ([^|]+) \|""", RegexOption.MULTILINE).findAll(spec)
            .associate { it.groupValues[1] to it.groupValues[2].trim() }
        assertTrue("no error rows found in SPEC.md", rows.size >= 8)
        assertEquals(rows.toSortedMap(), Messages.codes.associateWith { Messages.forCode(it) }.toSortedMap())
    }

    @Test
    fun unknownCodesFollowTheSpecification() {
        val row = Regex("""^\| E-09 \| any other code \| ([^|]+) \|""", RegexOption.MULTILINE).find(spec)
            ?: error("E-09 not found in SPEC.md")
        // SPEC writes the placeholder as `<code>`
        val expected = row.groupValues[1].trim().replace("`<code>`", "SOMETHING_NEW")
        assertEquals(expected, Messages.forCode("SOMETHING_NEW"))
    }
}
