# Issue 02 — Admin login fails: `.local` email rejected as "not deliverable"

## Symptom

Real output from the first live end-to-end verification run
(`scripts/verify_e2e.sh`):

```
[FAIL] admin: the admin account can read system status (0.0s) —
{"detail":[{"type":"value_error","loc":["body","email"],
"msg":"value is not a valid email address: The part after the @-sign is a
special-use or reserved name that cannot be used with email.",
"input":"admin@commerceiq.local", ...}]}
```

The admin account IS seeded correctly in the database on startup (confirmed
in the container logs: `Seeded admin user: admin@commerceiq.local`) — but
logging in as that account via `POST /api/auth/login` was **impossible**,
because the request body was rejected before the handler even ran.

## Root cause

`routers/auth.py`'s `LoginRequest`/`SignupRequest` used Pydantic's
`EmailStr` type, which validates through the `email-validator` package.
That package doesn't just check *syntax* — by default it also runs a
**deliverability check** that rejects domains on a reserved/special-use list
(`.local`, `.test`, `.example`, `.invalid`, etc., per RFC 2606 / RFC 6762),
on the theory that an email to such a domain could never really be
delivered. `commerceiq.local` matched that reserved-TLD rule and was
rejected outright, regardless of the fact that this app never sends real
email — it only uses the field as a login identifier.

This is a **real design mismatch, not just a test artifact**: the project
brief explicitly targets *internal company (사내) tools* for AX use cases,
where `.local` / `.internal` / `.corp` — style login domains are completely
normal for demo, staging, and even production on-prem deployments.
Deliverability-oriented email validation is the wrong tool for a login
identifier field.

## Fix applied

Replaced `EmailStr` with a plain `str` field plus a small custom Pydantic
`field_validator` (`_EMAIL_RE`) in `routers/auth.py` that checks only basic
shape — `local-part@domain.tld` — with no reserved-TLD or deliverability
check. `admin@commerceiq.local` (and any other internal-style domain) now
passes. Garbage input (`"notanemail"`, empty string) is still rejected.

## Verification

Re-ran `scripts/verify_e2e.sh` after the fix and rebuild — see
`../history/v1.0.0.md` for the full pass/fail table from that run.

## What to study if this is new to you

- This is a good real example of **"validate what you actually need, not
  the strictest available check."** `EmailStr`/`email-validator` is the
  right choice when an app genuinely sends email and needs deliverability
  confidence; it is the wrong choice for a login-ID field in an internal
  tool. Picking a validation library by name recognition instead of by what
  the field is actually used for is a common, easy-to-miss mistake.
- Related principle: this mirrors the "검증 규칙" (validation rules) idea of
  structuring inputs/outputs with explicit, purpose-built validation, and
  the broader "always define what 'valid' means for *this* field, don't
  assume a library's default is automatically correct" principle common to
  output-parsing and input-validation design generally.
