# MeetPilot policies and recording authorization

**Implemented in source: 12 October 2026. Status: development drafts.**

The founder confirmed that MeetPilot is not registered yet. No fictional legal
entity, business address, privacy email, court, liability cap or certification
has been inserted. The public pages identify incomplete operator details and
limit draft use to development evaluation with non-confidential test content.
These documents require qualified legal review; they do not establish permission
to record a company or serve as a signed data processing agreement (DPA).

## Pages and user flows

| Route | Covers |
| --- | --- |
| `/terms` | Account/organizational authority, ownership, limited processing permission, acceptable use, AI limitations, sharing, changes and mandatory rights |
| `/privacy` | Actual data categories, purposes, access, providers, retention/deletion limits, browser storage and data requests |
| `/recording-policy` | Pre-recording authorization and notice, objections, late arrivals, responsible uploads and an adaptable participant notice |

Pages are public for signed-out and signed-in users, have separate URLs, a table
of contents, theme support, mobile layouts and print/save-PDF styles. They are
linked from the landing footer, authentication UI, Settings and the first-action prompt.
Production hosting must serve the SPA for direct requests to these paths.

Registration, login, workspace entry and ordinary browsing do not prompt or
fetch legal acceptance status. The first operational action (join/upload/record,
AI queries, tasks, document uploads, connector setup or exports) checks the
account's saved acknowledgment. If absent, one dialog asks for agreement to Terms
and acknowledgment of the Privacy and Recording notices. These notices are not
represented as blanket consent to every processing purpose. On acceptance the
original action continues once. Cancelling leaves the action unperformed and
preserves any draft. Errors block only the requested action and offer retry;
the workspace remains accessible. OAuth callbacks finish without a prompt.

**Founder-directed UX revision:** acknowledgment is once per account. Login,
another workspace, revised disclosures or new policy versions do not trigger
another prompt. Existing receipts remain valid. Settings shows the acceptance
date/version and links to the current pages. Later policy publication is not
represented as acceptance of a new contract: the original receipt is retained.

### Backend receipts and capture checks

- `GET /api/v1/legal/policies` exposes only public, allowlisted policy details.
- `GET /api/v1/legal/acceptance` returns the authenticated account's existing
  receipt and current public policies, including the originally accepted versions.
- `POST /api/v1/legal/acceptance` requires three strict `true` booleans and the
  current policy bundle for first acceptance; extra actor IDs are rejected.
  A stale first submission returns 409. Already-accepted accounts reuse their
  original receipt even if the requested bundle has since changed.
- Receipts use the existing `product_events` table; no new migration is needed.
  They store the account, server timestamp, document versions and the public
  operator/disclosure snapshot. Tokens and IP addresses are not added.
- Versions, operator disclosures and publication state determine a bundle hash.
  Changes do not invalidate acknowledgment. Same-account acceptance locks the
  user row and reuses an existing receipt across bundles.
- Live starts and audio uploads check membership first, then require an existing
  account receipt. No per-recording agreement fields are required.
  This occurs before bot preflight/dispatch or application storage/processing.
  They record a workspace/meeting-scoped policy reference to the original
  receipt, with `participant_consent_verified=false` and
  `per_recording_authorization_collected=false`. No per-meeting attestation is invented.
- Repeated recording checkboxes have been removed. Microphone access and Pilot
  session creation wait for first acknowledgment; accepted accounts proceed
  immediately. A requester registered only in the authenticated workspace handles
  first-use prompts; it does not install a global registration/signup blocker.
- The shared API client defers mutations and semantic searches before sending
  them. Join/upload/record launchers, local microphone capture, exports and OAuth
  initiation explicitly check acceptance. Passive reads and OAuth returns are exempt.

**Scope:** this first-action UX is not a new global server authorization dependency.
Existing HTTP reads, connected-service imports, background work and voice
WebSocket protocols retain their existing authorization behavior. Do not claim
that every API is legally gated or that participant consent was independently
verified. Cover integration imports/automations and voice-session capture with
appropriate explicit instructions and audit controls before public launch.
Request multipart parsing can spool a file before route checks; application
storage and job dispatch are checked here, not pre-body network admission.

## Operator configuration

