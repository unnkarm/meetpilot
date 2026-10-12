# Workspace Access and Identity Audit

**Updated: 8 October 2026.** Source changes are implemented and focused checks pass. Docker remains stopped; the database migration and live browser flows still require verification when the stack is available.

## Requested policy

All approved teammates may see every meeting in their workspace, including transcripts, summaries, decisions, and meeting audio. Teammates see their own assigned task records. Managers control company knowledge documents, assignments, and shared analysis.

Workspace roles are `owner`, `admin` (manager), and `member` (teammate). They are scoped to a workspace, rather than inferred from a global user role.

## Findings and changes

The earlier implementation allowed members to manage documents, change other people's tasks, and edit shared analysis. Role updates also permitted unsafe changes to ownership. Meeting display names could be used to guess user assignments without adequate identity evidence.

The changes enforce permissions in backend routes and SQL retrieval, with corresponding UI controls. Task filtering applies before search/retrieval limits, and to Pilot context, so another teammate's assignments are not included merely because a query came through AI rather than the task endpoint.

The continuation audit also closed the following gaps:

- New accounts choose **Join Workspace with Code** or **Create workspace** explicitly; a personal workspace is no longer silently created.
- Approved applicants can enter the workspace from their request status. Removed memberships are shown as removed rather than approved.
- Managers can disable a join code, as well as replace it. Disabling a code blocks new applications; existing pending applications still need review.
- Membership changes use a workspace lock and fresh role checks. A cached manager role cannot authorize actions after demotion.
- Teammates cannot browse or import the company's external Zoom cloud recording library; they can still read meetings already imported into their workspace.
- Meeting-creator/uploader tags alone no longer prove speaker identity. Duplicate speaker labels, including case variants, are blocked from name-based attribution.
- Client request caches are separated by authenticated account, and task lists are filtered immediately after role changes while fresh server results are fetched.
- Pilot task-list queries give managers the workspace view and teammates their own assignments; an explicit "my tasks" query stays personal for every role.

## Permission matrix

| Capability | Owner | Admin / manager | Member / teammate |
| --- | --- | --- | --- |
| Read every workspace meeting and its analysis | Yes | Yes | Yes |
| Read/use company knowledge | Yes | Yes | Yes |
| Manage integrations / browse-import company Zoom cloud recordings | Yes | Yes | No |
| Upload/delete company documents | Yes | Yes | No |
| Read all task records | Yes | Yes | Own assignments only |
| Create, assign, edit, or delete tasks | Yes | Yes | No |
| Change an assigned task's status | Yes | Yes | Own assignments only |
| Edit shared summaries and decisions | Yes | Yes | No |
| Start a meeting | Yes | Yes | Yes |
| Manage a meeting's capture/title/retry/delete | All | All | Meetings they created |
| Generate/rotate join code; review applications | Yes | Yes | No |
| Directly invite an existing verified account as member | Yes | Yes | No |
| Promote/demote admins or remove an admin | Yes | No | No |
| Remove ordinary members | Yes | Yes | No |
| Change/remove the canonical workspace owner | No through member controls | No | No |
| Delete the workspace | Yes | No | No |
| Confirm speaker-to-account attribution | Yes | Yes | No |

Personal knowledge-chat history is scoped to its requester for teammates. Managers can review workspace chat history. Meeting content is shared under the requested all-meetings policy.

Meeting summaries may contain shared discussion of responsibilities. The task restriction applies to structured task records and task-based retrieval; it does not redact the shared transcript or summary. Removing someone from the workspace prevents further authorized access, but cannot revoke copies they already downloaded.

## Joining with manager approval

1. A manager opens **Team**, generates a join code, and uses **Copy code** to share it.
2. The applicant signs into MeetPilot and chooses **Join Workspace with Code**.
3. A valid code creates a pending request. It grants no workspace membership or data access.
4. Managers see pending requests in Team and the workspace notification banner.
5. Approval creates a `member` membership; rejection grants no access.

Codes use a cryptographically random 192-bit value. Only a SHA-256 hash is stored; the raw code is displayed when generated. Codes expire after 30 days and rotation invalidates the old code. Sample/demo workspaces do not issue join codes.

An applicant without any workspaces sees an onboarding screen with the join option and request history. Manager reviews are polled in Team; pending counts also appear on the navigation/dashboard. After approval, **Enter workspace** rechecks the applicant's available memberships before opening it.

Duplicate pending submissions are idempotent. Rejected applicants cannot repeatedly reapply through the same workflow; they can contact a manager. Someone previously approved and subsequently removed must obtain fresh approval if they request to rejoin. Approval checks the reviewer's current role and serializes workspace changes.

