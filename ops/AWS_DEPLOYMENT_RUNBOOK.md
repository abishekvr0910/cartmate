# CartMate AWS & Cloud Deployment Runbook

**Current hosting choice: EC2.** Use the [EC2 staging runbook](EC2_STAGING_RUNBOOK.md) for instance provisioning and launch. The Lightsail-specific steps below remain an alternative reference; the safe scratch restore procedure in Section 6.1 is shared by either host.

This guide prepares a closed, operator-admitted Silesia staging pilot on **AWS Lightsail** with persistent SQLite storage and Caddy HTTPS. Start with the [founder's first-deploy checklist](FOUNDER_AWS_FIRST_DEPLOY.md). It is not a record of a live deployment. An internet-facing hostname is publicly reachable even though social actions require admission and adult approval. Confirm costs, access policy and operator staffing before inviting people.

---

## 1. Cloud Architecture Overview

* **Host Machine:** Single Ubuntu 24.04 Lightsail instance. As checked against AWS's [current bundle list](https://docs.aws.amazon.com/lightsail/latest/userguide/amazon-lightsail-bundles.html) on 2026-10-13, the public-IPv4 Linux 2 GB/2-vCPU/60-GB plan is listed at **USD 12/month**. This is the recommended pilot size to leave room for a Docker frontend build; it is not a measured capacity guarantee. Confirm the console price before creating it. Domain registration, snapshots and S3 backups may add charges. Budget alerts are not a spending cap, and a stopped instance remains billable.
* **Storage Layer:** Named Docker volume (`cartmate-data`) mapped to persistent EBS storage, preserving `pilot_live.db` across container restarts.
* **Process Concurrency:** Single worker (`--workers 1`) to guarantee SQLite WAL lock integrity and in-process WebSocket connection state.
* **TLS & Reverse Proxy:** Caddy reverse proxy automatically obtains, renews, and serves SSL/TLS certificates via Let's Encrypt, routing REST (`/api`) and WebSockets (`/ws`) over HTTPS on port 443.
* **WebRTC TURN Relay:** A pinned coturn container listens on UDP/TCP 3478 and relay ports 49160-49200. The current Compose file requires `CARTMATE_TURN_SECRET`, `CARTMATE_TURN_EXTERNAL_IP`, and `CARTMATE_TURN_PRIVATE_IP`; see the EC2 runbook for the authoritative setup.

---

## 2. Server Provisioning & DNS

### 2.1 Launch Instance
1. **AWS Lightsail (Recommended for simplicity & fixed cost):**
   * Go to AWS Lightsail Console -> **Create instance**.
   * Platform: **Linux/Unix** | Blueprint: **OS Only -> Ubuntu 24.04 LTS**.
   * Plan: **2 GB RAM / 2 vCPUs / 60 GB SSD** (listed at **USD 12/month** on 2026-10-13). Confirm the plan and price shown in your AWS console.
   * Under **Networking**, create and attach a **Static IP**.
   * In **IPv4 Firewall**, ensure ports **80** (HTTP), **443** (HTTPS), **3478** UDP/TCP, and **49160-49200** UDP are open.
2. Keep SSH (22) available only for administration, and do not open the application container's port 8000 to the internet.

### 2.2 Configure DNS
Create a DNS **A record** with your domain registrar:
```text
Type:  A
Name:  cartmate (or @ for root)
Value: <STATIC_PUBLIC_IP_OF_AWS_INSTANCE>
TTL:   300
```
Verify resolution: `nslookup cartmate.yourdomain.com`

---

## 3. Deploying the Application

### 3.1 Install Docker on the Server
SSH into your AWS instance and follow Docker's [official Ubuntu apt-repository installation procedure](https://docs.docker.com/engine/install/ubuntu/) for Docker Engine and the Compose plugin. Verify `docker --version` and `docker compose version` before continuing. Commands below show `docker compose` for brevity; prefix **every** one with `sudo` if the login user is not in the Docker group. Adding a user to that group grants root-equivalent control of the host. If using `sudo docker compose cp`, ensure the copied backup files are readable by the separately configured S3 uploader without making them world-readable.

### 3.2 Transfer Source & Configure Environment

First review the **private source repository** you intend to deploy; verify that it contains no `.env`, databases, backups, activation tokens, signing keys or other credentials. Do not package the entire working directory with `tar`: simple exclude patterns can miss nested secrets and local artifacts. Only after a reviewed push, clone the private repository on the server:

```bash
# Replace YOUR-ACCOUNT with the account that owns the reviewed private repo.
git clone "git@github.com:YOUR-ACCOUNT/cartmate.git" cartmate
cd cartmate
```

Once source files are in place, copy the environment template:
```bash
cp ops/env.production.example .env
```

Edit `.env` using `nano .env`:
```ini
DOMAIN=cartmate.yourdomain.com
CARTMATE_STAGING_ALLOWED_PHONES=<approved +48 test handset numbers, comma separated>
SOS_WEBHOOK_SECRET=<unique random secret, at least 16 characters>
CARTMATE_TURN_SECRET=<different unique random secret, at least 32 characters>
CARTMATE_TURN_EXTERNAL_IP=<Elastic IP>
CARTMATE_TURN_PRIVATE_IP=<instance private IPv4>
CARTMATE_MODERATOR_USER_IDS=
```

`docker-compose.yml` fixes staging, operator admission, direct-112-only SOS, console OTP with no SMS dispatch, disabled Jev, the database path and exact CORS origins. It sets `CARTMATE_DEPLOYMENT=1`, so the allowlist, webhook secret and TURN credentials must be present even for the no-SMS operator pilot. Console OTP cannot be used as a substitute for operator admission. Do not commit `.env`, activation tokens, phone numbers or backups.

### 3.3 Build and Launch Containers
```bash
docker compose config --quiet
docker compose up -d --build
```

### 3.4 Verify Deployment
* **Container Status:** `docker compose ps`
* **Caddy Logs & SSL Certificate:** `docker compose logs -f caddy`
* **TURN Listeners:** `sudo ss -lunpt | grep -E '3478|4916'` must show coturn; the firewall must allow UDP/TCP 3478 and UDP 49160-49200.
* **Initial liveness:** `curl --fail https://cartmate.yourdomain.com/api/health`. `/api/ready` should return **503 with explicit blockers** until two trusted moderators have redeemed accounts and completed witnessed adult attestations. Require **200** only for the final pilot go/no-go.

---

## 4. Operator Account Bootstrap

1. **Issue two operator activation secrets after the container has created `/app/data/pilot_live.db`:**
   ```bash
   docker compose exec -T cartmate python ../ops/pilot_invites.py --db /app/data/pilot_live.db issue-activation --for "Founder" --hours 48
   docker compose exec -T cartmate python ../ops/pilot_invites.py --db /app/data/pilot_live.db issue-activation --for "Trusted backup operator" --hours 48
   ```
   The CLI path is relative to the container's `/app/backend` working directory. Each code is shown once; deliver it privately.
2. **Redeem both accounts** in the application. Each operator retrieves their own user ID through their authenticated `/api/users/me` response. Do not promote an ordinary friend to moderator merely to make readiness green: this role can suspend and ban accounts.
3. **Configure the allowlist:** set `CARTMATE_MODERATOR_USER_IDS=usr_<founder_id>,usr_<backup_operator_id>` in `.env`, then run `docker compose up -d --force-recreate cartmate` so the service receives it.
4. **Complete witnessed 18+ checks:** each subject obtains a fresh challenge; a different allowlisted operator checks a live, original physical ID or performs the official mDowód QR verification and submits the attestation. Self-approval is prohibited. Do not collect ID numbers or images. Follow the exact workflow in [the pilot runbook](PILOT_RUNBOOK_WINDOWS.md).
5. **Require final readiness:** `curl --fail https://cartmate.yourdomain.com/api/ready` must return HTTP 200. Then run `python ops/pilot_preflight.py --base-url https://cartmate.yourdomain.com --require-ready` from a trusted machine that has the project checkout.

---

## 5. Building the Matching Android APK

Once the server is reachable at `https://cartmate.yourdomain.com`:

Run the automated build script on your development PC:
```powershell
.\scripts\build_android_apk.ps1 -BackendOrigin "https://cartmate.yourdomain.com"
```

The script will:
1. Validate the origin scheme.
2. Build the optimized React production bundle with the cloud backend configured.
3. Synchronize assets into Android (`npx cap sync android`).
4. Compile and sign the APK via Gradle wrapper.
5. Print the output path, SHA-256 checksum, and `adb install` command.

---

## 6. Offsite Backup Custody

To take a consistent online SQLite backup, copy it out of the named volume, and sync to a private encrypted S3 bucket (only after S3 access and custody are configured):
```bash
# The online backup and manifest are written inside the mounted /app/data volume.
docker compose exec -T cartmate python ../ops/cartmate_backup.py --db /app/data/pilot_live.db --out /app/data/backups --tag scheduled

# This ignored host directory is accessible only to the operator account.
install -d -m 0700 ./ops/backups
docker compose cp cartmate:/app/data/backups/. ./ops/backups/
aws s3 sync ./ops/backups/ s3://<private-bucket>/cartmate/ --sse AES256
```

The Docker volume name is installation-dependent; do not guess `/var/lib/docker/volumes/...`. Configure least-privilege S3 access, verify that both the `.db` and `.json` manifest are copied, and rehearse an offline restore before calling recovery ready. Delete neither the source database nor the last verified backup during the drill.

### 6.1 Offline Restore Rehearsal Drill

**Never aim a rehearsal restore at `/app/data/pilot_live.db`.** A `docker compose run` container mounts the same named volume as the live service; calling it "isolated" does not isolate the database. Do not reuse a drill filename or use `--confirm-offline` for a test.

1. Download or copy one `.db` backup **and its same-named `.json` manifest** from the off-host backup location into `./ops/backups/`. Verify both files exist. The app may remain running because this drill writes only to a new scratch target.
2. On a trusted machine with the CartMate checkout and Python 3, choose a **new, non-existing** scratch filename and run:
   ```bash
   # Replace these examples with the actual downloaded backup and a NEW target.
   backup_file="./ops/backups/cartmate_backup_scheduled_REPLACE_WITH_ACTUAL_NAME.db"
   drill_target="./ops/backups/restore_drill_NEW_UNIQUE_NAME.db"
   python3 ops/cartmate_restore.py --backup "$backup_file" --target "$drill_target"
   ```
   The tool checks the manifest, SHA-256, SQLite integrity and row counts. Inspect the resulting scratch database and record the drill date. A **real incident restore** of the live database requires a separately approved outage and explicit target review; it is not this rehearsal.
