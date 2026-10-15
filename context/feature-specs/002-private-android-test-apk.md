# 002 — Private Android test APK

**Hosting update (2026-10-13):** The founder chose a paid EC2 staging host for this closed pilot. [The EC2 runbook](../../ops/EC2_STAGING_RUNBOOK.md) supersedes historical zero-cost/local-private-network delivery assumptions below, but not the adult, safety, HTTPS, APK-origin, backup, or physical-device gates. A new domain-bound APK must be built only after the EC2 HTTPS origin works. No EC2 or device result is yet verified.

**Current acceptance (2026-10-13):** [Original MR2-01/02 and MR3-01 failures closed](../../qa/CODEX_MR2_VERIFICATION.md). Native source-level routing and web fail-closed behavior are verified.
**Artifact built and verified:** Private debug APK compiled successfully via `./gradlew assembleDebug` using Java 21 (`C:\Program Files\Android\openjdk\jdk-21.0.8`) and Android SDK 36 (`C:\Program Files (x86)\Android\android-sdk`).
* Artifact: `frontend/android/app/build/outputs/apk/debug/app-debug.apk` (4,849,815 bytes)
* SHA-256: `532060129448B71897FAF56F9DA57D399CC3362D32F00C22F444542C6AA25D82`
* Package: `pl.cartmate.app`, Version 1.0 (code 1), `minSdkVersion 24` (Android 7.0), `targetSdkVersion 36`
* Permissions: `android.permission.INTERNET`, cleartext disabled
* Signature: APK Signature Scheme v2 verified (`apksigner verify -v`)
* **Handset installation / connected physical testing:** NOT YET INSTALLED; requires USB/ADB or sideload onto a physical Android handset with private network connectivity.

Status: **Debug APK compiled and signed; uninstalled on physical device; H-01..H-06 human/device checks NOT RUN.** Generated project uses Java 21; Gradle wrapper 8.14.3, Android Gradle Plugin 8.13.0.
Decision date: 2026-10-12. Founder confirmed an installable Android test build as the next milestone; iPhone is later. Phone models/Android versions are unknown and must not be fabricated. This supersedes the earlier exclusion of APK work, not the no-cost, private-only or safety boundaries.

## Outcome

Deliver a locally built, debug-signed Android APK for a supervised two-adult Silesia test, reusing the existing React application and FastAPI backend. Record the artifact path, SHA-256, version, minimum supported Android version from the generated project, build commands and actual installation result. A compiled APK is not proof of a working connected journey; no public store submission is in scope.

## Observed preflight, not assumptions

- `@capacitor/android@8.5.2` added and locked in `frontend/package.json`. Native Android project generated in `frontend/android` via `npx cap add android` and synced with `npx cap sync android`. `variables.gradle` specifies `minSdkVersion 24`, `compileSdkVersion 36`, `targetSdkVersion 36`. `AndroidManifest.xml` includes only `android.permission.INTERNET`.
- `frontend/capacitor.config.ts` specifies `pl.cartmate.app`, bundled `dist`, HTTPS Android scheme and cleartext disabled.
- JDK 21 (`C:\Program Files\Android\openjdk\jdk-21.0.8`) and Android SDK (`C:\Program Files (x86)\Android\android-sdk`) discovered and used for `./gradlew.bat assembleDebug` (build successful, 2m 12s).
- Backend routing in `frontend/src/api.ts` and `frontend/src/realtime/socket.ts` uses an immutable build-approved native origin; web callers use relative `/api` and ignore storage overrides. Native configuration rejects HTTP, userinfo, query/fragment and paths other than root or `/api`; requests may use full API paths on the approved origin. Unapproved/missing origins receive no bearer and cannot acquire a WS ticket. Source-level tests pass. MR3-01 fail-closed behavior verified.
- There is no verified private HTTPS backend address or physical Android handset connection. No SDK/software installation, native build, signing or deployment was performed during this preflight.
- R2-01/02's reproduced recovery defects remain closed. The latest independent retest passed 158 backend/DR tests (including 13 review cases), 12 preflight tests, 16 operator browser cases and nine diagnostic probes. Do not carry green web tests forward as native evidence.

## Sequence and ownership

Use one writer for shared application files. Existing handoff assigns recovery remediation to Gemini and independent review to Codex. Do not run two agents editing auth/API/config concurrently. Packaging preparation can proceed without approving real-user access; do not silently take over another writer's files.

