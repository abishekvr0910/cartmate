# CartMate on EC2: step-by-step closed Silesia pilot

**Decision (2026-10-13):** The founder chose **Amazon EC2** instead of Lightsail for the first hosted rehearsal. This guide supersedes the Lightsail-first checklist. It is a plan and operator procedure, **not evidence that an EC2 instance or a working app exists**. Do not invite testers merely because the site responds to `/api/health`. CartMate remains a single-worker, SQLite-backed staging service for a small, supervised adult cohort—not a highly available Poland-wide launch.

The minimal architecture is one x86 Ubuntu 24.04 EC2 instance with an encrypted gp3 EBS root volume, the existing Docker Compose app plus Caddy, one Elastic IP and one HTTPS domain. The Docker `cartmate-data` volume lives on that EBS disk. There is **no load balancer, RDS, NAT gateway, SMS provider or multi-instance cluster** in this pilot. If you need more than one app server later, first redesign SQLite persistence and the in-process WebSocket fan-out.

## Phase 1 — founder actions in the AWS console

1. **Check cost before creating resources.** Use the [AWS Pricing Calculator](https://calculator.aws/) for **Europe (Frankfurt), eu-central-1**. Include EC2 compute, 30 GiB gp3 EBS, one public IPv4/Elastic IP, outgoing traffic, optional snapshots and S3 backup storage. EC2 does not have Lightsail's all-in-one price; a public IPv4 is separately billed at the [current AWS rate](https://aws.amazon.com/vpc/pricing/). Create an [AWS Budget alert](https://docs.aws.amazon.com/cost-management/latest/userguide/budgets-managing-costs.html); it is **not** a hard spending cap. Enable MFA on the AWS account. Do not assume a free-tier discount.
2. Open **EC2 → Instances → Launch instances** in **eu-central-1**. Choose:

   | Setting | Choose |
   | --- | --- |
   | Name | `cartmate-silesia-staging` |
   | AMI | Official **Ubuntu Server 24.04 LTS, 64-bit x86** |
   | Instance type | **t3.medium** (2 vCPU, 4 GiB RAM) for Docker build headroom; review the displayed price. A smaller machine is possible only after measuring the build and runtime. |
   | Key pair | Create a new SSH key pair; download the `.pem` once and store it privately. Never send it to an assistant or put it in Git. |
   | VPC / subnet | Default VPC and a **public subnet** with internet-gateway access. If no default VPC exists, stop and review networking before launching. Do not create a NAT gateway for this one-server pilot. |
   | Security group | New group: TCP **22** from **your current public IP only**; TCP **80** and **443** from the internet for HTTPS issuance/traffic. **No inbound 8000 or database port.** Prefer IPv4-only initially; review any IPv6 rules separately. |
   | Storage | **30 GiB gp3 EBS root**, encrypted. In advanced storage settings choose **Delete on termination: No** and verify it after launch. This prevents accidental instance termination from automatically deleting the SQLite volume, but the retained volume still costs money. |
   | Advanced details | Enable **termination protection**. Leave user-data empty: it must not contain passwords, tokens, phone numbers or application secrets. |

   AWS documents the [EC2 launch wizard](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/tutorial-launch-a-test-ec2-instance.html), [t3.medium capacity](https://aws.amazon.com/ec2/instance-types/general-purpose/), [restricted SSH rules](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/changing-security-group.html), and [root-volume retention](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/configure-root-volume-delete-on-termination.html). T3 is burstable: sustained CPU in Unlimited mode can add credit charges. Inspect the CPU-credit setting and monitor it during builds.
3. After launch, verify **Instance state: Running**, record the **instance ID**, and confirm in **Storage → Block devices** that the root EBS volume is encrypted and **Delete on termination: No**. Do not terminate the instance to test this.
4. In **EC2 → Network & Security → Elastic IPs**, allocate one address in the **same region** and associate it with this instance. Record the address. Elastic IPs are billed even when idle; release an unused address deliberately only after DNS/rollback review. [AWS Elastic IP steps](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/working-with-eips.html)
5. Point an **A record** for a domain you control—for example, `staging.yourdomain.pl`—to the Elastic IP. This can be done at your registrar; Route 53 is optional. Wait until `nslookup staging.yourdomain.pl` returns that IP. **If you do not yet have a domain, stop here.** Do not replace HTTPS with a bare HTTP IP or distribute the old APK.

**Send Codex only:** instance ID, Elastic IP, intended hostname, and whether the domain resolves. These are non-secret. **Never send:** AWS login, access keys, private SSH key, `.env`, activation codes, real phone list or identity documents.

## Phase 2 — clean source and server setup

6. **Engineering source gate:** the local CartMate worktree currently has **no Git commit or remote**. A reviewed **private** repository must be committed/pushed before the next `git clone`. Review staged and untracked files and exclude `.env`, databases, backup archives, activation/recovery tokens, signing keys, local Android build outputs and `CODEX_WORK_DIRECTORY.md`. A GitHub source URL is not a deployed application. Do not upload a tarball of the whole worktree as a shortcut.
7. Connect to Ubuntu with the private key (from your Windows PC, substitute your real paths and IP):

   ```powershell
   ssh -i "C:\path\to\cartmate-staging.pem" ubuntu@YOUR_ELASTIC_IP
   ```

   Keep SSH port 22 scoped to your current IP. If access fails, inspect the instance state, public subnet route, Elastic IP association and security-group rule; do not open SSH to everyone just to get in.
8. On the server, apply Ubuntu security updates and install **Docker Engine plus the Compose plugin** using [Docker's official Ubuntu apt-repository procedure](https://docs.docker.com/engine/install/ubuntu/). Verify `docker --version` and `docker compose version`. The commands below use `sudo docker compose`; do not add the account to the root-equivalent Docker group merely for convenience.
9. Only after a clean private repository and read-only Git access from EC2 are prepared:

   ```bash
   # Replace YOUR-ACCOUNT with the owner of the reviewed private repo.
   git clone "git@github.com:YOUR-ACCOUNT/cartmate.git" cartmate
   cd cartmate
   cp ops/env.production.example .env
   chmod 600 .env
   nano .env
   ```

   Set `DOMAIN` to the exact hostname **without** `https://`. Set `CARTMATE_STAGING_ALLOWED_PHONES` to the private allowlist of approved Polish `+48` handsets, and `SOS_WEBHOOK_SECRET` to a fresh value of at least 16 characters (`openssl rand -hex 32` can generate one on the server). Leave `CARTMATE_MODERATOR_USER_IDS=` empty until operator accounts exist. Keep the deployed staging safeguards from `docker-compose.yml`: operator admission/manual age gate enabled, `SOS_PROVIDER=disabled`, `OTP_PROVIDER=console`, `JEV_MODE=disabled`, one worker and `/app/data/pilot_live.db`. The deployed-staging guard requires a nonempty phone allowlist **even though operator admission sends no SMS**. Do not commit `.env` or post its contents.
10. Validate the Compose file and launch the existing app/Caddy pair:

   ```bash
   sudo docker compose config --quiet
   sudo docker compose up -d --build
   sudo docker compose ps
   curl -fsS "https://YOUR_DOMAIN/api/health"
   ```

   Caddy needs correct DNS and reachable ports 80/443 to obtain HTTPS. If TLS or health fails, inspect `sudo docker compose logs --tail=100 caddy cartmate` privately; logs may contain sensitive data. The app's internal port 8000 must **not** be added to the EC2 security group. `/api/ready` can correctly return **503** until the human operator setup is complete. Never use `docker compose down -v` during a routine deploy.

## Phase 3 — admission, backup and actual acceptance

11. Issue two single-use activation codes from the running app container, redeem both privately, then add the **exact two trusted operator user IDs** to `CARTMATE_MODERATOR_USER_IDS` in `.env` and recreate only the app container:

   ```bash
   sudo docker compose exec -T cartmate python ../ops/pilot_invites.py --db /app/data/pilot_live.db issue-activation --for "Founder" --hours 48
   sudo docker compose exec -T cartmate python ../ops/pilot_invites.py --db /app/data/pilot_live.db issue-activation --for "Trusted backup operator" --hours 48
   # After editing .env with the exact IDs:
   sudo docker compose up -d --force-recreate cartmate
   ```

   Codes are printed once; do not paste them into chat, logs or Git. Moderators have powerful report/suspension privileges—**do not make an ordinary friend a moderator just to pass readiness**. A separate trusted operator must witness each adult check; nobody can approve their own age. Follow [the existing pilot procedure](PILOT_RUNBOOK_WINDOWS.md) for accepted physical-ID or live mDowód-QR methods. Do not retain ID numbers or photos.
12. Verify readiness and the app's security contract from a trusted checkout:

   ```bash
   curl -fsS "https://YOUR_DOMAIN/api/ready"
   python3 ops/pilot_preflight.py --base-url "https://YOUR_DOMAIN" --require-ready
   ```

   Both must succeed before inviting anyone. `/api/health` alone proves only liveness. Operator admission is not an SMS/identity-provider verification, and SOS remains a direct `tel:112` voice fallback—not an emergency dispatch service.
13. Before any real-user session, create a **private S3 backup bucket** with Block Public Access and encryption on, and give this EC2 instance a **least-privilege IAM role** limited to that bucket/prefix. Do not store long-lived AWS access keys on the server. Run CartMate's online SQLite backup, copy both the `.db` **and adjacent `.json` manifest** out of the Docker volume, upload them off-instance, download them again, and rehearse restore into a **new scratch database**, never `/app/data/pilot_live.db`. Follow [the safe backup/restore drill](AWS_DEPLOYMENT_RUNBOOK.md#6-offsite-backup-custody). S3 setup and successful recovery are **not yet verified**. [AWS EC2 role guidance](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/iam-roles-for-amazon-ec2.html), [S3 private-bucket guidance](https://docs.aws.amazon.com/AmazonS3/latest/userguide/security-best-practices.html)
14. Test the HTTPS website on **two physical phones** first. For Android packaging, after the live domain works, build a **new domain-bound APK** on the development PC:

   ```powershell
   .\scripts\build_android_apk.ps1 -BackendOrigin "https://YOUR_DOMAIN"
   ```

   Record the fresh APK checksum and test that exact installed file. The existing local APK points at a previous backend; **do not send it to friends**. iPhone testing uses the HTTPS website until a separate iOS build exists.
15. Perform and record the H-01–H-06 physical/human checks: two-device HTTPS/WebSocket flow, witnessed adult verification, join/plan/chat/PIN/cancellation/reconnect, off-instance restore proof, real screen-reader and zoom checks, staffed incident-response window, and explicit founder go/no-go. Never actually call 112 during a test. Stop invitations if a safety or authorization check fails.

## EC2-specific stop conditions and operational limits

- One EC2 server is a **single point of failure**. EBS persists across a normal stop/start, but availability is not guaranteed and retained volumes still incur charges. If instance termination occurs, the root volume survives only if its `Delete on termination` setting was correctly set to **No**; the off-instance backup is the independent recovery path. [AWS EBS lifecycle](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/preserving-volumes-on-termination.html)
- An Elastic IP preserves the public address across stop/start, but an unassociated or in-use address can still incur a charge. Confirm the budget and delete unused resources deliberately; do not infer that stopping EC2 ends the entire bill. [AWS IPv4 pricing](https://aws.amazon.com/vpc/pricing/)
- Do not add a second EC2 app instance or an Auto Scaling Group to the current SQLite/in-process-WebSocket architecture. Extra infrastructure would not make current state consistent across instances.
- No AWS console action, Docker boot, DNS/TLS check, S3 restore, domain-bound APK or physical H-01–H-06 check has been completed by this document. Keep the pilot closed until their actual results are recorded.
