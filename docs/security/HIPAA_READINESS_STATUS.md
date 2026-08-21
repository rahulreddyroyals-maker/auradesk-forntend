# HIPAA Readiness Status

**AuraDesk is not HIPAA compliant.** No product can claim that in
isolation. What follows is a line-by-line status of technical
safeguards, honestly classified. Compliance itself is a property of an
organization's whole program — this list is necessary, not sufficient.

Classification key: **IMPLEMENTED** / **PARTIALLY IMPLEMENTED** / **NOT
IMPLEMENTED** / **VENDOR DEPENDENCY** / **LEGAL/ADMINISTRATIVE
REQUIREMENT** / **UNKNOWN — REQUIRES VERIFICATION**

## Technical safeguards (45 CFR §164.312)

| Requirement | Status | Notes |
|---|---|---|
| Unique user identification | IMPLEMENTED | Supabase Auth, one account per staff member |
| Emergency access procedure | NOT IMPLEMENTED | No documented break-glass access process |
| Automatic logoff | UNKNOWN — REQUIRES VERIFICATION | Depends on Supabase's default session/refresh-token lifetime; not overridden or verified in this codebase |
| Encryption/decryption (at rest) | VENDOR DEPENDENCY | Supabase's platform default — not independently configured or verified by this codebase |
| Encryption/decryption (in transit) | IMPLEMENTED | HTTPS/TLS for all vendor API calls (verify this holds for however the app is ultimately deployed/hosted) |
| Audit controls | PARTIALLY IMPLEMENTED | `audit_logs` table added this pass, covering staff/integration/patient-deletion/escalation events; does not yet cover conversation *viewing* or every data-access path |
| Integrity controls (data not improperly altered/destroyed) | PARTIALLY IMPLEMENTED | Application-level tenant scoping + RLS reduce unauthorized alteration risk; no checksums/tamper-evidence on stored records |
| Person/entity authentication | IMPLEMENTED | JWT-based, verified server-side |
| Transmission security | IMPLEMENTED | TLS to every current vendor |

## Administrative safeguards (45 CFR §164.308)

| Requirement | Status | Notes |
|---|---|---|
| Risk analysis | NOT IMPLEMENTED | This document set is a technical audit, not a formal HIPAA risk analysis — those are related but distinct; a formal one should be commissioned |
| Risk management | NOT IMPLEMENTED | Follows from risk analysis above |
| Sanction policy | LEGAL/ADMINISTRATIVE REQUIREMENT | Not an engineering artifact |
| Information system activity review | PARTIALLY IMPLEMENTED | Audit log exists; no regular review process defined |
| Workforce security / access authorization | PARTIALLY IMPLEMENTED | RBAC exists (owner/admin/front_desk); no documented workforce clearance procedure |
| Security awareness/training | LEGAL/ADMINISTRATIVE REQUIREMENT | Not an engineering artifact |
| Security incident procedures | PARTIALLY IMPLEMENTED | `INCIDENT_RESPONSE.md` is a skeleton, not a completed, owned policy |
| Contingency plan (backup/DR) | PARTIALLY IMPLEMENTED | See `BACKUP_AND_RECOVERY.md` — relies on unverified Supabase defaults |
| Business Associate Agreements | **NOT IMPLEMENTED — CRITICAL BLOCKER** | Zero BAAs currently signed with any vendor |

## Multi-tenancy / access control

| Requirement | Status | Notes |
|---|---|---|
| Tenant data isolation (application layer) | IMPLEMENTED | Audited across all 44 endpoints this pass, confirmed clean |
| Tenant data isolation (database layer / RLS) | IMPLEMENTED, OPT-IN | Built this pass; requires running `sql/restrict_app_role.sql` and setting `DATABASE_URL`/`DATABASE_URL_ADMIN` — not yet activated by default |
| Role-based access control | PARTIALLY IMPLEMENTED | Three roles exist; finer-grained resource-level permissions (e.g. who can view raw conversations) not yet built |
| Multi-factor authentication | NOT IMPLEMENTED | Supabase supports it natively; no enrollment/challenge flow built in this app yet |

## AI-specific safeguards

| Requirement | Status | Notes |
|---|---|---|
| Tool authorization enforced server-side, not by the LLM | IMPLEMENTED | Was already true architecturally; verified by test this pass |
| Data minimization to the LLM | PARTIALLY IMPLEMENTED | Bounded conversation history, strict tenant scoping; the product's function inherently requires sending message content |
| Channel-specific PHI restriction (Messenger/Instagram) | IMPLEMENTED | Added this pass; reduces but does not eliminate exposure — see `AI_SAFETY.md` |
| Medical scope guardrails (no diagnosis/prescription) | IMPLEMENTED | System prompt + keyword-based urgent-escalation bypass |
| Prompt injection defense | PARTIALLY IMPLEMENTED | Relies on the tool-authorization boundary rather than a dedicated injection classifier |

## Vendor readiness (see `THIRD_PARTY_VENDOR_MATRIX.md` for full detail)

| Vendor | Status |
|---|---|
| Groq | VENDOR DEPENDENCY — BAA available, not signed |
| Twilio | VENDOR DEPENDENCY — BAA available on Security/Enterprise Edition only, current account is not that tier |
| Supabase | VENDOR DEPENDENCY — BAA + HIPAA add-on available on Team/Enterprise only, current plan is not that tier |
| Cartesia | VENDOR DEPENDENCY — BAA available via enterprise contract, not signed |
| ElevenLabs | VENDOR DEPENDENCY — BAA available on Business/Enterprise + Zero Retention Mode, not configured |
| **Meta (Messenger/Instagram)** | **STRUCTURAL — will not sign a BAA, ever, on any plan** |
| Stripe | N/A — no PHI exposure by architecture |

## The bottom line

Real engineering safeguards exist and were meaningfully strengthened
this pass: tenant isolation (now enforced at two layers), audit
logging, logging redaction, channel-specific AI restrictions, rate
limiting, and a security test suite. **None of that substitutes for the
business-side work that's still entirely outstanding**: signing BAAs,
upgrading vendor plans to their HIPAA-eligible tiers, commissioning a
formal risk analysis, and completing the administrative-safeguard
documents that are currently skeletons (`INCIDENT_RESPONSE.md`,
`BACKUP_AND_RECOVERY.md`). Until those are done, this system should only
ever be used with synthetic test data — never real patient information.
