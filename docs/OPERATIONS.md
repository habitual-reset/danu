# DANU — Operations Log

Living document for status, security hardening, and backup practices. Update as the project evolves.

**Last updated:** June 28, 2026

---

## Current status

| Area | Status |
|------|--------|
| Voice (510 number) | Working E2E with mock LLM |
| SMS (510 number) | A2P 10DLC campaign **submitted**, pending approval |
| Memory system | Event-sourced store + retrieval in place |
| LLM | Mock only — real provider not wired |
| GitHub | `habitual-reset/danu` — **pushed**, currently **public** |
| Local secrets | `~/danu/.env` only (gitignored) |

---

## Security & sustainability backlog

Items surfaced during SMS/Twilio unblock work. Priority order.

### High (do soon)

- [ ] **Rotate Twilio Auth Token** if it was ever pasted in chat; update `.env` only
- [x] **Implement STOP / HELP / START** SMS handlers (required by campaign + carrier compliance)
- [ ] **Stable public URL for compliance docs** before making repo private (see below)
- [ ] **Replace ephemeral Cloudflare tunnel URL** with ngrok authtoken or named Cloudflare tunnel for dev
- [ ] **Never commit `.env`** — verify before each push (`git status`, `.gitignore`)

### Medium (before consumer-facing)

- [ ] **Per-tenant LLM keys (BYOK)** — encrypted in DB, not env vars
- [ ] **Rate limiting** on webhooks (per phone number)
- [x] **Hangup → memory consolidation** for voice calls (status callback)
- [ ] **Audit log review** — ensure tool calls and memory commits are traceable
- [ ] **HTTPS only** in production (no tunnel in prod; deploy to Fly/Railway/etc.)

### Lower (scale later)

- [ ] Postgres migration path (designed, not deployed)
- [ ] Multi-user admin / tenant onboarding
- [ ] 10DLC for production multi-user SMS volume
- [ ] Secret manager (not flat `.env`) in cloud deploy

---

## GitHub backup strategy

### What we have now

- Manual push works (`git push origin main`)
- Helper: `scripts/push-to-github.sh`
- Repo is **public** (needed for Twilio to read policy URLs)

### Recommended workflow

After meaningful work:

```bash
~/danu/scripts/backup.sh
```

Or with a commit message:

```bash
~/danu/scripts/backup.sh "Wire OpenAI LLM adapter"
```

### Making the repo private again

**Tradeoff:** If the repo goes private, Twilio policy links (`github.com/.../PRIVACY.md`) **stop working** unless you:

1. Host policies on a **stable public URL** (e.g. `habitualreset.com/danu/privacy`), or
2. Use **GitHub Pages** (public site from docs; private repo needs GitHub Pro for private Pages), or
3. Keep compliance files in a **small public repo** (e.g. `habitual-reset/danu-policies`) and code in private `danu`

**Suggested path:** After A2P approval, create `habitual-reset/danu-policies` (public, only COMPLIANCE/PRIVACY/TERMS) and make `danu` **private**.

### Automatic backup (optional)

Cron example (daily, only if changes):

```bash
0 22 * * * /Users/mattkosko/danu/scripts/backup.sh "nightly backup" >> /Users/mattkosko/danu/data/backup.log 2>&1
```

---

## Twilio / SMS checklist (in progress)

- [x] Compliance docs (PRIVACY, TERMS, COMPLIANCE)
- [x] GitHub links live for Trust Hub
- [x] Campaign opt-in keywords + message submitted
- [ ] Campaign **approved**
- [x] STOP/HELP/START handlers in code
- [ ] Test SMS E2E after approval
- [ ] Update Twilio webhook if tunnel URL changes

---

## Architecture reminders (scale-minded)

- `tenant_id` / `user_id` on all tables — ready for multi-user
- LLM behind `danu/agent/llm.py` adapter — swap providers without channel changes
- Memory: persist before think; two-phase memory commits
- Channels normalize to `MessageEnvelope` — voice and SMS share orchestrator