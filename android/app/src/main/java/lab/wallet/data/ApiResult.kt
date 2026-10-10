package lab.wallet.data

/** The three ways a request can end (SPEC.md §6.2). */
sealed interface ApiResult<out T> {
    /** The API answered with success. [replayed]: Idempotent-Replayed: true, the original result of an earlier request. */
    data class Ok<T>(val value: T, val replayed: Boolean = false) : ApiResult<T>

    /** The API answered with an error: definitive, nothing was charged. */
    data class Refused(val status: Int, val code: String, val message: String) : ApiResult<Nothing>

    /** No usable answer (network error, or a body that is not JSON): the outcome is unknown. */
    data object NoAnswer : ApiResult<Nothing>
}