1. **Preserve recovery fixes and complete acceptance:** retain R2-01/02's independently verified protections and permanent regressions. Complete relevant mandatory R2-03 evidence before a real meetup rehearsal. No privacy-bearing friend test if revoked-session isolation regresses.
2. **Establish build tools:** install or locate a compatible Android Studio/SDK/JDK and verify versions. Obtain normal approval for installations outside the workspace; do not silently accept unrelated licenses, purchase services or assume configured paths work. Use the SDK/build-tool versions required by the generated Capacitor 8 project rather than guessing. Node is already available.
3. **Create native shell:** add matching `@capacitor/android`, keep core/CLI/platform versions compatible and lock the resulting dependencies. Generate the Android project using the installed CLI, retain generated Gradle wrapper/source, and keep local SDK paths, build outputs and signing secrets ignored. No unnecessary native permissions or plugins.
4. **Wire private networking:** bundle the React assets, introduce one validated backend base configuration shared by REST and WS-ticket acquisition, and derive the secure WebSocket endpoint from the same approved backend. Preserve relative same-origin behavior for the website. Require HTTPS/WSS for the pilot, no cleartext/certificate bypass, embedded tokens or arbitrary server-selection input. Confirm the actual WebView Origin and narrowly configure CORS/WS origin policy; an allowed Origin is not authentication. Missing backend configuration must fail clearly, not silently use demo data or claim connectivity. Do not treat Capacitor's remote live-reload URL setting as a production hosting design.
5. **Build internal artifact:** run frontend checks, synchronize web assets to Android, and build the debug APK using the generated Gradle wrapper. Document reproducible commands only after they run. Label it a private test build; verify package metadata and signature. Retain a controlled local debug signing identity for repeat installs and keep secrets out of Git. An APK contains client assets only, never the database/operator credentials/server.
6. **Install and test:** first synthetic accounts, then only the approved supervised human rehearsal. Observe launch, honest disconnected state, activation/recovery, witnessed-age pending state, discovery, join/accept, chat, plan agreement, PIN, cancellation, logout/revocation, network loss, background/foreground and server restart. Check Android back navigation, keyboard-covered controls, safe areas, text scaling and TalkBack. Inspect logs for sensitive data. Never actually call 112; test that the action opens the intended dialer without initiating a call. Record device/OS/WebView versions and results, not “all phones supported.”

## Required regression boundaries

- Bundled native API base and ticket/WS routing are consistent; web routing remains unchanged.
- Invalid/insecure/missing native backend configuration fails visibly and does not redirect bearer tokens to an unapproved destination.
- REST preflight and WS Origin checks accept only the configured client origin; wrong/missing Origin and invalid/used tickets remain rejected according to existing policy. No wildcard broadening to make the APK work.
- Operator admission is staging-only; production stays closed. Phone control and adult assurance are not fabricated by packaging. Moderator powers stay server-owned.
- Existing server session revocation applies to the native client; recovery is not an excuse to keep old subscriptions alive. Native logs and bundled assets contain no authentication secrets.
- Block/report/cancel and emergency guidance remain available according to the original policy. SOS is direct dialer fallback only, never emergency SMS/dispatch.
- Minimize local credential exposure and document the initial storage threat model; do not describe WebView localStorage as encrypted secure storage.

## External inputs and stop conditions

- Founder confirms access to an Android handset when ready; model/version can be supplied then. iPhone packaging is deferred, not part of this APK.
- Actual private-network enrollment and backend HTTPS address must be configured and verified. The host computer must stay running during the test. An APK does not remove that dependency.
- Keep the separate human age check, staffed test window, protected off-host backup and explicit go/no-go from feature 001. No provider fees, public tunnels, SMS purchase, public distribution or app-store account is authorized.
- A missing SDK or real endpoint blocks the corresponding build/connected-test step, not honest planning or synthetic web regression work. Never claim the APK exists before inspecting a successfully built artifact.

## Definition of done for this milestone

Distinguish **buildable**, **installed**, **connected synthetic test passed**, and **approved human pilot**. Deliver a private APK plus checksum and exact build evidence; demonstrate it on at least one actual compatible Android phone before calling it a working handset build. Two-device private testing still needs two authorized clients. Update the active handoff/tracker and list any unperformed hardware/network/human checks. No same-day completion guarantee is supported by the current missing toolchain and endpoint.

## Official references checked 2026-10-12

- [Capacitor environment setup](https://capacitorjs.com/docs/getting-started/environment-setup): current v8 documentation requires Node 22+, Android Studio 2025.2.1+ and an Android SDK; Studio supplies its JDK.
- [Capacitor Android workflow](https://capacitorjs.com/docs/android): platform package and native project workflow.
- [Capacitor configuration](https://capacitorjs.com/docs/config): bundled web assets, server/origin and cleartext settings. Recheck exact installed-version contracts during implementation.
