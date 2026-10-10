package lab.wallet.data

import java.io.IOException
import java.net.HttpURLConnection
import java.net.URL
import java.net.URLEncoder
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONArray
import org.json.JSONException
import org.json.JSONObject

/**
 * Every call to the payment API. Same behaviour as web/src/api.js: amounts are sent as the strings the
 * user typed (the API parses them into integer cents), an error answer is [ApiResult.Refused], and no
 * answer or a non-JSON answer is [ApiResult.NoAnswer].
 */
class ApiClient(private val config: ApiConfig) {

    suspend fun createWallet(owner: String): ApiResult<Wallet> =
        request("POST", "/wallets", JSONObject().put("owner", owner)) { Wallet.from(it) }

    suspend fun getWallet(walletId: String): ApiResult<Wallet> =
        request("GET", "/wallets/${seg(walletId)}") { Wallet.from(it) }

    suspend fun topUp(walletId: String, amount: String): ApiResult<TopUp> =
        request("POST", "/wallets/${seg(walletId)}/topups", JSONObject().put("amount", amount)) { TopUp.from(it) }

    /** The ledger, oldest first, as the API returns it. */
    suspend fun transactions(walletId: String): ApiResult<List<Entry>> =
        request("GET", "/wallets/${seg(walletId)}/transactions") { j ->
            val rows: JSONArray = j.getJSONArray("transactions")
            List(rows.length()) { Entry.from(rows.getJSONObject(it)) }
        }

    private fun seg(value: String): String = URLEncoder.encode(value, "UTF-8").replace("+", "%20")

    private suspend fun <T> request(
        method: String,
        path: String,
        body: JSONObject? = null,
        key: String? = null,
        parse: (JSONObject) -> T,
    ): ApiResult<T> = withContext(Dispatchers.IO) {
        val connection = (URL(config.baseUrl + path).openConnection() as HttpURLConnection).apply {
            requestMethod = method
            connectTimeout = 10_000
            readTimeout = 15_000
            setRequestProperty("Accept", "application/json")
            if (key != null) setRequestProperty("Idempotency-Key", key)
            if (body != null) {
                doOutput = true
                setRequestProperty("Content-Type", "application/json")
            }
        }
        try {
            if (body != null) connection.outputStream.use { it.write(body.toString().toByteArray()) }
            val status = connection.responseCode
            val stream = if (status in 200..299) connection.inputStream else connection.errorStream
            val text = stream?.bufferedReader()?.use { it.readText() } ?: return@withContext ApiResult.NoAnswer
            val json = JSONObject(text)
            if (status in 200..299) {
                ApiResult.Ok(parse(json), replayed = connection.getHeaderField("Idempotent-Replayed") == "true")
            } else {
                ApiResult.Refused(status, json.optString("error_code", "UNKNOWN"), json.optString("message"))
            }
        } catch (e: IOException) {
            ApiResult.NoAnswer
        } catch (e: JSONException) {
            ApiResult.NoAnswer          // an answer without a JSON body: not a usable answer
        } finally {
            connection.disconnect()
        }
    }
}
