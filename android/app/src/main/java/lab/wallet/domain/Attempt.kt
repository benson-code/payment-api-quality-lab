package lab.wallet.domain

import java.util.UUID
import java.util.concurrent.atomic.AtomicBoolean
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import lab.wallet.data.ApiResult

/**
 * Sending an amount: top-up, payment, refund. Same rules as web/src/useAttempt.js (SPEC.md §6.2).
 *
 * One attempt = one amount the user confirmed, with one Idempotency-Key when the API takes one.
 * - K-01 The key is created when the attempt is first sent, not before.
 * - K-02 While a request is in flight, another submit sends nothing: the flag is set before anything
 *   suspends, so a second tap that arrives before the screen redraws is ignored too.
 * - K-03 No answer: the outcome is unknown. The attempt and its key are kept; the next submit of the
 *   same amount resends the same key, so a request the server already processed is not charged again.
 * - K-04 An error answer is definitive and nothing was charged: the attempt ends.
 * - K-05 Only a different amount (compared as money: "30" is "30.00") ends a pending attempt.
 * - K-07 Top-ups take no key ([idempotent] = false): the screen offers no Retry after no answer.
 *
 * Plain Kotlin, so these rules are unit-tested on the JVM (AttemptTest).
 */
class Attempt(
    private val idempotent: Boolean,
    private val newKey: () -> String = { UUID.randomUUID().toString() },
) {
    sealed interface State {
        data object Idle : State
        data object Pending : State
        data class Refused(val code: String, val message: String) : State
        data object Unknown : State
    }

    private data class Sent(val amount: String, val key: String?)

    private val _state = MutableStateFlow<State>(State.Idle)
    val state: StateFlow<State> = _state.asStateFlow()

    private val inFlight = AtomicBoolean(false)
    private var pending: Sent? = null

    /** The amount of the attempt still waiting for an answer, or null. */
    val pendingAmount: String? get() = pending?.amount

    /** The key of that attempt, or null (for the process-death rule K-08, which persists it). */
    val pendingKey: String? get() = pending?.key

    /**
     * Sends [amount] with [send], unless a request is already in flight (then returns null at once).
     * Returns the API's result; [state] tells the screen what to show.
     */
    suspend fun <T> submit(amount: String, send: suspend (amount: String, key: String?) -> ApiResult<T>): ApiResult<T>? {
        if (!inFlight.compareAndSet(false, true)) return null
        try {
            pending?.let { if (!Money.sameAmount(it.amount, amount)) pending = null }
            val attempt = pending ?: Sent(amount, if (idempotent) newKey() else null).also { pending = it }
            _state.value = State.Pending
            val result = send(attempt.amount, attempt.key)
            when (result) {
                is ApiResult.Ok -> { pending = null; _state.value = State.Idle }
                is ApiResult.Refused -> { pending = null; _state.value = State.Refused(result.code, Messages.forCode(result.code)) }
                ApiResult.NoAnswer -> _state.value = State.Unknown
            }
            return result
        } finally {
            inFlight.set(false)
        }
    }

    /**
     * Brings back an attempt saved before the app's process was killed (K-08). Its outcome is unknown:
     * the request may or may not have reached the server, so the screen offers Retry with the same key.
     */
    fun restore(amount: String, key: String?) {
        if (inFlight.get()) return
        pending = Sent(amount, key)
        _state.value = State.Unknown
    }

    /** Ends the attempt without sending (the user changed the amount). Ignored while in flight. */
    fun reset() {
        if (inFlight.get()) return
        pending = null
        _state.value = State.Idle
    }

    /** Clears a refusal message after the user edits the field; a pending attempt is kept (K-05). */
    fun clearRefusal() {
        if (_state.value is State.Refused) _state.value = State.Idle
    }
}
