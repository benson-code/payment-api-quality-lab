# Wallet — Android app

The native Android client of the wallet: Kotlin and Jetpack Compose, the same screens and behaviour
as the web page (`../web/`), both defined by [`../SPEC.md`](../SPEC.md). Status: project skeleton and
design system done; the screens are being built (SPEC.md marks each app rule *planned* until it is).

## Build

Requires JDK 17 or later and an Android SDK with platform 36.

```bash
cd android
echo "sdk.dir=/path/to/android-sdk" > local.properties   # or set ANDROID_HOME
./gradlew assembleDebug testDebugUnitTest                # app/build/outputs/apk/debug/app-debug.apk
```

The Gradle wrapper pins Gradle 8.14.5 by SHA-256; CI also checks the wrapper jar against Gradle's
published checksums.

### On an ARM64 Linux machine

Google publishes `aapt2`, the resource compiler the build runs, for x86-64 Linux only. The project's
development machine (Oracle Cloud Ampere, ARM64) builds anyway by running the official x86-64
`aapt2` that matches this AGP version through QEMU user-mode emulation:

```bash
sudo apt-get install --no-install-recommends qemu-user libc6-amd64-cross libgcc-s1-amd64-cross
# wrapper script around the official aapt2 (com.android.tools.build:aapt2:8.13.2-14304508, linux)
#   exec qemu-x86_64 -L /usr/x86_64-linux-gnu /path/to/aapt2.x86_64 "$@"
# in ~/.gradle/gradle.properties (never in the repository):
#   android.aapt2FromMavenOverride=/path/to/that/wrapper
```

`--no-install-recommends` keeps `binfmt` out: only this one program runs emulated. Two things that
did not work, for the record: Ubuntu's own arm64 `aapt2` (package `aapt`, Android 14 era) cannot read
platform 36's `android.jar`, and command-line tools 23.0 replaced the Java `sdkmanager` with an x86-64
binary (version 19.0 still works). When AGP is upgraded, the wrapper must point at the matching
`aapt2` version. CI builds on x86-64 runners and needs none of this.

## Versions

All in [`gradle/libs.versions.toml`](gradle/libs.versions.toml): AGP 8.13.2, Kotlin 2.3.21, Compose BOM
2025.12.01; compileSdk and targetSdk 36, minSdk 26. AGP 9 is not used yet: it changes the build DSL and
the Kotlin setup, and the ARM64 machine needs the `aapt2` that matches the AGP version.

## Design system

The app and the web take their design tokens from the same Figma file (SPEC.md §3).

- `ui/theme/DesignTokens.kt` holds the colours, spacing, radii and text styles under their Figma names
  (`color/bg/page`, `Display/Balance`), as plain Kotlin.
- `ui/theme/Theme.kt` turns them into `WalletColors`, `WalletType`, `WalletSpacing` and `WalletRadius`.
- **`DesignTokenParityTest`** reads the web's `web/src/tokens.css` and fails if any value differs. It
  was checked by changing one colour, one spacing value and one line height in the app: each of the
  three tests failed on its own change.
- Components in `ui/components/` are named after their Figma components (`TopBar`, `WalletButton`,
  `Message`, ...). Touch targets are at least 48 dp (SPEC.md L-02).
- Icons are vector drawables with the same paths as the web's icon set.

## Test hooks

Compose `testTag`s are exposed as resource-ids (`testTagsAsResourceId` on the root), under the same
names as the web's `data-testid` (SPEC.md §7). Appium needs
`appium:disableIdLocatorAutocompletion: true`; otherwise it prefixes the ID with `lab.wallet:id/` and
finds nothing.

## Reaching the API

The app calls `http://127.0.0.1:8400`; on a device or emulator, `adb reverse tcp:8400 tcp:8400`
forwards that to the API on the host, so nothing is exposed on the network. Debug builds accept
another base URL as the launch extra `apiBaseUrl` (tests use it to put the test proxy in between);
release builds ignore it. Cleartext HTTP is allowed only for `127.0.0.1` and `10.0.2.2`.

## Third-party assets

| Asset | Source | Licence |
|---|---|---|
| Inter 4.1, Regular / Medium / SemiBold / Bold (`app/src/main/res/font/`) | [rsms/inter release v4.1](https://github.com/rsms/inter/releases/tag/v4.1), `extras/ttf/` | SIL Open Font License 1.1, copy in `app/src/main/assets/licenses/Inter-OFL.txt` |

The release publishes no checksum, so the files could not be verified against one; they were
downloaded from the release page over HTTPS. Their SHA-256, to detect any later change:

```
40d692fce188e4471e2b3cba937be967878f631ad3ebbbdcd587687c7ebe0c82  inter_regular.ttf
97ad806f526e41546d46365bb3a393145f75b7b1568913db74549ad8b8dba872  inter_medium.ttf
78a843fade9d4612a5567302fb595b56976eb5fcebf4fea5a5912d638bafcde3  inter_semibold.ttf
288316099b1e0a47a4716d159098005eef7c0066921f34e3200393dbdb01947f  inter_bold.ttf
```

The web bundles Inter from the `@fontsource/inter` package (Google Fonts build); both are Inter 4 and
look the same, but they are not byte-identical files.
