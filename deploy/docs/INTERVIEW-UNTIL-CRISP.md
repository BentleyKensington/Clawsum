# Interview until the spec is crisp

Hermes (and any agent that receives a fuzzy Boss ask) must **not** invent a build. Use skill `spec-interview`.

---

## Spec card (required fields)

| Field | Done when |
|-------|-----------|
| **Goal** | One sentence, testable |
| **Success metric** | Number, date, or observable |
| **Out of scope** | At least one explicit non-goal |
| **Owner agent** | OpenClaw id |
| **Cell** | From authority projects |
| **Deadline** | Date or “no date — queue” |
| **Risk tier** | 0–3 |
| **Dependencies** | Keys, SSH, people, other CLA ids |
| **Open questions** | Zero, or listed with owners |

---

## Procedure

1. Restate the ask in one sentence. If Gerald says “wrong,” fix the sentence before anything else.
2. Fill the card from what he already said (Gmail, archive, Paperclip). **Don’t re-ask known facts.**
3. Ask **one** missing field per turn, highest leverage first (usually Goal → Success → Out of scope → Owner).
4. When blocked on a secret/path, say exactly which env var or file is missing — don’t stall with vague “need more info.”
5. Write/update Paperclip issue. Link Gmail `ops.emails.id` and archive conversation ids in the description.
6. Stop. Execution starts only after Approve All / existing preapproved skill.

Casual hellos skip this (SOUL conversational mode).

---

## Linking Gmail, tasks, archive

On every non-casual work item:

```bash
python3 /docker/clawsum/scripts/gmail-inbox-review.py --inbox-only --markdown --no-per-email-report
python3 /docker/clawsum/scripts/archive-proactive-brief.py --markdown
python3 /docker/clawsum/scripts/gmail-task-link.py --markdown
```

Say `CLA-…` ids. Do not create duplicate issues for the same thread.

Personal-scope archive stays off business agents.
