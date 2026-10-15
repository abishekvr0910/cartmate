# CartMate Windows Operator Runbook: Zero-Cost Private Staging Pilot

This runbook guides the operator through hosting, admitting participants, witnessing 18+ age checks, and operating the zero-cost, private two-person Silesia friend test on a local Windows machine.

> [!IMPORTANT]
> - **Zero-cost, private-only:** Do not use public tunnels (e.g. ngrok, localtunnel), paid SMS gateways, or cloud databases.
> - **Hardware availability:** The operator's computer hosts the backend server and SQLite database; it must remain powered on with sleep/hibernate disabled during staffed test windows.
> - **Stop conditions:** If an ordinary public browser can reach the app, or if a non-invited party accesses the private tailnet URL, immediately terminate the process and revoke active sessions.

---

## 1. Prerequisites and Environment Setup

### 1.1 Private Networking (Tailscale)
1. Install [Tailscale for Windows](https://tailscale.com/download/windows).
2. Ensure both the operator's PC and the participant's phone are connected to the same private Tailnet (Personal Free plan).
3. Verify Tailscale connectivity per official documentation: [Tailscale Serve Guide](https://tailscale.com/docs/features/tailscale-serve).
4. Note your tailnet machine name or IP (e.g., `https://<operator-node>.ts.net` or Tailscale Serve HTTPS endpoint).

### 1.2 Build Frontend Bundle
From `S:\APPs\cartmate\frontend`:
```powershell
npm run lint
npm run build
```
This produces optimized production assets in `S:\APPs\cartmate\frontend\dist`.

---

## 2. Server Startup & Moderator Bootstrap

The application must run in single-process mode (`--workers 1`) to ensure SQLite WAL consistency and in-process WebSocket synchronization.

### 2.1 PowerShell Launch Script
Execute from `S:\APPs\cartmate`:

```powershell
# Set operational environment flags
$env:CARTMATE_ENV = "staging"
$env:CARTMATE_OPERATOR_PILOT_ENABLED = "1"
$env:CARTMATE_MANUAL_AGE_PILOT_ENABLED = "1"
$env:CARTMATE_DATABASE_PATH = "S:\APPs\cartmate\ops\pilot_live.db"
$env:CARTMATE_FRONTEND_DIST = "S:\APPs\cartmate\frontend\dist"
$env:SOS_PROVIDER = "disabled"
$env:OTP_PROVIDER = "console"
$env:JEV_MODE = "disabled"
$env:SESSION_TTL_HOURS = "24"
$env:CARTMATE_DEPLOYMENT = "0"

# Explicit allowed origins for private web access and native Android Capacitor WebView:
# Replace <operator-node> with your actual Tailscale node name (from `tailscale status`)
$env:CARTMATE_CORS_ALLOWED_ORIGINS = "https://<operator-node>.ts.net,https://localhost"

# Note: Set to your actual redeemed operator/moderator user ID(s) once generated in Section 3
# $env:CARTMATE_MODERATOR_USER_IDS = "usr_operator_id,usr_friend_id"

# Generate a unique, session-scoped secret for SOS webhooks (min 16 chars)
$env:SOS_WEBHOOK_SECRET = [System.Convert]::ToBase64String((1..24 | ForEach-Object { [byte](Get-Random -Minimum 0 -Maximum 256) }))

# Launch FastAPI on loopback (single worker) with backend in Python module path
python -m uvicorn main:app --app-dir backend --host 127.0.0.1 --port 8000 --workers 1
```

> [!NOTE]
> **Why `--app-dir backend` is required:**
> `backend/main.py` uses flat sibling module imports (`from config import ...`, `import database`). Supplying `--app-dir backend` adds the `backend` directory to `sys.path`, allowing imports to resolve deterministically without modifying repository layout.
>
> **Why `CARTMATE_DEPLOYMENT=0` is used:**
> `config.py:108-166` implements automated deployment enforcement (`assert_deployment_environment`) whenever `CARTMATE_DEPLOYMENT=1`. It enforces explicit staging/production, a non-default `SOS_WEBHOOK_SECRET` (>= 16 chars), and in staging unconditionally requires a non-empty `CARTMATE_STAGING_ALLOWED_PHONES` allowlist (the code check `not STAGING_ALLOWED_PHONE_NUMBERS` triggers whenever `CARTMATE_DEPLOYMENT=1` and `CARTMATE_ENV=staging`, regardless of SMS carrier or provider). In our zero-cost private friend pilot, accounts are admitted in person without carrier SMS (`OTP_PROVIDER=console`), and emergency response is direct-112 only (`SOS_PROVIDER=disabled`). Setting `CARTMATE_DEPLOYMENT=0` allows the server to boot without configuring phone allowlists while preserving all staging invariants (`CARTMATE_ENV=staging`, fail-closed production guards, witnessed 18+ attestation, single-use activation/recovery tokens, disabled console SOS, and bounded 24h session TTL).
>
> **Bootstrap vs. Routine Startup:**
> - **Bootstrap (First-time setup):** Boot server with `CARTMATE_MODERATOR_USER_IDS` unset; issue tokens (Section 3.1); redeem trusted operator accounts (Section 3.2) to obtain user IDs; configure `$env:CARTMATE_MODERATOR_USER_IDS = "usr_op_id,usr_friend_id"` and restart the server (Section 3.3); then perform witnessed 18+ attestations (Section 4). Never promote an ordinary participant by default; preserve the existing full-privilege warning.
> - **Routine (Subsequent sessions):** Boot server with `$env:CARTMATE_MODERATOR_USER_IDS` already populated and point to the existing `ops/pilot_live.db`.

### 2.2 Expose via Tailscale Serve
Using the current Tailscale CLI syntax, expose the local loopback port `8000` over secure private HTTPS:
```powershell
tailscale serve --https=443 http://127.0.0.1:8000
```
*(Verify status via `tailscale serve status`. To turn off: `tailscale serve --https=443 off` or `tailscale serve reset`).*

### 2.3 Run Pilot Security & Readiness Preflight
Before admitting any participants, run the read-only operator preflight script:
```powershell
# Diagnostic bootstrap preflight (allows non-zero blockers while holding for moderator configuration):
python ops/pilot_preflight.py --base-url https://<operator-node>.ts.net

# Final Go/No-Go readiness check before admitting participants (enforces exit code 0 only when fully ready with 0 blockers):
python ops/pilot_preflight.py --base-url https://<operator-node>.ts.net --require-ready

# Or against loopback during local setup:
python ops/pilot_preflight.py --base-url http://127.0.0.1:8000 --allow-loopback --require-ready
```
This confirms that the server is in staging mode, operator pilot is active, SOS is direct-112 only, the active launch region is Silesia, demo credentials return 401, and zero QA helper routes exist on the shipped router. Use `--require-ready` for the final go/no-go command. Without `--require-ready`, the preflight outputs diagnostic status and may report HOLD while waiting for moderator IDs to be configured; do NOT use exit 0 with blockers as permission to invite.

---

## 3. Operator Admission & Moderator Setup Workflow

Operator admission establishes truthful `operator_in_person` account assurance without SMS or third-party identity document collection.

### 3.1 Issuing Activation Tokens
Issue single-use tokens valid for 24 hours:
```powershell
# Token for Operator / Moderator 1:
python ops/pilot_invites.py --db S:\APPs\cartmate\ops\pilot_live.db issue-activation --for "Operator Jan" --hours 24

# Token for Participant Friend / Moderator 2:
python ops/pilot_invites.py --db S:\APPs\cartmate\ops\pilot_live.db issue-activation --for "Friend Anna" --hours 24
```
Give the raw `CMACT-...` tokens to the respective participants in person. Raw tokens are never stored in plain text.

### 3.2 Participant Token Redemption
1. Open the private HTTPS URL on the mobile device browser.
2. Click **Zaloguj / Dołącz**.
3. Select the **🔑 Aktywuj** tab (visible when `operator_pilot_enabled: true`).
4. Enter the `CMACT-...` token, full name, city (*Katowice* or other Silesian launch hub), and optional bio.
5. Click **Aktywuj konto pilotażu**.
6. Note the generated `user.id` from the response (or inspect via `GET /api/users/me`).

### 3.3 Complete Moderator Configuration
To perform adult attestations, the approving account must be present in `CARTMATE_MODERATOR_USER_IDS`. Furthermore, self-approval is forbidden (`current_user.id != user_id`). For a two-person pilot, configure mutual peer moderators:

> [!WARNING]
> **Moderator permissions:** Adding an account ID to `CARTMATE_MODERATOR_USER_IDS` grants broad administrative authority across the platform (access to user reports, suspension/ban capabilities, shadow audit data, and adult attestations). Only grant this role to an explicitly trusted backup operator or co-founder, never to ordinary participants.

1. Stop uvicorn (`Ctrl + C`).
2. Add both redeemed user IDs to `$env:CARTMATE_MODERATOR_USER_IDS` in your PowerShell window:
   ```powershell
   $env:CARTMATE_MODERATOR_USER_IDS = "usr_operator_id,usr_friend_id"
   ```
3. Restart uvicorn:
   ```powershell
   python -m uvicorn main:app --app-dir backend --host 127.0.0.1 --port 8000 --workers 1
   ```

---

## 4. In-Person Witnessed 18+ Age Check Workflow

Operator admission establishes account presence, but live outings and chat remain locked behind the server-enforced 18+ gate until witnessed verification occurs.

1. **Subject Challenge Generation:**
   The subject clicks "Weryfikacja 18+" in the UI (or calls `POST /api/users/me/age-check-challenge` with their Bearer token) to receive a single-use 5-minute challenge code.
2. **In-Person Inspection (Match the recorded method):**
   - **`physical_identity_document`**: Use when visually inspecting an original physical identity document (e.g. Dowód osobisty, Paszport) in person.
   - **`mdowod_qr`**: Use **ONLY** after conducting a live QR code scan through the official government verification portal/scanner. Simply glancing at the mObywatel app screen without scanning the QR code does not verify certificate authenticity and must not be recorded as `mdowod_qr`.
   - *No photo, document number, PESEL, birth date, or scan is ever collected or stored.*
3. **Attestation Submission:**
   The moderator submits the attestation using their moderator account:
   ```powershell
   # Example for physical ID inspection:
   Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/moderation/users/<subject_user_id>/adult-attestation" `
     -Method Post `
     -Headers @{ "Authorization" = "Bearer <moderator_token>" } `
     -ContentType "application/json" `
     -Body (@{
       method = "physical_identity_document"        # or "mdowod_qr" ONLY if scanned via government verifier
       confirmed_over_18 = $true
       subject_present = $true
       subject_consented = $true
       account_bound = $true
       account_challenge = "<challenge_code>"
     } | ConvertTo-Json)
   ```
4. **Mutual Attestation:**
   Moderator 1 attests Friend Anna. Friend Anna (using her moderator token) attests Operator Jan. Both accounts now have active 7-day 18+ admission.

---

## 5. Two-Device Verification: Full Outing & Realtime Journey

> [!NOTE]
> Automated backend tests prove API contract validity, but **only an actual two-phone rehearsal** proves mobile viewport usability, HTTPS certificate trust, WebSocket delivery over private networking, mutual plan acceptance, check-in, and cancellation.

Once both accounts are admitted and 18+ attested, verify the complete live loop between the two handsets:

1. **Publish Outing (Device 1 — Host):**
   - Tap **Nowe wyjście**.
   - Choose category (e.g. *Zakupy spożywcze* / *Biedronka Katowice*), set time and tags.
   - Tap **Opublikuj wyjście**.
   - *Pass Criteria:* The outing publishes immediately. No SMS verification prompt is shown.
2. **Browse & Join (Device 2 — Guest):**
   - Open radar/feed. The newly published outing appears in Katowice.
   - Tap the outing and send a join request (*"Chętnie dołączę do zakupów"*).
3. **Acceptance & Trip Formation (Device 1 — Host):**
   - Host receives the join request notification and taps **Zaakceptuj**.
   - A synchronized Trip is formed with an active chat room and mutual safety PIN.
4. **Realtime WebSocket Chat (Both Devices):**
   - Both devices open the outing chat room.
   - Send messages back and forth in real-time.
   - Verify WebSocket updates deliver messages instantly without page reloads.
5. **Rendezvous PIN Handshake & Plan Settlement:**
   - Both devices verify the 4-digit meeting PIN upon rendezvous.
   - Test shared-cost ledger entry (e.g. 50/50 balance).
6. **Cancellation & Disconnect Rehearsal:**
   - Test one-party cancellation and confirm instant UI reset on the other handset.
   - Test brief host restart / network drop to verify WebSocket auto-reconnect without lost state.

---

## 6. Backup, Integrity & Incident Shutdown

### 6.1 Online Backup During Operation
Run periodically to capture a consistent SQLite WAL snapshot:
```powershell
python ops/cartmate_backup.py --db S:\APPs\cartmate\ops\pilot_live.db --tag pilot_session
```
This produces a point-in-time database snapshot and a SHA-256 JSON manifest in the backup directory.

### 6.2 Encrypted Off-Device Backup Custody
> [!IMPORTANT]
> A local copy on the same machine is **not** an off-device backup. For real pilot operations:
> 1. Copy the generated `.db` snapshot and `.json` manifest to an encrypted external storage volume (e.g. a BitLocker-encrypted USB drive or VeraCrypt container).
> 2. Ensure only the authorized founder/operator holds decryption credentials.
> 3. Verify backup freshness before and after each staffed test window.

### 6.3 Offline Disaster Recovery Drill
Before live pilot sessions, verify database restoration against an isolated target path:
```powershell
# Restore drill against disposable database:
python ops/cartmate_restore.py --backup <path-to-snapshot.db> --target S:\APPs\cartmate\ops\pilot_restore_drill.db
# Verify integrity via automated recovery suite:
python -m pytest ops/test_disaster_recovery.py -q
```

### 6.4 Emergency Incident Stop Procedure
If unauthorized access, unexpected non-tailnet traffic, safety violations, or data leaks occur:
1. **Immediately sever public/network access:**
   ```powershell
   tailscale serve --reset
   ```
2. **Terminate the application server:**
   Press `Ctrl + C` in the uvicorn terminal, or kill the process:
   ```powershell
   Get-Process -Name python | Where-Object { $_.CommandLine -like "*main:app*" } | Stop-Process -Force
   ```
3. **Revoke sessions:** If necessary, run session revocation against the live database before restart.
4. **Inspect audit log and checkpoint database.**

