package lab.wallet.domain

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class MoneyTest {
    @Test
    fun displayGroupsThousandsAndKeepsTheCents() {
        assertEquals("0.00", Money.display("0.00"))
        assertEquals("999.99", Money.display("999.99"))
        assertEquals("1,000.00", Money.display("1000.00"))
        assertEquals("12,345.60", Money.display("12345.60"))
        assertEquals("1,234,567.89", Money.display("1234567.89"))
        assertEquals("-7.00", Money.display("-7.00"))
    }

    @Test
    fun signedUsesPlusAndTheTypographicMinus() {
        assertEquals("+100.00", Money.signed("100.00"))
        assertEquals("−30.00", Money.signed("-30.00"))
        assertEquals("−1,234.50", Money.signed("-1234.50"))
    }

    @Test
    fun centsRoundTripWithoutFloatingPoint() {
        // 19.99 * 100 is 1998.9999... in floating point; the API's float_math defect loses that cent
        assertEquals(1999L, Money.toCents("19.99"))
        assertEquals(10050L, Money.toCents("100.5"))
        assertEquals(3000L, Money.toCents("30"))
        assertEquals(-5L, Money.toCents("-0.05"))
        assertEquals("19.99", Money.fromCents(1999))
        assertEquals("-0.05", Money.fromCents(-5))
        assertEquals("0.00", Money.fromCents(0))
        assertEquals("50000.00", Money.fromCents(5_000_000))
    }

    @Test
    fun normalizeAcceptsOnlyPlainAmounts() {
        assertEquals("30.00", Money.normalize("30"))
        assertEquals("30.50", Money.normalize(" 30.5 "))
        assertEquals("0.01", Money.normalize("0.01"))
        // The client does not validate (R-02): these go to the API as typed, and Confirm shows them as typed
        for (notPlain in listOf("", "-1", "1e3", "10.555", "1,000", "abc", ".5", "5.")) {
            assertNull(notPlain, Money.normalize(notPlain))
        }
    }

    @Test
    fun sameAmountComparesMoneyNotText() {
        assertTrue(Money.sameAmount("30", "30.00"))
        assertTrue(Money.sameAmount(" 30.5", "30.50"))
        assertFalse(Money.sameAmount("30", "20"))
        assertTrue(Money.sameAmount("1e3", "1e3"))       // not plain: compared as typed
        assertFalse(Money.sameAmount("1e3", "1000"))
    }
}
