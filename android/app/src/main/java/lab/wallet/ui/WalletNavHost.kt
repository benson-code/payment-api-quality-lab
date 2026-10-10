package lab.wallet.ui

import androidx.compose.animation.EnterTransition
import androidx.compose.animation.ExitTransition
import androidx.compose.runtime.Composable
import androidx.compose.runtime.remember
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
import lab.wallet.ui.screens.StartScreen
import lab.wallet.ui.screens.StartViewModel
import lab.wallet.ui.screens.TopUpScreen
import lab.wallet.ui.screens.TopUpViewModel

/**
 * The screens and how Back moves between them (SPEC.md §4): Start and Home leave the app, History
 * returns to Home, Top up returns to Home. No transition animations, as on the web.
 */
@Composable
fun WalletNavHost(api: ApiClient, nav: NavHostController = rememberNavController()) {
    val formats = remember { Formats() }
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
        composable("home/{wallet}") { entry ->
            val walletId = entry.arguments?.getString("wallet").orEmpty()
            HomeScreen(
                vm = viewModel { HomeViewModel(api, walletId) },
                formats = formats,
                onTopUp = { nav.navigate("topup/$walletId") },
                onHistory = { nav.navigate("history/$walletId") { launchSingleTop = true } },
                onSwitchWallet = { nav.navigate("start") { popUpTo(nav.graph.id) { inclusive = true } } },
            )
        }
        composable("history/{wallet}") { entry ->
            val walletId = entry.arguments?.getString("wallet").orEmpty()
            HistoryScreen(viewModel { HistoryViewModel(api, walletId) }, formats, onHome = { nav.popBackStack() })
        }
        composable("topup/{wallet}") { entry ->
            val walletId = entry.arguments?.getString("wallet").orEmpty()
            TopUpScreen(viewModel { TopUpViewModel(api, walletId) }, onBack = { nav.popBackStack() }, onDone = { nav.popBackStack() })
        }
    }
}
