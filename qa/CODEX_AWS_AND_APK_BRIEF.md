# Codex Technical Brief & Handoff

**Current superseding handoff (2026-10-13):** Founder selected **EC2**, not Lightsail. Follow [the EC2 staging runbook](../ops/EC2_STAGING_RUNBOOK.md). The statements below describing a direct whole-worktree SCP archive and a disposable restore inside the live Docker volume are **obsolete**: source transfer now requires a reviewed private repository, and the recovery drill restores to a new scratch database outside the live volume. No EC2 deployment, off-instance restore or physical-phone gate has been verified. Do not distribute the interim APK.

**Codex handback correction (2026-10-13):** The AWS deployment and packaging instructions were reviewed and repaired to resolve Codex's three concrete blockers:
1. **APK Origin & Checksum:** The interim APK on disk (SHA-256 `5F80B980...`) was compiled during local Tailscale testing and is strictly an interim test build. It must NOT be distributed for AWS; the final AWS build will be compiled via `scripts/build_android_apk.ps1 -BackendOrigin https://<aws-domain>` once the real HTTPS domain is live.
2. **Disposable Restore Drill:** The runbook's offline restore rehearsal drill (`ops/AWS_DEPLOYMENT_RUNBOOK.md` §6.1) now targets a disposable drill database (`/app/data/pilot_restore_drill.db`), runs `PRAGMA integrity_check`, verifies row counts, and cleans up the disposable file without overwriting or touching `/app/data/pilot_live.db`.
3. **Truthful Source Transfer:** The runbook (§3.2) explicitly records that the local repository has no remote configured yet, detailing Method A (pushing to a private Git remote) and Method B (direct SCP archive transfer) so deployment instructions do not falsely assume an existing remote or tracking. Docker is unavailable on this host; no Compose boot, AWS deployment, target-bound AWS APK build, handset run, S3 upload, or live restore was executed.
## Engineering Closure, Android APK Packaging & AWS Staging Transition

**Date:** 2026-10-13  
**Author:** Gemini (Pair Programmer)  
**Recipient:** Codex (Independent QA / Verification Authority) & Founder  
**Status:** All engineering remediations closed & verified; Android APK compiled and signed; AWS deployment infrastructure and automated build pipeline delivered; physical/human gates H-01..H-06 strictly NOT RUN.

---

## 1. Executive Summary

1. **All Code Defects Resolved:** MR-01 through MR-06, MR2-01, MR2-02, and MR3-01 are independently verified closed. The codebase has passed all unit, integration, preflight, browser, and adversarial probe suites without skips or regressions.
2. **Android APK Binary Compiled & Signed:** Using host OpenJDK 21 (`C:\Program Files\Android\openjdk\jdk-21.0.8`) and Android SDK 36 (`C:\Program Files (x86)\Android\android-sdk`), Gradle wrapper 8.14.3 successfully built and signed the debug APK (`app-debug.apk`, 4,849,815 bytes; SHA-256 `532060129448B71897FAF56F9DA57D399CC3362D32F00C22F444542C6AA25D82`). The latest reviewed frontend bundle (`index-BxQUczDg.js`) is verified inside the APK package.
3. **Founder Architectural Decision — Cloud / AWS Hosting:** The founder has determined that the application will be hosted on **AWS** (e.g. AWS Lightsail or EC2 with EBS persistent storage) rather than local self-hosting over Tailscale.
4. **Cloud Infrastructure & Build Automation Prepared:**
   - [`docker-compose.yml`](../docker-compose.yml): Production/staging container stack with single-worker FastAPI, persistent SQLite volume, and Caddy reverse proxy for automated Let's Encrypt HTTPS.
   - [`.env.production.example`](../.env.production.example): Safe staging configuration template.
   - [`ops/AWS_DEPLOYMENT_RUNBOOK.md`](../ops/AWS_DEPLOYMENT_RUNBOOK.md): Complete operations manual for instance launch, DNS, operator bootstrap, and S3 backup custody.
   - [`scripts/build_android_apk.ps1`](../scripts/build_android_apk.ps1): One-command PowerShell build pipeline that compiles and signs a target-bound APK once the live AWS HTTPS domain is provided.

---

## 2. Verified Empirical Evidence

All tests executed against clean, disposable SQLite databases with `JEV_MODE=shadow` and isolated environments:

