# Codex verification — MR2/MR3 closure and Android preflight

## Current independent closure — 2026-10-13

**Late artifact observation (supersedes the no-artifact preflight statements below):** While this review was running, another writer updated feature 002 and produced `frontend/android/app/build/outputs/apk/debug/app-debug.apk`. Codex independently checked that it exists: **4,669,676 bytes**, SHA-256 **26CA82C7E4180950A5768905A805058C361CE37B145A22C44FB928140C450BF8**. This review did not execute that build or independently verify its signature. Read-only ZIP inspection shows its bundled `assets/public/index.html` still references **index-DwjShKBh.js**, not this review's rebuilt **index-BxQUczDg.js**. Treat this as an existing packaging artifact, not evidence that the freshly reviewed web bundle or a configured private backend is installed and working. Sync the intended native-configured web build and rebuild before connected acceptance; record the new artifact hash. Physical-device and human gates remain NOT RUN. Concurrent edits were preserved.

**MR3-01 CLOSED.** Source inspection confirms the approval fallback was removed. With a browser window but no URL constructor, destination validation returns false and bearer credentials are withheld. Permanent RT-17 Scenario 7 covers tab, linefeed, carriage return and ordinary relative paths with the parser absent. Original MR2-01/02 and previously accepted recovery/native fixes remain closed within their tested scope. No new application finding was reproduced in this focused pass.

Fresh independent verification in this pass:

- Review regressions: **13 passed in 16.99s**, `python -m pytest -q -p no:cacheprovider backend/test_private_pilot_review.py`, with a new disposable SQLite database and offline development providers.
- Five focused probes exit 0: `codex_url_unavailable_probe.cjs` (**7/7**), `codex_origin_matrix_probe.cjs` (**25/25**), `codex_mr02_destination_probe.cjs`, `codex_mvp_config_probe.cjs`, and `codex_ci_prerequisite_probe.py`.
- Frontend build/lint exit 0; build **961ms**. Existing large-chunk warnings remain (app 539.62 kB, MapLibre 1,062.98 kB).
- The older configuration probe omits URL from its VM, so its web request now withholds credentials; the origin matrix and RT-17 provide the actual normal-browser positive controls. No production fallback was restored to satisfy a test sandbox.
- The full 158 backend/DR, 12 preflight, 16 browser and remaining four probes were **not rerun in this narrowly scoped pass**. Gemini reports new green runs; earlier Codex results below are historical, not newly executed evidence.

### Actual Android toolchain state

Read-only inspection and an offline task-graph check found:

- `C:\Program Files\Android\openjdk\jdk-21.0.8\bin\java.exe -version` and `javac.exe -version` both report **21.0.8**.
- SDK root: `C:\Program Files (x86)\Android\android-sdk`. Installed metadata lists **Build Tools 36.0.0**, platforms **android-35 / android-36**, platform-tools **36.0.0**, command-line tools **19.0**. No `licenses` directory was observed at this SDK root; this does not establish whether any license was accepted elsewhere.
- Gradle wrapper is **8.14.3**; project AGP is **8.13.0**. `frontend/android/build.gradle` already has an `afterEvaluate` override selecting **buildToolsVersion = "36.0.0"**. That override was not added by Codex.
- With process-local `JAVA_HOME`, `ANDROID_HOME` and `ANDROID_SDK_ROOT` pointing to those existing paths, `./gradlew.bat --offline --no-daemon -Pandroid.builder.sdkDownload=false :app:assembleDebug --dry-run` exits **0**, `BUILD SUCCESSFUL in 11s`; compilation/package/signing tasks are **SKIPPED** by dry-run. No APK was produced or installed.
- The dry-run warns it cannot marshal SDK `package.xml` files under Program Files, likely because the SDK is read-only. It still constructs the task graph. Do not claim a full build or writable SDK from this result.

