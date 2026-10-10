package lab.wallet.ui.screens

import lab.wallet.data.ApiResult
import lab.wallet.domain.Messages

/** Data a screen shows after loading it: [data], or the message for why it could not be loaded. */
data class Loaded<T>(val data: T? = null, val error: String? = null)

fun <T> ApiResult<T>.toLoaded(): Loaded<T> = when (this) {
    is ApiResult.Ok -> Loaded(data = value)
    is ApiResult.Refused -> Loaded(error = Messages.forCode(code))
    ApiResult.NoAnswer -> Loaded(error = Messages.NO_ANSWER)
}