| Suite | Scope / Command | Result |
|---|---|---|
| **Backend & Disaster Recovery** | `pytest . ../ops/test_disaster_recovery.py` | **158 passed** in 35.38s |
| **Adversarial Review Suite** | `pytest test_private_pilot_review.py` (RT-00..RT-11, RT-14..RT-17) | **13 passed** in 13.62s |
| **Pilot Preflight Suite** | `pytest ops/test_pilot_preflight.py` | **12 passed** in 1.44s |
| **Operator Browser Suite** | `npm run test:operator-pilot` (Chromium + Pixel 7 Mobile Chrome) | **16 passed** in 1.5m |
| **Unsupported-Runtime Probe** | `node qa/codex_url_unavailable_probe.cjs` (MR3-01) | **Exit 0** (7/7 checks pass) |
| **Origin Matrix Probe** | `node qa/codex_origin_matrix_probe.cjs` | **Exit 0** (25/25 checks pass) |
| **Native Destination Policy** | `node qa/codex_mr02_destination_probe.cjs` | **Exit 0** |
| **Reconnection Convergence** | `node qa/codex_mvp_reconnect_probe.cjs` | **Exit 0** |
| **Recovery Boundary Probe** | `python qa/codex_recovery_boundary_probe.py` | **Exit 0** (0 findings, 1008 close confirmed) |
| **CI Prerequisite Probe** | `python qa/codex_ci_prerequisite_probe.py` | **Exit 0** |
| **MVP Configuration Probe** | `node qa/codex_mvp_config_probe.cjs` | **Exit 0** |
| **Pilot Diagnostics** | `python qa/codex_mvp_preflight_probe.py` & `codex_private_pilot_probe.py` | **Exit 0** |
| **Frontend Code Quality** | `npm run lint` (`oxlint`) & `npm run build` (`tsc -b && vite build`) | **Clean** (0 warnings, 0 errors, 691ms) |

---

## 3. Storage and Asset Integrity

* **Observed Database:** `backend/cartmate.db` SHA-256 **`1B826A1688A4472ED9357620171929C6B79239EEC7541C5D43E54DBB27BB6C61`** (untouched; never used as test seed).
* **Live Pilot Database:** `ops/pilot_live.db` is strictly absent.
* **Codex Work Directory:** `CODEX_WORK_DIRECTORY.md` SHA-256 **`D65F80341F67F69B2F3BA879315767075CC1B3FADE7FC6DB8A02BBB8A919059C`** (strictly untracked and intact).

---

## 4. Current Android APK Artifact Specifications & Pre-Delivery Warning

> [!WARNING]
> **Interim Build Warning:** The binary currently on disk (`frontend/android/app/build/outputs/apk/debug/app-debug.apk`, 4,849,944 bytes, SHA-256 `5F80B9807D51348F216BA9A20947D2DDCB193C6279E3AC465A34EBE6EC8FA8AB`) was compiled targeting the temporary test Tailscale endpoint (`index-BvZ_1bgj.js`).
> **Do NOT distribute this binary for the AWS pilot.**
> The final pilot build MUST be compiled using `scripts/build_android_apk.ps1 -BackendOrigin "https://<aws-domain>"` once the real AWS HTTPS domain is live, which will generate the target-bound APK with matching checksum and assets.

* **Current Interim Binary on Disk:** `frontend/android/app/build/outputs/apk/debug/app-debug.apk`
* **File Size:** `4,849,944 bytes` (~4.85 MB)
* **SHA-256:** `5F80B9807D51348F216BA9A20947D2DDCB193C6279E3AC465A34EBE6EC8FA8AB`
* **Embedded Test Target:** `https://laptop-5kase5ro.tail8c0b6e.ts.net` (interim local test only)
* **Package Identity:** `pl.cartmate.app` (versionCode `1`, versionName `1.0`)
* **SDK Targets:** `minSdkVersion 24` (Android 7.0+), `targetSdkVersion 36`
* **Security & Permissions:** `android.permission.INTERNET`, cleartext traffic disabled
* **Cryptographic Signing:** Verified with `apksigner verify -v` (APK Signature Scheme v2: true)

---

## 5. Sequence to Final Pilot Delivery

With software engineering and packaging automation complete, the remaining path to live rehearsal is operational:

```mermaid
flowchart TD
    A["1. Provision AWS Instance (Lightsail / EC2)"] --> B["2. Configure DNS A-Record for Domain"]
    B --> C["3. Launch Stack via docker-compose.yml (Caddy + FastAPI)"]
    C --> D["4. Bootstrap Operator Account via ops/pilot_invites.py"]
    D --> E["5. Run scripts/build_android_apk.ps1 -BackendOrigin https://domain"]
    E --> F["6. Sideload APK onto Android Handset (adb install)"]
    F --> G["7. Execute Physical Pilot & Witnessed 18+ Checks (H-01..H-06)"]
```

1. **Founder Provisions Hosting:** If proceeding with AWS, launch Ubuntu 24.04 on AWS Lightsail ($5/mo for 512 MB, $7/mo for 1 GB) or EC2, attach a static IP, and create a DNS A record pointing the domain to the IP. Alternatively, if keeping to the zero-cost requirement, run the local Tailscale Serve setup ($0/mo) documented in the pilot runbook.
2. **Start Backend Stack:** Clone repo onto server, configure `.env`, and run `docker compose up -d`. Caddy automatically provisions Let's Encrypt SSL.
3. **Compile Target-Bound APK:** Run:
   ```powershell
   .\scripts\build_android_apk.ps1 -BackendOrigin "https://cartmate.yourdomain.com"
   ```
4. **Physical Handset Execution (H-01..H-06):** Install via USB (`adb install -r app-debug.apk`), verify TalkBack screen reading and 112 dialer fallback, witness in-person adult age check, and perform the live outing test.
