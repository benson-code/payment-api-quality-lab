package lab.wallet.data

import org.junit.Assert.assertEquals
import org.junit.Test

class ApiConfigTest {
    @Test
    fun debugBuildTakesTheLaunchExtra() {
        assertEquals("http://127.0.0.1:8471", ApiConfig.resolve("http://127.0.0.1:8471/", debugBuild = true).baseUrl)
    }

    @Test
    fun releaseBuildIgnoresTheLaunchExtra() {
        assertEquals(ApiConfig.DEFAULT_BASE_URL, ApiConfig.resolve("http://127.0.0.1:8471", debugBuild = false).baseUrl)
    }

    @Test
    fun noExtraMeansTheDefault() {
        assertEquals(ApiConfig.DEFAULT_BASE_URL, ApiConfig.resolve(null, debugBuild = true).baseUrl)
    }

    @Test
    fun somethingThatIsNotAUrlIsIgnored() {
        for (bad in listOf("", "  ", "127.0.0.1:8400", "ftp://127.0.0.1", "http://", "http://host/path", "javascript:alert(1)")) {
            assertEquals(bad, ApiConfig.DEFAULT_BASE_URL, ApiConfig.resolve(bad, debugBuild = true).baseUrl)
        }
    }
}