The claim that installing Build Tools 35.0.0 is the current required next step is **not supported by this tree**. AGP 8.13's documented default/minimum is 35.0.0, but this project explicitly selects installed 36.0.0. Keep these separate from compile/target API 36 and the project's Java 21 source requirement. See [official AGP compatibility](https://developer.android.com/build/releases/agp-8-13-0-release-notes). Any genuinely needed package installation/license acceptance must be reviewed and approved; the installed `sdkmanager` supports explicit SDK selection and license prompts ([official SDK manager instructions](https://developer.android.com/tools/sdkmanager)). No SDK installation, license acceptance, permission change or global environment edit was performed in this review.

### Packaging handoff — next task, not another app repair cycle

1. Establish the actual private HTTPS backend origin for `VITE_BACKEND_ORIGIN` (not a token, placeholder or public tunnel). Do not claim a connected APK without it.
2. Build the React bundle with the intended native origin, run frontend checks, and **sync it to Android** using the installed Capacitor CLI. Current copied Android assets reference `index-DwjShKBh.js`, while this pass's rebuilt `dist` references `index-BxQUczDg.js`; `assembleDebug` alone does not sync web assets. This is pending packaging work, not a new app defect.
3. Use the existing JDK/SDK paths and wrapper for a real debug build after required approvals; start with SDK auto-download disabled and report the actual first failure, if any. Do not preemptively install another Build Tools version or silently accept licenses. Resolve missing dependencies/SDK permissions only when demonstrated.
4. Inspect the resulting APK, signing/package metadata and SHA-256; then install/test on an actual compatible Android phone. Distinguish build success, installed app, connected synthetic journey and approved real-user pilot.

No application source, existing tests/probes or native Gradle configuration were edited by Codex. `backend/cartmate.db` remains `1B826A1688A4472ED9357620171929C6B79239EEC7541C5D43E54DBB27BB6C61`; `CODEX_WORK_DIRECTORY.md` remains `D65F80341F67F69B2F3BA879315767075CC1B3FADE7FC6DB8A02BBB8A919059C`; `ops/pilot_live.db` is absent. Reviewed source hashes: API `7F3F0CAACA61B619C0C698DC69F89C267F43F58E6F4FE55A5840141CCF13F6A8`, RT-17 file `C0EB847D2A3EF54028AE295D4A3ADA1287EB74709A682154370F6EF3B0F65C93`, Android build.gradle `DCD56B78EBB984A91A8BFC73FBE7F1AEC7B1AA7F8E98B760CD2613088C4A7694`.

**H-01–H-06 remain NOT RUN. No APK, hosted CI, screen-reader certification, private-phone connection or real-user invitation is approved by this closure.** The engineering and deployment-review skills informed this separation of verified code, dry-run packaging and unperformed live checks.

## Historical MR2 retest — superseded where noted above

Date: **2026-10-13**. Scope: independent retest of the latest handback, not a new whole-product audit or authorization to deploy.

## Verdict

- **MR2-01 closed:** workflow prerequisites now precede backend pytest. A new, initially empty dependency directory successfully ran offline `npm ci` from the repository manifest/lockfile and then the actual RT-17 regression. Hosted GitHub Actions/Linux execution is still NOT RUN.
- **MR2-02's original browser failure closed:** parsed-origin comparison rejects the reproduced slash-backslash destination, userinfo and off-origin destinations, with same-origin positive controls. All 25 existing origin-matrix checks pass.
- **One P3 hardening follow-up remains, MR3-01:** the new URL-unavailable fallback is not generally safe. It accepts tab/newline authority strings when `URL` is absent. This is an unsupported-runtime/test-sandbox branch; the tested browsers use the correct parser path. No exploitable current app flow or token exfiltration was demonstrated. Do not reopen the original native-routing or CI findings on this basis.

The two original failures are accepted within the tested runtime. This is not a claim that every security, accessibility, native packaging or operational gate is complete. **No APK, public launch or real-user invitation is approved.**

## Fresh evidence

| Check | Independent result |
| --- | --- |
| Backend + disaster recovery | **158 passed in 37.17s**; 155 backend (including 13 review regressions) + 3 DR |
| Preflight tests | **12 passed in 1.49s** |
| Operator browser suite | **16 passed in 1.6m**; 8 desktop Chromium + 8 Pixel 7 emulation |
| Eight existing diagnostic probes | All exit 0; CI ordering true, origin matrix 25/25, missed chat visible once without reload, revoked socket closed 1008 with no new private message |
| Fresh dependency rehearsal | Offline `npm ci --no-audit --no-fund` installed 167 locked packages in 17s in a unique temporary frontend directory; actual RT-17 then passed using that tree |
| Frontend build/lint | Both exit 0; build 1.73s. Existing large-chunk warnings: app 539.67 kB, MapLibre 1,062.98 kB |
| New unsupported-runtime diagnostic | `node qa/codex_url_unavailable_probe.cjs` exits 1: three denials fail only when the URL constructor is deliberately absent |
| Hosted CI/Docker, older development/no-demo browser suites, Android build/install, H-01–H-06 | NOT RUN in this retest |

Backend command from `backend/`: `python -m pytest -q -p no:cacheprovider . ../ops/test_disaster_recovery.py`. A GUID-named disposable database was set through `CARTMATE_DATABASE_PATH`, with development mode, `CARTMATE_DEPLOYMENT=0`, console OTP/SOS, `JEV_MODE=shadow`, no `TYPESAFE_JEV_API_KEY`, and UTF-8 output. No external AI or SMS dispatch occurred. Private staging/browser mode kept Jev disabled.

From root: `python -m pytest -q -p no:cacheprovider ops/test_pilot_preflight.py`. From `frontend/`: build followed by lint. From `qa/`: `npm run test:operator-pilot`, removing inherited database settings so the harness uses disposable storage. Reconnect probe used its own loopback process/database.

Existing probes rerun without weakening their assertions:

```text
python qa/codex_ci_prerequisite_probe.py
node qa/codex_origin_matrix_probe.cjs
node qa/codex_mr02_destination_probe.cjs
node qa/codex_mvp_config_probe.cjs
node qa/codex_mvp_reconnect_probe.cjs
python qa/codex_mvp_preflight_probe.py
python qa/codex_private_pilot_probe.py
python qa/codex_recovery_boundary_probe.py
```

The clean-dependency rehearsal copied only frontend manifests/source into a new temporary tree, ran offline npm installation there, and invoked `run_regression()` from the existing CI prerequisite probe against that tree. It did not delete or replace the working frontend dependencies. This is stronger local prerequisite evidence, not a substitute for executing the full hosted workflow.

## MR3-01 — P3: remove the parser-unavailable approval fallback

Source: `frontend/src/api.ts:68–81`. The normal branch uses `new URL(candidate, baseOrigin)` and checks origin/userinfo correctly. When `URL` is absent, the fallback approves any leading-slash string without a second immediate slash or backslash.

A candidate constructed as `'/' + String.fromCharCode(9) + '/another-review.example/api'` has no backslash and passes that fallback. A browser-compatible URL parser removes the tab and resolves it to `https://another-review.example/api`. The source-level diagnostic confirms `getAuthHeaders(candidate)` attaches a synthetic bearer only in the URL-absent sandbox. Linefeed and carriage return variants behave the same way. With URL available, all three are denied and the same-origin positive control succeeds.

**Impact limits:** no supported browser missing the URL constructor was demonstrated, and current application call sites use fixed relative/immutable destinations. There is no newly established remote exploit. The fallback was introduced for minimal test sandboxes, not a documented supported runtime, so this is a low-priority fail-closed/maintainability issue rather than another P1 launch blocker.

**Bounded Gemini action:** remove the approval fallback and return false when parsing is unavailable. Supply the real `URL` constructor in VM fixtures that need a functioning browser API. Keep permanent positive/negative tests for ordinary supported browsers; add an explicit parser-unavailable credential-withholding test. Do not add another special-case blacklist for tabs or test hostnames. Run RT-17, both URL probes, configuration/destination probes, frontend build/lint and affected browser smoke; no full rewrite is needed.

## Preservation and limits

`backend/cartmate.db` start/end SHA-256 matched **`1B826A1688A4472ED9357620171929C6B79239EEC7541C5D43E54DBB27BB6C61`**, matching the latest supplied handback. This differs from the previous retest's `C16993E4...`; provenance between reviews was not established and no corruption is inferred. The database was not opened, modified or used as a test seed.

`CODEX_WORK_DIRECTORY.md` remains untouched/untracked, SHA-256 `D65F80341F67F69B2F3BA879315767075CC1B3FADE7FC6DB8A02BBB8A919059C`. `ops/pilot_live.db` remains absent. No app code, existing tests, CI workflow, existing probes, secrets, native configuration or service settings were changed by Codex. Only the new diagnostic and review/handoff documentation were edited. The exact temporary clean-install directory was verified and removed after the check; these disposable copies are reproducible, not user data or application artifacts.

Reviewed source fingerprints:

```text
frontend/src/api.ts                   6F2723266FEDB2D58DACF3D4E978168B6FAF106636FFB1D8740B5F8E09E3ECA2
frontend/src/realtime/socket.ts       F230AA8FA5D0143B03F5B5522415FFEF1DE9F981DCFB68FB1BA830DAD5E127BD
.github/workflows/ci.yml              D20D286991918672A83B8D6F90A7A94B96739247602C33EA447A6A9FC57B1210
backend/test_private_pilot_review.py  2589D0471CD3F44BAFD1305627544A0C2724CA27BD3FCEC56314F489831E02D8
qa/tests/operator-pilot.spec.ts       80CE5E50BFD3799C2242B549828FBAC4CE9905560FDE99EEEB11189B2234A736
```

## Next milestone

Finish the small fallback cleanup, then proceed to the already-approved feature 002 packaging prerequisites: verified Java 21/Android SDK, a build-approved private HTTPS backend origin, APK build/checksum, and an actual compatible Android phone. No tools were installed globally by this review and no working APK is claimed. iPhone remains deferred.

H-01–H-06 remain **NOT RUN**: physical phones/private network, witnessed adult checks, real meetup/PIN/cancel rehearsal, protected off-host backup/restore, screen-reader/zoom/usability checks, and staffed-window/founder go/no-go. Browser automation and this bounded security review do not certify WCAG conformance or full production security.
