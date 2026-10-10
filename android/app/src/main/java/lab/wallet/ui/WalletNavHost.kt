package lab.wallet.ui

import androidx.compose.animation.EnterTransition
import androidx.compose.animation.ExitTransition
import androidx.compose.runtime.Composable
import androidx.compose.runtime.remember
import androidx.lifecycle.createSavedStateHandle
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.navigation.NavHostController
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import lab.wallet.data.ApiClient
import lab.wallet.domain.Formats
import lab.wallet.ui.screens.HistoryScreen
import lab.wallet.ui.screens.HistoryViewModel
import lab.wallet.ui.screens.HomeScreen
import lab.wallet.ui.screens.HomeViewModel
import lab.wallet.ui.screens.PayScreen
import lab.wallet.ui.screens.PayViewModel
import lab.wallet.ui.screens.PaymentDetailScreen
import lab.wallet.ui.screens.PaymentDetailViewModel
import lab.wallet.ui.screens.StartScreen
import lab.wallet.ui.screens.StartViewModel
import lab.wallet.ui.screens.TopUpScreen
import lab.wallet.ui.screens.TopUpViewModel

/**
 * The screens and how Back moves between them (SPEC.md §4): Start and Home leave the app; History,
 * Top up and Pay return to Home; Payment detail returns to History, wherever it was opened from
 * (from Home or a receipt, History is put on the stack first, as the web's back link does). No
 * transition animations, as on the web.
 */
@Composable
fun WalletNavHost(api: ApiClient, nav: NavHostController = rememberNavController()) {
    val formats = remember { Formats() }
    val home = "home/{wallet}"
    fun toHome() { nav.popBackStack(home, inclusive = false) }
    fun openPayment(walletId: String, paymentId: String, fromHistory: Boolean) {
        if (!fromHistory) nav.navigate("history/$walletId") { popUpTo(home); launchSingleTop = true }
        nav.navigate("payment/$walletId/$paymentId")
    }
    NavHost(
        navController = nav,
        startDestination = "start",
        enterTransition = { EnterTransition.None },
        exitTransition = { ExitTransition.None },
        popEnterTransition = { EnterTransition.None },
        popExitTransition = { ExitTransition.None },
    ) {
        composable("start") {
            StartScreen(viewModel { StartViewModel(api) }) { walletId ->
                nav.navigate("home/$walletId") { popUpTo("start") { inclusive = true } }
            }
        }
        composable(home) { entry ->
            val walletId = entry.arguments?.getString("wallet").orEmpty()
            HomeScreen(
                vm = viewModel { HomeViewModel(api, walletId) },
                formats = formats,
                onTopUp = { nav.navigate("topup/$walletId") },
                onPay = { nav.navigate("pay/$walletId") },
                onHistory = { nav.navigate("history/$walletId") { launchSingleTop = true } },
                onOpenPayment = { openPayment(walletId, it, fromHistory = false) },
                onSwitchWallet = { nav.navigate("start") { popUpTo(nav.graph.id) { inclusive = true } } },
            )
        }
        composable("history/{wallet}") { entry ->
            val walletId = entry.arguments?.getString("wallet").orEmpty()
            HistoryScreen(
                viewModel { HistoryViewModel(api, walletId) },
                formats,
                onHome = { toHome() },
                onPay = { nav.navigate("pay/$walletId") },
                onOpenPayment = { openPayment(walletId, it, fromHistory = true) },
            )
        }
        composable("topup/{wallet}") { entry ->
            val walletId = entry.arguments?.getString("wallet").orEmpty()
            TopUpScreen(viewModel { TopUpViewModel(api, walletId) }, onBack = { toHome() }, onDone = { toHome() })
        }
        composable("pay/{wallet}") { entry ->
            val walletId = entry.arguments?.getString("wallet").orEmpty()
            PayScreen(
                viewModel { PayViewModel(api, walletId, createSavedStateHandle()) },
                formats,
                onBack = { toHome() },
                onDone = { toHome() },
                onViewPayment = { openPayment(walletId, it, fromHistory = false) },
            )
        }
        composable("payment/{wallet}/{payment}") { entry ->
            val paymentId = entry.arguments?.getString("payment").orEmpty()
            PaymentDetailScreen(viewModel { PaymentDetailViewModel(api, paymentId) }, formats, onBack = { nav.popBackStack() })
        }
    }
}
