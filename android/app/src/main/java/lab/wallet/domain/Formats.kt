package lab.wallet.domain

import java.time.Clock
import java.time.LocalDate
import java.time.OffsetDateTime
import java.time.ZoneId
import java.time.format.DateTimeFormatter
import java.util.Locale

/**
 * Dates, IDs and entry types as the screens show them. Same behaviour as web/src/format.js.
 *
 * The API returns UTC timestamps ("2026-10-10T06:31:12.345+00:00"); they are shown in the device's time
 * zone (SPEC D-03). [clock] decides "today"; tests pass a fixed one.
 */
class Formats(private val clock: Clock = Clock.systemDefaultZone()) {
    private val zone: ZoneId get() = clock.zone
    private val time = DateTimeFormatter.ofPattern("HH:mm", Locale.UK)
    private val day = DateTimeFormatter.ofPattern("d MMM", Locale.UK)
    private val dayYear = DateTimeFormatter.ofPattern("d MMM yyyy", Locale.UK)

    private fun local(iso: String) = OffsetDateTime.parse(iso).atZoneSameInstant(zone)

    /** "14:31" */
    fun time(iso: String): String = local(iso).format(time)

    /** "10 Oct 2026, 14:31" */
    fun dateTime(iso: String): String = local(iso).let { it.format(dayYear) + ", " + it.format(time) }

    /** The heading a row is grouped under: "Today", "Yesterday", "9 Oct", or "9 Oct 2025" in another year. */
    fun dayLabel(iso: String): String {
        val date = local(iso).toLocalDate()
        val today = LocalDate.now(clock)
        return when {
            date == today -> "Today"
            date == today.minusDays(1) -> "Yesterday"
            date.year == today.year -> date.format(day)
            else -> date.format(dayYear)
        }
    }

    /** Items grouped by day, keeping their order. */
    fun <T> groupByDay(items: List<T>, createdAt: (T) -> String): List<Pair<String, List<T>>> {
        val groups = mutableListOf<Pair<String, MutableList<T>>>()
        for (item in items) {
            val label = dayLabel(createdAt(item))
            if (groups.isNotEmpty() && groups.last().first == label) groups.last().second.add(item)
            else groups.add(label to mutableListOf(item))
        }
        return groups
    }

    companion object {
        /** "w_beeb1c2d3e4f4385" -> "w_beeb •••• 4385", as banking apps show account numbers (SPEC D-04). */
        fun maskId(id: String): String = if (id.length > 12) "${id.take(6)} •••• ${id.takeLast(4)}" else id

        private val TYPES = mapOf(
            "TOPUP" to "Top-up",
            "PAYMENT" to "Payment",
            "REFUND" to "Refund",
            "TRANSFER_IN" to "Transfer in",
            "TRANSFER_OUT" to "Transfer out",
        )

        /** The ledger's entry types, as the user reads them. */
        fun typeLabel(type: String): String = TYPES[type] ?: type
    }
}
