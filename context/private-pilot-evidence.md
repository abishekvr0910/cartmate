# Private two-person website pilot evidence

**Current independent evidence (2026-10-13):** [Codex verification](../qa/CODEX_MR2_VERIFICATION.md) passed 158 backend/DR, 12 preflight, 16 operator browser cases, eight existing probes and build/lint. Fresh offline dependency-install/RT-17 rehearsal passes. Original MR2-01/02 failures closed in the tested runtime; **MR3-01 P3** parser-unavailable fallback cleanup remains. No APK or human approval. Existing DB start/end hash matches the latest handback and remains unchanged this retest; earlier differences remain unexplained, not a finding of corruption.

Status: **Independent retest complete with one low-priority hardening follow-up; human and physical-network gates unverified; no real-user link approved.** See [results matrix](../qa/PRIVATE_PILOT_REVIEW_RESULTS.md). Record only redacted facts. Do not include names, phone numbers, email addresses, document details, secrets, invitation codes, session tokens, location trails or screenshots of ID documents.

| Gate | Evidence to record | Result |
| --- | --- | --- |
| No-paid operator admission and production hard-off | Commit, negative/positive/replay/revocation/restart tests | Current local suites pass: 158 backend/DR, 12 preflight, 16 operator browser, eight existing probes. Original MR2 failures closed; MR3-01 P3 open; no hosted result |
| Two distinct adult operator checks, consent and appeal | Reviewed procedure, named custodians recorded privately | Open |
| Private HTTPS reachability | Actual phone models, private URL class, tailnet access denial for nonmember, host loopback binding | Open |
| Same-origin API and WebSocket | Origin/ticket denial and live two-phone chat/check-in/cancel result | Open |
| Local durable database and off-device recovery | Online backup checksum, protected off-device copy, offline full-schema restore and time | Open |
| Security and WCAG 2.2 review | Independent reviewer, date, findings, fixes and residual risk | Open |
| Observed human usability | Two consenting adults, tasks, confusion points, fixes; no identifying content | Open |
| Staffed pilot operation | Test hours, available moderator/backup, incident stop and 112 disclaimer | Open |
| Founder go/no-go | Explicit final approval after all preceding evidence, not a test-count inference | Open |

If any mandatory row remains open, the app may be shown only as a clearly labeled non-live preview, not as a real meetup service.
