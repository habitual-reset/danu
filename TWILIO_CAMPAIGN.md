# Twilio A2P 10DLC — Copy-Paste Reference

Use these values in **Twilio Trust Hub → Messaging → Campaigns** (or Customer Profile / Brand registration flow).

> **Important:** Twilio must be able to open your policy links in a browser. If the GitHub repo is **private**, either make the repo public or host these files on a public URL (e.g. GitHub Pages, your domain).

**Repository:** `github.com/habitual-reset/DANU`

---

## Links for Twilio form

Replace `main` with your default branch if different.

| Field | URL |
|-------|-----|
| **Embedded link / Program website** | `https://github.com/habitual-reset/DANU/blob/main/COMPLIANCE.md` |
| **Privacy Policy** | `https://github.com/habitual-reset/DANU/blob/main/PRIVACY.md` |
| **Terms and Conditions** | `https://github.com/habitual-reset/DANU/blob/main/TERMS.md` |

Alternate raw URLs (if Twilio prefers plain text):

- Privacy: `https://raw.githubusercontent.com/habitual-reset/DANU/main/PRIVACY.md`
- Terms: `https://raw.githubusercontent.com/habitual-reset/DANU/main/TERMS.md`

---

## Campaign description (suggested)

> Personal AI assistant (DANU). Authorized users text or call to receive conversational AI replies. User-initiated, two-way messaging. Not marketing. Message frequency varies. Msg & data rates may apply. STOP to opt out. HELP for help.

---

## Sample messages (paste into Twilio sample message fields)

**Sample 1 (conversational reply):**
```
DANU: Got it — I'll remind you about that meeting tomorrow at 9am. Reply HELP for help, STOP to opt out. Msg & data rates may apply.
```

**Sample 2 (user-initiated response):**
```
DANU: You asked about your grocery list — you have milk and eggs on the list. Reply HELP for help, STOP to opt out.
```

**Sample 3 (help):**
```
DANU: Personal AI assistant. Reply STOP to cancel SMS. HELP for support or email journey@habitualreset.com. Msg & data rates may apply.
```

**Sample 4 (opt-out confirmation):**
```
DANU: You have been unsubscribed and will no longer receive messages. Reply START to resubscribe. Msg & data rates may apply.
```

---

## Other fields Twilio may ask

| Field | Suggested answer |
|-------|------------------|
| **Use case** | Mixed / Customer Care / Low Volume (or "Sole proprietor conversational") |
| **Opt-in type** | Verbal or written (authorized allowlist) |
| **Opt-in description** | User's phone number is explicitly allowlisted by the operator before messaging. User initiates by texting or calling. |
| **Embedded link in messages?** | No (unless you later add links — update campaign if so) |
| **Subscriber help** | Reply HELP or email journey@habitualreset.com |
| **Subscriber opt-out** | Reply STOP |
| **Message volume** | Low (personal use) |