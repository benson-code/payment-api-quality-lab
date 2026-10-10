package lab.wallet.domain

import java.time.Clock
import java.time.Instant
import java.time.ZoneId
import org.junit.Assert.assertEquals
import org.junit.Test

class FormatsTest {
    // "Now" is 10 Oct 2026, 12:00 in Taipei (UTC+8)
    private val taipei = Formats(Clock.fixed(Instant.parse("2026-10-10T04:00:00Z"), ZoneId.of("Asia/Taipei")))

    @Test
    fun timesAreShownInTheDeviceTimeZone() {
        assertEquals("14:31", taipei.time("2026-10-10T06:31:12.345+00:00"))
        assertEquals("10 Oct 2026, 14:31", taipei.dateTime("2026-10-10T06:31:12.345+00:00"))
        val utc = Formats(Clock.fixed(Instant.parse("2026-10-10T04:00:00Z"), ZoneId.of("UTC")))
        assertEquals("06:31", utc.time("2026-10-10T06:31:12.345+00:00"))
    }

    @Test
    fun dayLabelsUseTheLocalDate() {
        // 16:30 UTC on 9 Oct is 00:30 on 10 Oct in Taipei: "Today", not "Yesterday"
        assertEquals("Today", taipei.dayLabel("2026-10-09T16:30:00+00:00"))
        assertEquals("Yesterday", taipei.dayLabel("2026-10-09T15:59:00+00:00"))
        assertEquals("8 Oct", taipei.dayLabel("2026-10-08T15:00:00+00:00"))
        assertEquals("31 Dec 2025", taipei.dayLabel("2025-12-31T01:00:00+00:00"))
    }

    @Test
    fun groupingKeepsTheOrder() {
        val items = listOf("2026-10-09T16:30:00+00:00", "2026-10-09T16:31:00+00:00", "2026-10-09T15:59:00+00:00")
        val groups = taipei.groupByDay(items) { it }
        assertEquals(listOf("Today" to 2, "Yesterday" to 1), groups.map { it.first to it.second.size })
    }

    @Test
    fun walletIdsAreMasked() {
        assertEquals("w_beeb •••• 4385", Formats.maskId("w_beeb1c2d3e4f4385"))
        assertEquals("w_short", Formats.maskId("w_short"))
    }

    @Test
    fun entryTypesHaveLabels() {
        assertEquals("Top-up", Formats.typeLabel("TOPUP"))
        assertEquals("Payment", Formats.typeLabel("PAYMENT"))
        assertEquals("SOMETHING_NEW", Formats.typeLabel("SOMETHING_NEW"))
    }
}