Set these server-side fields after actual review. They are **public disclosures**;
never put credentials, private database URLs or secret infrastructure details in
them. Blank fields are displayed as not finalized.

```dotenv
LEGAL_POLICIES_PUBLISHED=false
LEGAL_OPERATOR_NAME=
LEGAL_OPERATOR_ADDRESS=
LEGAL_PRIVACY_EMAIL=
LEGAL_JURISDICTION=
LEGAL_PROCESSING_DISCLOSURE=
LEGAL_RETENTION_DISCLOSURE=
```

The public metadata reports publication only when the publication flag and all
six disclosures are present. A flag is an operator declaration, not legal
approval. **Do not switch it on for the current development copy.** First finalize
the contracting person/entity and contact, actual provider/region/transfer list,
retention schedules, production safeguards and reviewed policy wording; replace
draft-only statements and bump the document versions in both
`frontend/src/utils/legal.ts` and `backend/app/services/legal_policies.py`.
Archive each reviewed policy revision and its rendered text outside mutable
working copies. The current receipt stores metadata, not the full document text.
Deploy matched frontend/backend versions together; version mismatches block the
first-acceptance flow; accepted accounts are not reprompted for mismatches.
Restart/redeploy the backend when settings/routes change.

## Data authority and launch work still required

Customer rights to content and participants' privacy rights continue to apply.
The limited permission in Terms is for delivering requested services, security,
authorized support and legal obligations; it does not transfer company-data
ownership or establish a lawful basis on participants' behalf. Host admission
is not evidence of everyone's consent. Applicable law can require a different
basis or additional permissions; assess participants' locations and the actual
employment/business context.

Before handling production company data:

- Identify the operator (which may be a natural person or entity as legally
  appropriate), publish a real privacy contact, and settle governing terms.
- Obtain legal review for intended markets, recording rules, employment use,
  sensitive data and applicable rights/request deadlines.
- Prepare a suitable DPA, documented customer instructions, subprocessor list,
  transfer arrangements, security schedule and change notification process.
- Publish and actually implement retention, backup expiry, provider/object-store
  deletion, account requests and incident response. Current deletion controls
  do not prove complete erasure from every provider or backup.
- Review the two open access-audit findings in `Workspace_Access_Audit.md` and
  verify production auth, isolation and media access. These policy changes do
  not fix those findings or confer a compliance/security certification.
- Confirm providers' current training/retention terms before configuring paid
  inference. Keep credentials server-side; do not activate paid fallbacks.

## Primary guidance reviewed

- [EDPB small-business FAQ](https://www.edpb.europa.eu/sme/find-practical-info/faq_en):
  informs the distinction between notice, lawful processing and controller /
  processor contracts. Applicable GDPR obligations depend on the processing.
- [EDPB legal basis guidance](https://www.edpb.europa.eu/topics/key-gdpr-concepts/legal-basis_en):
  supports determining an appropriate legal basis rather than assuming a
  platform checkbox supplies one for every use.
- [Indian DPDP Rules 2025, official Gazette](https://www.meity.gov.in/static/uploads/2025/11/53450e6e5dc0bfa85ebd78686cadad39.pdf):
  commencement is phased. Do not assume every provision is already operative on
  12 October 2026; review the applicable commencement notices and corrections
  for the actual launch date. No Indian-law compliance claim is made here.

## Verification

- Backend compilation passed for `backend/app` and `backend/alembic`.
- 31 isolated SQLite/HTTP tests passed: eight new policy tests plus 23 existing
  workspace permission regressions. Vexa calls and job dispatch were mocked.
  The host Python lacked PyJWT, so tests used dependencies inside the already
  running backend container; no services, models or bots were started.
- Frontend TypeScript and production build passed.
- Isolated Playwright checks cover public pages with/without sign-in, history,
  draft disclosures, no entry prompt, first-action continuation/cancellation,
  saved acknowledgment across revisions, Settings, stale first-submission
  rejection, action-specific error blocking, deferred task creation, print and mobile.
- All 17 frontend unit tests and the existing full workspace browser walkthrough
  passed. Only the already-running backend was restarted to expose the new
  endpoints; its public policy metadata reports draft status. The three local
  public page routes returned HTTP 200. Meeting/model services stayed stopped.
- Live company recording, legal approval and a hosted deployment were not
  verified by these source checks.
