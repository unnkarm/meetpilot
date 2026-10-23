# MeetPilot frontend redesign

## Delivery status — 12 October 2026

Implemented in source and checked in an isolated browser using fixture API responses.
The full Docker/model stack was kept stopped. This is not a hosted launch certification
or a verification of a real meeting, identity provider or Calendar/Zoom account.

## Design

- A light workspace with a persistent sidebar, a compact action toolbar, teal accents,
  readable typography and consistent surfaces replaces the dark purple/glowing UI.
- Responsive navigation includes a mobile drawer, keyboard focus handling, Escape
  dismissal, visible focus indicators, dialog labels and a skip-to-content link.
- Landing, sign-in, onboarding, meeting library/detail, actions, knowledge, search,
  analytics, people/access, integrations, activity and settings use the same palette.
- The landing page describes implemented workflows. Its example summary is explicitly
  illustrative; fabricated adoption/ROI statistics and unimplemented pricing promises
  are not displayed. Data/privacy copy reflects configurable hosted processing.
- The workspace loads separately from the public page. The production build continues
  to use Clerk; the fixture identity module is only selected by the separate UI-test
  Vite configuration.

## Feature and API connections

| Capability | Frontend result | Backend connection |
| --- | --- | --- |
| Meeting library | All meetings, title/participant search, status filters, sort and responsive rows | Existing workspace-scoped meeting list |
| Live meeting state | Live/queued/processing/ready/needs-attention labels; admission-aware request confirmation | Existing live-meeting dispatch; Vexa Lite unchanged |
| Actions | Workspace creation form, verified member selector, optional deadline, source meeting/quote and reversible status selection | Existing task POST/PATCH/DELETE endpoints |
| Role controls | Managers create/assign actions; members see their assigned rows; meeting delete respects manager/creator rules | Existing server role filters retained |
| Knowledge | Document upload, sourced questions and keyboard-accessible citations | Existing document and knowledge-chat endpoints |
| Search | Decision sources now open the meeting at their timestamp; cross-meeting links avoid seeking the previous recording | Existing workspace search endpoint |
| Review | Summary styles, follow-up drafts, chapters, bookmarks, risk review and speaking metrics remain reachable from the meeting tabs | Existing review endpoints and processing worker |
| Export | Markdown and JSON retained; Print/PDF includes summary, decisions, visible actions and transcript regardless of active tab | Existing authenticated meeting data |
| Voice | Live Pilot panel and manager voice settings retained | Existing session/audio/settings endpoints |
| People/access | Join-code entry, approval requests, code rotation, member management and participant mapping retained | Existing workspace/identity endpoints |
| Calendar/Zoom OAuth | Added return screens, expiring account-bound state validation, synchronous popup opening, error handling and parent refresh | Existing authenticated manager-only OAuth exchange endpoints |

### OAuth correction

The old services could save a connected integration using mock credentials when
configuration was missing or a token exchange failed. They now reject missing
configuration, mismatched redirect overrides, rejected/tokenless exchanges and
missing account metadata before committing a connection. Only returned provider
tokens are encrypted and saved. No external account was connected during this work.

Configure the server's Google/Zoom client IDs, secrets and redirect URIs before a
real provider test. Redirects must match the served frontend's
`/oauth/google/callback` or `/oauth/zoom/callback` route. No provider secret is stored
in the browser. The return state is checked against the initiating account,
workspace context and ten-minute browser session record.

## Verification

- `npm run lint`: TypeScript checks passed.
- `npm test`: 17 frontend regression checks covering existing language/audio/role
  behavior plus library status/filtering, ownership controls, action creation
  controls, printable evidence and OAuth return validation.
- `npm run build`: passed; public and workspace bundles split, with no large-bundle warning.
- `python -m compileall -q backend/app backend/alembic`: backend compilation.
- Isolated backend tests: 23 workspace RBAC checks and 4 OAuth failure/success checks passed.
- `frontend/tests/ui/verify_workspace.py`: a headless Chromium walkthrough with
  mocked API responses, including action creation/status writes, knowledge Q&A,
  search-to-source navigation, review generation, role-specific controls, mobile
  layouts/dialogs, printing and OAuth callback success/rejection. No real model calls.
- Screenshots and a sample PDF are written to ignored `scratch/frontend-review/`.

To rerun the isolated UI checks, run `npm run dev:ui-fixture` from `frontend`, then
`python frontend/tests/ui/verify_workspace.py` from the repository root. It requires
an installed Python Playwright runtime and Chromium. Stop the fixture server after
verification. Use the normal frontend dev command for real authentication/data.

## Appearance update — 12 October 2026

Dark is the default, with Blue & purple as the initial accent palette. Explicitly
saved choices are retained. Landing and workspace headers include a light/dark
toggle, and **Settings → Appearance** offers Light, Dark and System plus five
instant-preview palettes: Blue & purple, Ocean blue, Teal, Rose and Amber. Display
mode and palette are saved independently in the browser and synchronized across
tabs. System mode follows device changes. An early HTML initializer applies both
saved choices before React loads. Storage restrictions do not prevent changing
the current tab.

Shared surfaces, meeting views, dialogs, semantic states and Clerk sign-in forms
use the selected palette. Print/PDF reports retain white paper and dark text.
The isolated browser walkthrough checks preference persistence, system changes,
cross-tab updates, restricted storage, pre-React initialization, print colors,
each palette in both display modes, primary button contrast and mobile overflow
with mocked APIs. Screenshots are in the ignored `scratch/frontend-palettes/`
directory. This verifies the frontend behavior;
it does not add a server-side account preference or certify hosted sign-in.

Development Compose mounts current frontend source and enables modest source
polling for Docker Desktop on Windows. A live edit/restore check confirmed Vite
invalidates its module cache; the frontend was recreated independently with
`--no-deps`. Updating `frontend/dist` alone does not update a running dev container.

## Before public launch

Verify real Clerk sign-in, a manager/member pair, joins/approvals, uploads, audible
live voice and configured provider callbacks on the intended HTTPS deployment.
Apply the existing review/workspace migrations. Billing, quotas, private media
storage and deployment operations retain their roadmap status.

The known meeting-voice permission inheritance and JWT authorized-party findings
in [Workspace Access Audit](Workspace_Access_Audit.md) are separate backend launch
blockers; this UI redesign does not close them.
