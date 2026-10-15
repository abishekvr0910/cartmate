# CartMate pre-pilot review handoff — 2026-09-30

**This is an engineering self-review and a brief for independent reviewers, not an independent security or WCAG conformance certificate.** Do not invite real participants while `LAUNCH_READINESS.md` has open release gates. A reviewer who did not implement the feature must record their own findings and sign-off.

## Evidence verified locally

- Backend: 127/127 pytest cases on a disposable database, including explicit group joining/leaving, sender-bound group-message reporting, rollback on injected group write failure, deployed WebSocket Origin denial and oversized-frame rejection.
- Browser: 40/40 local desktop/mobile Chromium cases with a WebSocket-capable backend; 4/4 isolated no-demo built-bundle cases. Narrow (320px) spot/group dialogs have accessible names, labeled inputs, keyboard focus containment and Escape/focus restoration.
- Recovery: 3/3 local drills, including an offline restore of every table from a disposable real-schema database with report/group context. This does **not** test encryption, offsite upload, a hosted volume, or measured recovery time.
- Frontend: TypeScript/build and lint pass. Vite still warns about the large app and MapLibre chunks.

## Security review target

The independent reviewer should exercise the real deployed configuration (not demo tokens or `qa/staging_harness.py`) and record HTTP/WSS evidence for outsider, blocked, suspended, revoked-session, missing/expired/revoked age proof, out-of-region, former group member and moderator/non-moderator roles. Include concurrent join/vote/leave/report retries and forced database-write failures. Confirm that a vote never grants room membership, an explicit leave revokes existing room subscriptions, and report evidence must be authored by the reported member.

High-priority unresolved items: the web bearer credential is still readable from `localStorage`; browser session-cookie/CSRF/rotation work in E04 is unfinished. Existing WebSocket connections recheck session/adult status at most every 30 seconds while idle; expiry is not a synchronous push revocation. Group chat history is not paginated and group closure/expiry are not implemented. No approved age provider is trusted. An independent reviewer must decide whether these issues require fixes before a controlled pilot and test the final candidate, not this note. Use the [OWASP WebSocket Security Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/WebSocket_Security_Cheat_Sheet.html) for handshake, authorization and resource-limit probes.

## Accessibility review target

Evaluate the public/pending screen, OTP/register, discovery, outing request, plan acceptance, cancel, report, block, group vote/join/chat/leave, SOS guidance, profile and moderation. Use WCAG 2.2 AA as the review target; test keyboard-only operation, visible and unobscured focus, dialog name/focus/return, error announcements, zoom/reflow at 200% and 400%, text spacing, contrast, reduced motion and 320px/short-landscape layouts. Perform a manual screen-reader pass with Polish content, then check the English/UK/RU paths for untranslated controls. Test at least one real phone with its virtual keyboard. Record criterion, screen, device/AT version, steps, observed result and issue ID. Automated Playwright checks are evidence for a few behaviors only; W3C states that no tool alone establishes conformance. See [WCAG 2.2](https://www.w3.org/TR/WCAG22/) and [W3C evaluation guidance](https://www.w3.org/WAI/test-evaluate/).

## Sign-off record (unfilled)

| Area | Reviewer and date | Evidence link/ID | Result and remaining severity |
| --- | --- | --- | --- |
| Independent authorization/security | — | — | Open |
| Manual WCAG 2.2/assistive technology | — | — | Open |
| Privacy/age-assurance method | — | — | Open |
| Hosted operations and recovery | — | — | Open |
| Founder/safety-lead pilot approval | — | — | Open |
