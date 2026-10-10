package lab.wallet.data

/**
 * Where the app finds the payment API.
 *
 * The API runs on the developer's machine; the device reaches it at 127.0.0.1 through
 * `adb reverse tcp:<port> tcp:<port>`, so nothing is exposed on the network (SPEC.md §2). Tests point
 * debug builds elsewhere, for example at the test proxy, with the launch extra [EXTRA_BASE_URL].
 * Release builds ignore the extra.
 */
data class ApiConfig(val baseUrl: String) {
    companion object {
        const val EXTRA_BASE_URL = "apiBaseUrl"
        const val DEFAULT_BASE_URL = "http://127.0.0.1:8400"

        /** [override] is the launch extra, or null. Anything that is not an http(s) URL is ignored. */
        fun resolve(override: String?, debugBuild: Boolean): ApiConfig {
            val url = override?.trim()?.trimEnd('/')
            val usable = debugBuild && url != null && Regex("""^https?://[^/\s]+$""").matches(url)
            return ApiConfig(if (usable) url!! else DEFAULT_BASE_URL)
        }
    }
}