Existing manager email invitations remain an explicit direct grant to an existing verified account. Owner-only controls apply when inviting an admin.

## How meeting identity is established

MeetPilot login identity is based on the authenticated Clerk subject. Email linking requires verified email evidence from trusted claims or Clerk's primary-email verification metadata.

A Google Meet display name is not proof that the speaker is the same MeetPilot user. Two participants can have the same name, names can change, and the current Vexa bridge usually supplies speaker labels without guaranteed verified account emails.

Supported attribution paths are:

- Trusted provider identity evidence tied to the workspace, including verified email matched to an app account whose email is also verified.
- A manager's explicit selection of a workspace account for an observed speaker label in the meeting identity panel.

Name-only assignment guesses no longer establish `assignee_id`. Proposed owner names and source quotes can remain visible as unconfirmed evidence until a manager resolves them. Ambiguous labels and out-of-workspace account selections are rejected. Uploading a recording or starting a bot does not establish that the creator actually spoke under a matching label.

**Manager-confirmed attribution is not voice authentication.** It helps attach evidence and tasks to an account. It does not authorize that speaker to issue privileged commands. Privileged actions from the meeting audio source remain restricted; explicit authenticated Pilot task creation also checks the user's manager role.

No biometric same-person verification or guaranteed Google-account identification has been implemented. This limitation must remain clear in product documentation.

## Migration and existing data

New migration: `backend/alembic/versions/e5f6a7b8c9d0_workspace_approval.py`.

It adds join-code metadata, join-request records, verified-email metadata, and manager attribution metadata. It repairs memberships to protect the workspace's canonical owner.

It also clears assignment IDs on older AI-extracted tasks that may have been attached by name-only guessing, preserving task text, proposed names, and evidence. Managers should review and confirm those assignments after migration. The migration does not restore these assignment IDs on downgrade.

The migration accounts for the existing bootstrap process creating new schema elements before Alembic. Actual PostgreSQL execution still needs verification on both an existing database and a fresh installation.

When the local stack is ready, back up the database, rebuild the backend image so the migration and schema changes are available, and run the normal reviewed migration/startup process. The stack was deliberately not restarted during this audit because of the PC heating issue.

## Verification completed

- Backend compilation: `python -m compileall -q backend/app backend/alembic backend/scripts` passed.
- Focused backend suite: **43 passed, 1 skipped** across workspace RBAC, authentication, workspace isolation, processing/edit regression, and language preferences. The skipped test depends on unavailable ffmpeg.
- The RBAC suite includes **23 database-backed tests**, covering pending-access denial, approval/rejection, expiry/rotation/disabling, ownership protection, assignment visibility, manager-only mutations, identity evidence, personal history, removal/reapproval, cached-role demotion, Zoom access, and Pilot task queries.
- Frontend tests: **8 passed**; permission checks include missing-role defaults, teammate task controls, explicit onboarding choices, and approval-only workspace entry.
- Frontend lint/type checking and production build passed. The build retains the existing large-chunk warning.

These are host-side checks, primarily using an in-memory SQLite database for HTTP permission tests. They do not prove a live PostgreSQL migration, actual Clerk production configuration, multi-user browser behavior, or meeting-provider account verification. This was a focused access audit, not a comprehensive penetration test.

## Production follow-up

Before broad public signup, add rate limits for join requests and privileged actions, a comprehensive administrative audit trail, production JWT audience/authorized-party hardening, migration/restore tests, and real multi-account staging checks. Validate removal during active WebSocket sessions and identity conflicts across actual meetings.

## Manual verification when the stack is available

1. Sign in as the workspace owner. Open Team and generate/copy a code.
2. In a separate browser profile, sign in as a teammate, request to join, and confirm no company meetings/documents are accessible before approval.
3. Approve the request as the owner. Enter the workspace as the teammate and read a meeting summary and company knowledge.
4. Assign one task to that teammate and another to someone else. Confirm task lists, search, and Pilot task queries show only the teammate's assignment, with only status editing available.
5. Confirm document upload/delete, shared-analysis editing, and manager controls are unavailable to the teammate and return 403 through the API.
6. Confirm a speaker using the meeting identity panel; separately test a duplicated name. Attribution must never authorize meeting voice actions.
7. Remove the teammate or demote an admin, then retry actions from their still-open session. Confirm access reflects the new membership/role and a removed user must request approval again.
8. Disable/rotate the code and confirm the previous value cannot create a new request.

This verification uses two authenticated accounts and remains pending while Docker is stopped. Source checks do not substitute for it.

The deployment, scaling, pricing, and launch plan is in `SaaS_Deployment_Scaling_GoToMarket.md`.
