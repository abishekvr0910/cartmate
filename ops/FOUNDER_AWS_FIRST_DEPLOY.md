# CartMate: founder's first AWS deploy (closed Silesia pilot)

**Hosting choice superseded on 2026-10-13:** the founder chose **EC2**. Use the [EC2 staging runbook](EC2_STAGING_RUNBOOK.md) for all new provisioning; this Lightsail checklist remains an alternative/historical reference only. Do not create a Lightsail instance and an EC2 instance for the same pilot by following both guides.

Status: **instructions only**. No AWS instance, domain, live SMS delivery, offsite backup, or physical-phone rehearsal has been verified by this file. This is **staging**, not a public Poland launch. The server's HTTPS address will be publicly reachable; account admission and 18+ checks still gate participation. Do not invite testers until the final gates below pass.

## The one thing to do now: create a Lightsail instance

In the [AWS Lightsail console](https://lightsail.aws.amazon.com/), choose **Create instance**:

| Console choice | Set it to |
| --- | --- |
| Region | **Europe (Frankfurt), eu-central-1** |
| Platform / blueprint | **Linux/Unix → OS Only → Ubuntu 24.04 LTS** |
| Plan | **Public IPv4, 2 GB RAM / 2 vCPUs / 60 GB SSD** (AWS listed **USD 12/month** on 2026-10-13; confirm today's console price) |
| Name | `cartmate-silesia-staging` |

The 2 GB plan is a practical starting recommendation for the Docker/React build, **not** a measured capacity guarantee. Domain, S3 and snapshots can cost extra. A budget alert warns you; it does **not** cap spending. Stopping a Lightsail instance does not stop its instance charge. See [AWS bundle prices](https://docs.aws.amazon.com/lightsail/latest/userguide/amazon-lightsail-bundles.html), [billing FAQ](https://docs.aws.amazon.com/en_en/lightsail/latest/userguide/amazon-lightsail-frequently-asked-questions-faq-billing-and-account-management.html), and [AWS Budgets](https://docs.aws.amazon.com/cost-management/latest/userguide/budgets-managing-costs.html).

After creation, in **Networking**, [create and attach a static IPv4 address](https://docs.aws.amazon.com/lightsail/latest/userguide/lightsail-create-static-ip.html). Allow inbound TCP **80 and 443**; keep **8000 closed**. Keep SSH **22** for administration only, restricted to your own IP where practical. Use the Lightsail browser SSH console if you have not set up local SSH. Do not put passwords, API keys or phone numbers in the instance launch script.

Set a small AWS budget alert and enable MFA on the AWS account before doing further work. A budget alert is only a notification. Record the static public IP and the domain/subdomain you intend to use, such as `staging.yourdomain.pl`. Send **only those two non-secret values** back to Codex. Do **not** send AWS credentials, card details, private keys, activation codes, ID images or your `.env` file.

If you do not own a domain yet, stop after creating the instance and static IP. CartMate's current Caddy and Android setup needs a domain that resolves to this server for valid HTTPS. Do not substitute an HTTP IP address or send the existing APK to your friend.

## What must be ready before deploying source

1. Point the domain's **A record** to the attached static IPv4 address and verify it resolves. You can use your registrar's DNS; a Lightsail DNS zone is optional. See [AWS DNS guidance](https://docs.aws.amazon.com/lightsail/latest/userguide/understanding-dns-in-amazon-lightsail.html).
2. Prepare a **private, reviewed source repository** containing the exact commit to deploy. Review staged and untracked files; exclude `.env`, databases, backups, activation/recovery codes, local signing keys and build artifacts before the first commit/push. Do not archive and upload the entire work directory. This is an engineering handoff step Codex can help complete once you provide the IP and domain; it does not require your AWS password.
3. Choose **two genuinely trusted adult operators** for witnessed age checks. A moderator can inspect reports and suspend or ban accounts; do not give that role to an ordinary participant just to turn readiness green. Confirm the time window during which a human can respond to incidents. No unattended 24/7 coverage has been demonstrated.

## Server deployment, once the private repository and domain exist

Connect by the Lightsail **Connect using SSH** button. On Ubuntu, follow [Docker's official apt-repository instructions](https://docs.docker.com/engine/install/ubuntu/) to install Docker Engine and the Compose plugin. Verify:

```bash
docker --version
docker compose version
```

The commands below use `sudo docker compose` so the login user need not join the root-equivalent `docker` group. Configure a read-only Git SSH key or another secure repository access method; do not embed a personal access token in a URL or shell history.

```bash
# Replace YOUR-ACCOUNT after a reviewed private repository exists.
git clone "git@github.com:YOUR-ACCOUNT/cartmate.git" cartmate
cd cartmate
cp ops/env.production.example .env
chmod 600 .env
nano .env
```

Set `DOMAIN` to the real **hostname only** (no `https://`), `CARTMATE_STAGING_ALLOWED_PHONES` to the private comma-separated `+48...` test-handset allowlist, and `SOS_WEBHOOK_SECRET` to a fresh random value of at least 16 characters (`openssl rand -hex 32` can generate one locally). Leave `CARTMATE_MODERATOR_USER_IDS=` blank until both operator accounts exist. Keep `CARTMATE_ENV=staging`, `CARTMATE_DEPLOYMENT=1`, operator admission and manual age pilot enabled, `SOS_PROVIDER=disabled`, `OTP_PROVIDER=console`, and `JEV_MODE=disabled` as in the template/Compose file. **The staging deployment guard requires a phone allowlist even though operator admission sends no SMS.** Do not put the secret or numbers in Git, chat or screenshots. The current Compose file also requires `CARTMATE_TURN_SECRET`, `CARTMATE_TURN_EXTERNAL_IP`, and `CARTMATE_TURN_PRIVATE_IP` for the coturn relay; use the EC2 runbook's TURN setup and open UDP/TCP 3478 plus UDP 49160-49200.

```bash
sudo docker compose config --quiet
sudo docker compose up -d --build
sudo docker compose ps
curl --fail "https://<YOUR_DOMAIN>/api/health"
```

Caddy obtains HTTPS certificates when DNS points to this server and ports 80/443 are reachable. If health fails, inspect `sudo docker compose logs --tail=100 cartmate caddy` without posting raw logs that may contain private data. `/api/ready` may correctly return **503** before operator bootstrap; do not treat `/api/health` 200 as launch approval. See the detailed [AWS runbook](AWS_DEPLOYMENT_RUNBOOK.md) for the operator activation, moderator allowlist and witnessed 18+ sequence. No `docker compose down -v` or volume deletion belongs in a routine deploy.

## Final release gates before sending a link or APK

1. Two trusted operators redeem single-use codes. Configure their exact IDs in `CARTMATE_MODERATOR_USER_IDS`, recreate the app container, and perform witnessed adult attestations. No self-attestation. Use the [pilot procedure](PILOT_RUNBOOK_WINDOWS.md); do not photograph or retain identity documents.
2. Require `/api/ready` to return **200** and run `python3 ops/pilot_preflight.py --base-url "https://<YOUR_DOMAIN>" --require-ready` from a trusted checkout. Direct-112 fallback stays enabled; commercial SOS SMS stays disabled. The app is **not an emergency service**.
3. Configure an encrypted, access-controlled **off-host** backup destination. Take a SQLite online backup and its manifest, retrieve both from off-host storage, and restore to a **new scratch file**, never the live database. Use [the corrected backup/restore drill](AWS_DEPLOYMENT_RUNBOOK.md#61-offline-restore-rehearsal-drill). Merely creating an S3 bucket or backup script is not proof of recovery.
4. Build a **new domain-bound** Android APK from the Windows development machine only after the HTTPS URL works: `.\scripts\build_android_apk.ps1 -BackendOrigin "https://<YOUR_DOMAIN>"`. The existing local APK targets a previous backend and must **not** be distributed. Record the new file's SHA-256 and test the exact installed artifact. The HTTPS website can be tested on phones first; an APK is optional for the initial two-person rehearsal.
5. On **two physical phones**, confirm live join/chat, mutual plan acceptance, cancellation propagation, reconnect after restart, zoom/screen reader, direct 112 fallback UI, and that the app does not claim an SMS alert was delivered. Do not actually place an emergency call. Record H-01–H-06 outcomes and obtain an explicit founder go/no-go before inviting anyone.

Current handoff: the code has automated-test evidence, but **no AWS instance or real-device rehearsal is verified**. Your immediate handoff is the static public IP and intended domain; Codex can then review the private-source package and walk through the deployment and safety checks without receiving your AWS credentials.
