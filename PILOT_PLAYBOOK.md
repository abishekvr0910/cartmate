# CartMate — Closed Silesia Friend Pilot Playbook

**Scope update, 2026-10-12:** The initial real-world evaluation is a **supervised, two-adult friend test in Katowice (Silesia)** running on the founder's local computer over a secure private network (Tailscale Serve), using operator admission (`CMACT-...`) and witnessed 18+ attestation (`physical_identity_document` / `mdowod_qr`). Paid Render hosting and carrier SMS are paused. Read `GEMINI_HANDOFF.md`, `ops/PILOT_RUNBOOK_WINDOWS.md`, and feature spec 001 for engineering prerequisites.

**Status:** Rehearsal plan, not authorization to recruit or launch publicly. The release gates in [LAUNCH_READINESS.md](LAUNCH_READINESS.md) take precedence. Real participant outcomes remain blank until observed.

---

## 1. The Experiment

CartMate must evaluate whether two real adults can comfortably coordinate a short, ordinary outing in a public place, understand the safety boundaries, and find the experience valuable. Test counts and simulated personas do not prove human usefulness.

### 1.1 Core Boundaries
- **Cohort Size:** Exactly two consenting adults (the founder and a trusted adult friend). No bulk outreach, company rosters, or student recruitment.
- **Venue:** Well-lit, accessible public location in Katowice (e.g. Silesia City Center, Galeria Katowicka). No private residences or unmonitored spaces.
- **Timing:** Pre-scheduled, staffed operational window (e.g. 2 hours on a Saturday afternoon). Host machine powered on with sleep disabled.
- **Truthful Identity & Age Rules:** Operator admission tokens (`CMACT-...`) grant access to the staging service without SMS, but do **not** certify adulthood or identity. Adult status requires separate witnessed in-person verification by a second authorized adult; **no one may approve their own account**.
- **Safety Invariant:** SOS is direct voice `tel:112`. CartMate does not monitor meetings or dispatch responders.

---

## 2. Participant Journey & Observation Protocol

### 2.1 Step-by-Step Flow
1. **In-Person Token Handover:** Operator delivers a single-use `CMACT-...` admission token to the participant in person.
2. **Account Activation:** Participant opens the private HTTPS URL on their phone, navigates to "🔑 Aktywuj", enters token, name, and city.
3. **Witnessed 18+ Attestation:**
   - Participant generates a 5-minute challenge code.
   - Operator visually inspects original physical ID (`physical_identity_document`) or scans live mObywatel QR (`mdowod_qr`).
   - Operator submits attestation via Operator Console or API.
   - Friend attests Operator Jan using mutual moderator token (no self-approval).
4. **Outing Discovery & Coordination:**
   - Host publishes outing with clear activity, meeting time, expected duration, and cost terms (e.g. 50/50 split).
   - Companion browses radar, submits join request.
   - Host reviews and accepts. Both enter Active Trip HUD.
5. **Rendezvous & Handshake:**
   - Meet at agreed public entrance.
   - Host shares 4-digit PIN; Companion enters PIN to confirm mutual presence.
6. **Cost Settlement & Completion / Cancellation:**
   - Log shared expense (e.g. 40.00 zł total, 20.00 zł net settlement).
   - Test low-guilt cancellation or mutual completion with follow-up ratings.

---

## 3. Minimal Human Observation Sheet (Unfilled)

*To be recorded during the actual friend trial by an observer without coaching.*

| Metric / Question | Value / Denominator | Notes & Direct Observations |
| :--- | :---: | :--- |
| **Token activation unaided** | — / 2 | Observed friction, input confusion, error messages |
| **18+ challenge generation unaided** | — / 2 | Understanding of why live features were locked |
| **Plan terms understood before acceptance** | — / 2 | Understood time, venue, 50/50 cost sharing rule |
| **PIN handshake completed smoothly** | — / 2 | Time to verify 4-digit rendezvous PIN |
| **Low-guilt cancellation reassuring** | — / 2 | Did participant feel pressured, judged, or penalized? |
| **Emergency limits understood** | — / 2 | Understood that SOS dials 112 directly, not app dispatch |
| **Actual physical outing completed?** | [ ] Yes  [ ] No | Factual confirmation of public meetup |
| **Willingness to repeat?** | — / 2 | Voluntary answer to: "Would you use this for a real errand?" |

---

## 4. Operational Roles

| Role | Responsibilities | Assigned Human |
| :--- | :--- | :--- |
| **Host / Operator** | Runs local backend on Windows PC, maintains Tailscale connection, issues `CMACT-...` tokens, captures database backups before/after test. | Founder |
| **Backup Operator** | Inspects original physical ID of Founder to witness 18+ check (satisfies no-self-approval rule), assists with incident stop. | Trusted Peer / Co-tester |
| **Participant Friend** | Consenting adult friend testing the user experience on physical handset. | Friend |
| **Safety Lead** | Monitors staffed hours, enforces immediate stop conditions, executes emergency Tailscale severing if needed. | Founder |

---

## 5. Stop Conditions (Immediate Halt)
1. Any connection from an unauthorized device outside the private tailnet.
2. Any exposure of personal data, tokens, or private chat to unauthorized parties.
3. Software crash or data corruption requiring restore drill.
4. Participant distress or discomfort at any point.

---

## 6. Draft Polish Invitation for Consenting Friend

> Cześć! Testujemy wczesny, prywatny prototyp CartMate — aplikacji, która pomaga umówić się na zwykłe, codzienne wyjście (np. zakupy w Silesia City Center) w bezpiecznym, publicznym miejscu.
> 
> Udział jest całkowicie dobrowolny. Prototyp działa na moim własnym komputerze przez bezpieczną sieć prywatną. Przed dołączeniem sprawdzamy pełnoletność (wgląd do dokumentu tożsamości w cztery oczy, bez robienia zdjęć i bez zapisywania danych dokumentu).
> 
> W aplikacji obie osoby z góry uzgadniają plan, czas i podział kosztów (np. 50/50). W każdej chwili można zrezygnować bez żadnych konsekwencji. Aplikacja nie śledzi lokalizacji w tle i nie wzywa służb (przycisk SOS łączy bezpośrednio z numerem 112).
> 
> Jeśli masz ochotę przetestować ze mną aplikację na żywo przez 30 minut, dam Ci jednorazowy kod aktywacyjny `CMACT-...`.

*(Do not distribute until all automated engineering gates pass and preflight reports ready).*
