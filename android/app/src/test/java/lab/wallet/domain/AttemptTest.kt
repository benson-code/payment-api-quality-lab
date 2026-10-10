package lab.wallet.domain

import kotlinx.coroutines.CompletableDeferred
import kotlinx.coroutines.async
import kotlinx.coroutines.test.runTest
import lab.wallet.data.ApiResult
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

/** The attempt rules of SPEC.md §6.2, against a fake API that records what it was sent. */
class AttemptTest {
    private class FakeApi {
        val sent = mutableListOf<Pair<String, String?>>()
        var answers = ArrayDeque<ApiResult<String>>()
        suspend fun send(amount: String, key: String?): ApiResult<String> {
            sent += amount to key
            return answers.removeFirst()
        }
    }

    private var counter = 0
    private fun attempt(idempotent: Boolean = true) = Attempt(idempotent) { "key-${++counter}" }
    private val ok = ApiResult.Ok("done")
    private val refused = ApiResult.Refused(409, "INSUFFICIENT_BALANCE", "")

    @Test
    fun aKeyIsCreatedOnlyWhenTheAttemptIsSent() = runTest {
        val a = attempt()
        assertNull(a.pendingKey)
        val api = FakeApi().apply { answers += ApiResult.NoAnswer }
        a.submit("30", api::send)
        assertEquals(listOf("30" to "key-1"), api.sent)
    }

    @Test
    fun noAnswerKeepsTheKeyForTheRetry() = runTest {
        val a = attempt()
        val api = FakeApi().apply { answers += listOf(ApiResult.NoAnswer, ok) }
        a.submit("30", api::send)
        assertEquals(Attempt.State.Unknown, a.state.value)
        a.submit("30", api::send)
        assertEquals(api.sent[0].second, api.sent[1].second)
        assertEquals(Attempt.State.Idle, a.state.value)
        assertNull("a successful attempt ends", a.pendingAmount)
    }

    @Test
    fun theSameAmountWrittenDifferentlyKeepsTheKey() = runTest {
        val a = attempt()
        val api = FakeApi().apply { answers += listOf(ApiResult.NoAnswer, ok) }
        a.submit("30", api::send)
        a.submit("30.00", api::send)
        assertEquals(api.sent[0].second, api.sent[1].second)
        assertEquals("the pending attempt's own amount is resent", "30", api.sent[1].first)
    }

    @Test
    fun aDifferentAmountStartsANewAttempt() = runTest {
        val a = attempt()
        val api = FakeApi().apply { answers += listOf(ApiResult.NoAnswer, ok) }
        a.submit("30", api::send)
        a.submit("20", api::send)
        assertNotEquals(api.sent[0].second, api.sent[1].second)
        assertEquals("20", api.sent[1].first)
    }

    @Test
    fun anErrorAnswerEndsTheAttempt() = runTest {
        val a = attempt()
        val api = FakeApi().apply { answers += listOf(refused, ok) }
        a.submit("30", api::send)
        assertEquals(Attempt.State.Refused("INSUFFICIENT_BALANCE", "Not enough balance for this payment."), a.state.value)
        assertNull(a.pendingAmount)
        a.submit("30", api::send)
        assertNotEquals(api.sent[0].second, api.sent[1].second)
    }

    @Test
    fun aSecondSubmitWhileInFlightSendsNothing() = runTest {
        val a = attempt()
        val gate = CompletableDeferred<ApiResult<String>>()
        var calls = 0
        val first = async { a.submit("30") { _, _ -> calls++; gate.await() } }
        testScheduler.runCurrent()                       // the first submit is now waiting for its answer
        assertEquals(Attempt.State.Pending, a.state.value)
        val second = a.submit("30") { _, _ -> calls++; ok }
        assertNull("the second submit is ignored", second)
        gate.complete(ok)
        first.await()
        assertEquals(1, calls)
    }

    @Test
    fun resetIsIgnoredWhileInFlight() = runTest {
        val a = attempt()
        val gate = CompletableDeferred<ApiResult<String>>()
        val first = async { a.submit("30") { _, _ -> gate.await() } }
        testScheduler.runCurrent()
        a.reset()
        assertEquals(Attempt.State.Pending, a.state.value)
        gate.complete(ApiResult.NoAnswer)
        first.await()
        assertEquals("30", a.pendingAmount)
    }

    @Test
    fun topUpsSendNoKey() = runTest {
        val a = attempt(idempotent = false)
        val api = FakeApi().apply { answers += listOf(ApiResult.NoAnswer, ok) }
        a.submit("10", api::send)
        assertEquals(Attempt.State.Unknown, a.state.value)
        a.submit("10", api::send)
        assertTrue(api.sent.all { it.second == null })
    }

    @Test
    fun clearRefusalKeepsAPendingAttempt() = runTest {
        val a = attempt()
        val api = FakeApi().apply { answers += ApiResult.NoAnswer }
        a.submit("30", api::send)
        a.clearRefusal()
        assertEquals("no answer is not a refusal: it stays", Attempt.State.Unknown, a.state.value)
        assertEquals("30", a.pendingAmount)
    }

    @Test
    fun aRestoredAttemptResendsItsKey() = runTest {
        // K-08: the process died while the outcome was unknown; the saved amount and key come back
        val a = attempt()
        a.restore("30", "saved-key")
        assertEquals(Attempt.State.Unknown, a.state.value)
        val api = FakeApi().apply { answers += ok }
        a.submit("30.00", api::send)
        assertEquals(listOf("30" to "saved-key"), api.sent)
    }

    @Test
    fun aRestoredAttemptEndsWhenTheAmountChanges() = runTest {
        val a = attempt()
        a.restore("30", "saved-key")
        val api = FakeApi().apply { answers += ok }
        a.submit("20", api::send)
        assertEquals("key-1", api.sent.single().second)
    }
}
