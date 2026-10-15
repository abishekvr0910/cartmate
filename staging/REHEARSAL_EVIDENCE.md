# Hosted staging evidence record

**PARKED PAID-PATH RECORD (2026-10-01):** This table is for a later Render/carrier rehearsal, not the active no-cost friend test. Record private local-web evidence in `../context/private-pilot-evidence.md`; do not mark these rows complete because a local test passes.

The staging-only, operator-witnessed age-attestation route is now implemented and locally tested, but it is disabled by default. This row remains open until a real operator process is reviewed and the final hosted negative/positive/revocation paths are witnessed. It is not a connected mObywatel API.

**Unfilled: no Render account, host, carrier handset, offsite destination or age provider is connected in this checkout.** The approved live service remains closed. Use `staging/README.md`, `staging/preflight.py`, `staging/otp_rehearsal.py`, `ops/RUNBOOK.md` and `LAUNCH_READINESS.md` for procedures. Never paste credentials, OTPs, phone numbers or identity material into this file.

Start with the concise [`HOSTING_HANDOFF.md`](HOSTING_HANDOFF.md) for the difference between hosting closed staging and approving live invitations. The latest 2026-09-30 local rerun passed 129/129 backend tests, frontend build/lint, 40/40 development browser tests, 4/4 no-demo browser tests and the local recovery drill. It did not fill any hosted, carrier, offsite, independent-review or human-session row below.

| Gate | Timestamp, operator and candidate commit | Evidence (redacted) | Result |
| --- | --- | --- | --- |
| Private Git and hosted CI/image build | — | — | Open |
| Render Frankfurt HTTPS/WSS, clean persistent disk, restart | — | — | Open |
| Deployed age-provider negative/positive paths | — | — | Open; no provider chosen |
| Eligible carrier one-handset OTP, replay, outage and spend cap | — | — | Open |
| Positive authorized WSS and denied Origin/ticket | — | — | Open |
| Direct-112-only SOS and report/moderator incident drill | — | — | Open |
| Encrypted, restricted offsite backup + offline full-schema restore | — | — | Open |
| Measured recovery/rollback and revocation-after-restore check | — | — | Open |
| Independent security, accessibility, privacy and human usability reviews | — | — | Open |

Render's persistent disk preserves only its mounted path and has provider snapshots, but its own documentation warns that snapshot restore can lose later changes. Do not count those snapshots as this application's tested encrypted offsite backup. See [Render persistent disks](https://render.com/docs/disks).
