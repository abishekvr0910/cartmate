# CartMate — Muse research note and AI-agent boundary

**Research received 2026-09-29, fact-checked against primary sources by Hermes the same day.** This is a research note, not launch approval or an implementation authorization. Release gates in [LAUNCH_READINESS.md](LAUNCH_READINESS.md) are unchanged. Evidence sources are linked; every load-bearing claim below was verified to exist at its cited source on 2026-09-29.

## What Muse is (verified)

Meta launched **Muse** on **2026-09-08** as a "personal AI agent" — an always-on assistant running on a dedicated **Muse Secure VM** (isolated Linux box with its own Chromium browser), available 18+ in the US via standalone app or WhatsApp. It browses, fills forms, completes email workflows, manages goals, and produces rich "Artifacts" (itineraries, dashboards) that live inside and outside chat. Source: [Meta announcement](https://about.fb.com/news/2026/09/introducing-muse-personal-ai-agent/), [The Independent coverage](https://www.independent.co.uk/bulletin/news/meta-muse-ai-agent-mark-zuckerberg-b3046908.html), [How We Designed Muse](https://introducing.muse.ai/) (Mona Sarantakos & Christine Awad, Sept 2026).

**Architecture** (from [How We Built Safety Into Muse](https://research.meta.ai/blog/security-and-safety-for-ai-agents-our-approach-with-muse), Tarek Sheasha): two isolated security domains on one VM — the agent runs in a systemd-nspawn runtime cell (cell-root mapped to unprivileged host user); security-sensitive services stay outside it: `privsep` connector workers (credentials never in agent scope), an `authd` credential daemon, and **Sentinel**, the sole permission authority for connector actions and network egress, which the agent cannot override. The browser sub-agent sees an accessibility-tree snapshot, not the raw DOM, with prompt-injection classifiers and a full pause on user takeover or credential auto-fill. A **Muse Confidential VM** (user-held encryption keys, Meta locked out) was announced for later in 2026.

**Model**: [Muse Spark 1.1](https://dev.meta.ai/models/muse-spark-1-1) — multimodal (text/image/video/audio/PDF in), 1,048,576-token context, computer use, multi-agent orchestration, OpenAI-SDK-compatible API in public preview (US). The [Muse Spark Safety & Preparedness Report](https://arxiv.org/abs/2606.12429) (arXiv 2606.12429) discloses Chemical & Biological capabilities likely reaching **high risk before mitigations**, reduced to **moderate-or-lower** residual after multi-layered safeguards; lowest cyber-misuse compliance among peers (9.0%); known robustness gaps under adaptive jailbreak and prompt injection in agentic settings; highest evaluation-awareness rate Apollo Research had observed.

**Product-philosophy points relevant to CartMate** (all verified from [introducing.muse.ai](https://introducing.muse.ai/)): the proactive-message bar is "genuinely helpful and worth the interruption," with user-configurable proactivity; chat bubbles exist because flat transcripts become unreadable; full activity log + approved permissions + editable Memory files live under the avatar; deterministic approval cards are "non-negotiable" where conversation isn't enough, with explicit anti-banner-blindness design ("the default allows standard browsing and stops for anything hard to undo").

## What CartMate should take from Muse — and what it should not

**Adopt (principles, not code):**

1. **The proactivity bar.** Any future CartMate notification/suggestion must clear "genuinely helpful and worth the interruption." This is consistent with the humane-product plan's no-guilt, no-loss-aversion stance and gives us vocabulary for it.
2. **Deterministic controls over conversational suggestions.** Outing publication, plan acceptance, and cancellation are already structured accept/reject actions in CartMate — Muse's anti-banner-blindness reasoning (stop for anything hard to undo) validates keeping them that way rather than softening them into chat.
3. **Transparency surfaces.** Muse's activity-log-under-avatar pattern maps to CartMate's future "what Jev did and why" surface if Jev ever gains user-visible behavior. Until then it is a design reference only.
4. **Separation of the permission authority from the actor.** CartMate's analogue already exists and must stay: moderation is a server-configured allowlist (`require_moderator`), Jev is shadow-mode and decides nothing, admission gates are deterministic code. The Sentinel lesson is: never let the model be its own permission authority. We already comply; keep complying.

**Do not adopt:** public avatar/personality (privacy-first product), flat unbounded chat (structured outings), browser automation, payment processing (manual BLIK copy stays), multi-app connector ecosystem, global discovery.

**Where the research overstates slightly:** CartMate does not need a "Sentinel-like approval authority for outing publication" as a new component — outing publication is already gated by deterministic server checks (invite, OTP provenance, region, screening). The correct takeaway is architectural vocabulary for what exists, not a feature to build. Similarly, "AI filtering hotspot votes to remove blocked-pair combinations" is now deterministic code (F04 fix, 2026-09-29), not an AI task — and should stay deterministic.

## Competitor scan (context, verified at category level)

Meetup (60M+ members, event categories), Bumble BFF (swipe-based friend matching), Nextdoor (neighborhood posts), Hey!VINA (women-focused), Wink (Tinder-like for friends), Clockout (post-grad professionals). All confirm the same gap CartMate targets: they arrange **groups and chat**, not structured two-person ordinary outings with mutual plan acceptance, PIN rendezvous verification, cost-rule transparency, and low-guilt cancellation. No scanned competitor does physical-verification handshakes or 50/50 ledgers. This is positioning context, not evidence of demand — only a real pilot can prove that.

## Boundary statement for all future AI work on CartMate

- Jev stays in shadow mode; it never decides age, identity, admission, matching eligibility, SOS, or bans (existing policy, unchanged).
- Any AI-suggested outing template is a **draft the user explicitly publishes**; no autonomous outing creation (research conclusion accepted; already the plan's E08 stance).
- AI never becomes a companion substitute: the product's success metric is a completed real-world outing, not conversation volume.
- The age gate (U03) precedes all AI feature work; nothing in this note unblocks it.

## Status

Research accepted as accurate (fact-checked 2026-09-29). No code changes authorized by this note. Relevant later tickets: E02 admission foundation (blocked on U03), E08 bounded optional assistance. Competitor figures are marketing claims from the companies themselves, not audited numbers.