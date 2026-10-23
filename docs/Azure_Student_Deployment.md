# MeetPilot on Azure for Students

Prepared 12 October 2026. The founder confirmed **Azure for Students with $100 credit**.
Remaining balance, activation/expiry dates, eligible free meters, allowed regions,
quotas and resource availability have not been read from the account. No Azure
resource has been created and no paid provider has been enabled by this preparation.

## 1. What your offer can realistically cover

The $100 is a pool for the offer period, not $100 each month. It is usable within
12 months; eligible students can renew annually. Specific free service allowances
are separate, and some apply only to new Azure customers for their first 12 months.
Renewing student eligibility does not establish that every introductory service
allowance restarts. Check the actual subscription before provisioning.
[Student program](https://learn.microsoft.com/en-us/azure/education-hub/about-azure-for-students),
[offer overview](https://azure.microsoft.com/en-us/free/students/).

There are three different meanings of "free":

1. **Within a recurring free allowance:** suitable for a small static website.
2. **Within an introductory allowance:** potentially the small database, for a limited period.
3. **Paid usage covered by your $100:** no personal payment while protected credit remains,
   but it spends the same finite pool you want to preserve.

**Recommendation:** publish the frontend as a personal project preview on Static
Web Apps Free, then use tightly scheduled, private cloud sessions for the backend.
The present complete live-meeting platform cannot responsibly be promised as an
always-on, permanently free service on this offer. A website URL alone does not
mean uploads, summaries, workspace data, search or live calls are deployed.

### Component-by-component assessment

| MeetPilot part | Azure option | Cost boundary and readiness |
| --- | --- | --- |
| React landing page/dashboard files | Static Web Apps **Free** | Good first step. 100 GB monthly bandwidth per subscription, 250 MB per deployment, free TLS. Free is intended for personal projects and has no SLA. |
| Main PostgreSQL + pgvector | PostgreSQL Flexible Server, eligible **B1ms** free meters | Offer lists 750 compute hours/month, 32 GB data and 32 GB backup for 12 months. Confirm eligibility; enable `vector`. A second server shares applicable allowance usage; it is not another automatic free database. |
| FastAPI | Container Apps Consumption or Linux VM | A small API may fit a free grant after preparation. Current image also installs speech models, audio tools and Chromium; it is not a lean web image. |
| Celery + Redis | Private services on a host initially | Need durable workers/queues. Do not budget a managed Redis service as free without a specific verified allowance. |
| Vexa Lite and bridge | Suitable x86-64 Linux compute | Long-running browsers, shared memory, audio and a separate engine database/queue/storage make this the difficult part. Preserve the working integration. |
| Whisper/Piper | Server-side speech workers | No metered inference bill when self-hosted, but CPU, RAM, disks and runtime still consume hosting resources. |
| Ollama text/embeddings | Server-side model host for development | Free model software does not make its hosting free. Tiny promotional VMs are unsuitable for the complete stack. |
| GPT and embeddings | Direct OpenAI today; Azure adapter is future work | Existing direct OpenAI requests are outside Azure credit. Azure-hosted models require account quota, an adapter and metered usage. |
| Recordings | Persistent host volumes initially; private Blob adapter later | Current app storage supports only `local://`. Creating a Blob account does not connect the app to it. |
| Login | Existing Clerk integration | Separate service/account and limits. Keep Clerk; Azure deployment does not replace it automatically. |

Sources: [Static Web Apps pricing](https://azure.microsoft.com/en-us/pricing/details/app-service/static/),
[student service allowances](https://azure.microsoft.com/en-us/free/students/),
[PostgreSQL vector support](https://learn.microsoft.com/en-us/azure/postgresql/extensions/how-to-use-pgvector).
Readiness comes from this repository's Compose, Dockerfiles, provider/storage code
and [Cloud_AI.md](Cloud_AI.md), rather than from an Azure deployment test.

### Why "free VM" and "2 million requests" do not mean the whole app is free

The advertised B2ats_v2 VM has 2 vCPUs but only **1 GiB RAM** and uses burst CPU
credits. It is not the 2-vCPU/8-GiB B2as_v2, which is a different SKU. Memory and
sustained compute are decisive for browsers and models.
[Microsoft VM specifications](https://learn.microsoft.com/en-us/azure/virtual-machines/sizes/general-purpose/basv2-series).

Container Apps Consumption grants 180,000 vCPU-seconds, 360,000 GiB-seconds and
2 million external HTTP requests per subscription per calendar month. An active
1-vCPU/2-GiB replica consumes both compute grants in **50 hours**. At 0.25 vCPU /
0.5 GiB, that arithmetic becomes 200 hours, but this is not enough capacity for
our full image/stack. Multiple apps share the grant. Idle rules differ; attached
storage, networking and logging can add charges. Scaling to zero stops replica
compute billing, not all associated resource costs.
[Container Apps billing](https://learn.microsoft.com/en-us/azure/container-apps/billing).

For now, splitting the complete stack across serverless replicas would also break
the shared local-file assumption unless durable shared storage is configured.
Replica-local files are temporary. Vexa's browser/audio runtime needs its own
compatibility verification, rather than a blind Compose conversion.
[Storage behavior](https://learn.microsoft.com/en-us/azure/container-apps/storage-mounts).

## 2. Azure vocabulary

- **Tenant/directory:** the identity boundary of your Azure account.
- **Subscription:** the billing/credit and quota boundary. Select the student one.
- **Resource group:** a folder-like grouping for resources with a common lifecycle.
  The grouping itself does not buy or allocate a server.
- **Region:** where a service runs. Prefer a nearby permitted region with compatible
  services and a suitable quote; India availability is not assumed.
- **Resource:** an individual website, database, disk, IP address or server.
- **SKU/tier:** the exact size/plan. A similarly named paid SKU is not free.
- **VM:** a rented computer where we manage Linux, Docker, backups and updates.
- **Container Apps:** managed container execution; it does not remove compute charges.
- **Static Web Apps:** hosting for built browser files, separate from our Python workers.
- **TLS/HTTPS:** encrypted browser access, also needed for hosted microphone access.
- **Budget:** a cost alert. It does not normally stop resources.

## 3. Protect the $100 before deploying

1. Open [Azure Portal](https://portal.azure.com/) and search **Subscriptions**.
   Select **Azure for Students** and check that its state is Active. Record its
   expiry and current balance in a private note. The
   [Sponsorships portal](https://www.microsoftazuresponsorships.com/) can show credit;
   follow the account's actual billing links if the portal layout differs.
   [Credit guidance](https://learn.microsoft.com/en-us/azure/cost-management-billing/manage/azurestudents-subscription-disabled).
2. Keep the student spending protection. Do not upgrade to pay-as-you-go or remove
   a spending limit to get around a blocked region, SKU or AI quota. Exhausting
   student credit can disable the subscription and interrupt even the website.
   Export data before reaching that point.
   [Spending limits](https://learn.microsoft.com/en-us/azure/cost-management-billing/manage/spending-limit).
3. Inspect **Free services** in the subscription/portal and note the eligible
   meters and end dates. Creation-screen price estimates may show retail rates;
   confirm the meter allowance rather than assuming a zero-looking estimate is proof.
4. If Cost Management budgets are available, set an initial monthly alert budget
   equivalent to **$5**, with actual thresholds 50%, 80% and 100%, plus a forecast
   alert. Use the account's billing currency. If budgeting is unavailable for your
   offer, track the credit balance directly; a missing budget does not make usage free.
5. Review balance and cost by resource after each experiment and again after usage
   data updates. Budget alerts can lag; they are not a $5 hard cap.
   [Budget behavior](https://learn.microsoft.com/en-us/azure/cost-management-billing/costs/tutorial-acm-create-budgets).
6. Use separate groups: `rg-meetpilot-web-preview` and later
   `rg-meetpilot-compute-demo`. This makes it easier to identify experiment costs
   without accidentally deleting the frontend or shared data.

The full-year arithmetic is **$100 / 12 = $8.33/month**, not a new monthly credit.
Any already-used balance or shorter remaining time changes this calculation.
Our suggested $5 target leaves room for mistakes and backups; it is a planning
choice, not an Azure-enforced limit.

Avoid adding Kubernetes, a GPU, a NAT Gateway, Bastion, premium database replicas,
or large monitoring workspaces for the initial preview. They are not needed for
this first deployment. Student credits also have exclusions, including Azure
Marketplace purchases; downloaded software benefits have separate restrictions.
[Offer details](https://azure.microsoft.com/en-us/pricing/offers/ms-azr-0170p/).

### Runtime example, not a current Azure price quotation

Get an account/region-specific quote from the
[Azure calculator](https://azure.microsoft.com/en-us/pricing/calculator/) before
creating compute. The retail API could not be reached from this workspace, so no
VM dollar rate has been verified in this preparation.

Suppose a selected VM cost **$0.20/hour**, and retained disk/IP/other resources
cost **$5/month**. Those are deliberately hypothetical inputs:

| Schedule | Compute | Other | Result |
| --- | --- | --- | --- |
| 730 hours in a month | $146 | $5 | $151/month; exceeds the whole credit in one month |
| 10 hours/month | $2 | $5 | $7/month; $84 over 12 months, before inference/other extras |
| 20 hours/month | $4 | $5 | $9/month; $108/year, before inference/other extras |

Thus "two hours every day" can be unaffordable even when a few scheduled sessions
fit. For a chosen planning period, subtract retained-resource and other costs
from available credit, then divide the remainder by the actual hourly rate.
Keep a reserve. Do not count API calls, builds, disks or network traffic twice,
and do not omit them. Full-stack capacity still needs benchmarking.

## 4. Deploy the frontend first

This is a personal project preview. No backend is provisioned in this stage.
Existing sign-in and dashboard code still needs a real Clerk publishable key;
workspace operations need a backend even though the files are hosted.

### Files prepared in this change

- `frontend/public/staticwebapp.config.json`: SPA fallback so `/app`, `/workspace`,
  legal pages and OAuth callbacks can refresh. `/api/*`, `/health` and missing
  static assets are excluded so a missing API is not disguised as HTML.
- `deploy/azure/frontend.manual.yml`: manually triggered GitHub Actions template.
  It builds only the frontend, checks types, then uploads the built files. It
  creates no resources and is inactive outside `.github/workflows`.

Vite copies the public configuration into `frontend/dist` during the build.
[Routing configuration](https://learn.microsoft.com/en-us/azure/static-web-apps/configuration),
[prebuilt asset deployment](https://learn.microsoft.com/en-us/azure/static-web-apps/build-configuration).

### A. Create the free hosting resource

1. In Azure Portal search **Static Web Apps**, then choose **Create**.
2. Select your student subscription and `rg-meetpilot-web-preview` (create that
   group if needed). Name the app, for example `meetpilot-student-preview`.
3. Select **Free** explicitly. Use a permitted region offered by the wizard.
4. For deployment source choose **Other** if available, since the prepared
   workflow uses a deployment token. This avoids automatically adding a second
   workflow. If using the portal's GitHub integration instead, use the settings
   in the table below and keep only one frontend deployment workflow.
5. Review the selected plan and create the resource. Copy its assigned HTTPS URL.
   It will resemble `https://<assigned-name>.azurestaticapps.net`.

If using the portal-generated GitHub build:

| Field | Value |
| --- | --- |
| Application source directory / app location | `frontend` (or `/frontend` in the wizard) |
| API location | **Empty**; `backend` is not an Azure Functions project |
| Output location | `dist` |
| App build command | `npm run build` |

The supplied prebuilt-upload workflow instead uses `frontend/dist` as app location
and an empty output location because it runs the build first. Do not mix these
two sets of paths. [Build configuration](https://learn.microsoft.com/en-us/azure/static-web-apps/build-configuration).

### B. Configure GitHub without publishing secrets

Use the repository where the intended MeetPilot source is committed. This
workspace contains substantial existing uncommitted work; a GitHub run deploys
the selected committed revision, not these local files. Review that revision
deliberately. Do not use a blanket commit/push just to publish this guide.

1. In the Azure Static Web App, open **Manage deployment token** (wording may
   vary). Save it privately in GitHub **Settings → Secrets and variables →
   Actions → Secrets** as `AZURE_STATIC_WEB_APPS_API_TOKEN`. Never commit it.
2. Add these **Actions repository variables**:

   | Variable | Value |
   | --- | --- |
   | `VITE_CLERK_PUBLISHABLE_KEY` | Actual Clerk publishable key from the same instance the backend will verify |
   | `VITE_API_BASE_URL` | Actual API HTTPS origin, without path or trailing slash |

3. For a frontend-only preview, temporarily use the Static Web App's own HTTPS
   origin as `VITE_API_BASE_URL`. There is no API there: workspace requests will
   fail, as expected. This avoids embedding `localhost` in a public build. Do
   not invite users to process recordings until a real API is connected.
4. Configure the hosted origin in the existing Clerk instance using its current
   domain/redirect settings. A test instance can serve a personal preview; use
   the appropriate production instance and its requirements for a later release.
5. Copy `deploy/azure/frontend.manual.yml` to
   `.github/workflows/azure-frontend.yml` in the intended deployment revision.
6. Commit the reviewed frontend/config/workflow files to your GitHub repository.
   Select the repository's default branch in **Actions → Deploy MeetPilot
   frontend to Azure → Run workflow**.

`VITE_*` values are public and embedded at build time. Changing Azure runtime
settings after a build does not rewrite those assets: update the build variables
and deploy again. The only Clerk value allowed here is its publishable key.
Keep Clerk secret keys, database passwords, OpenAI keys and Vexa tokens on servers.

GitHub Actions has its own account allowances. Check the repository's Actions
billing/limits; the Azure student credit is not a promise of unlimited GitHub
runner time. This template runs only on manual dispatch to reduce unnecessary builds.

### C. Verify the hosted frontend

- Check Actions succeeded and the site loads over HTTPS.
- Open `/app`, `/workspace`, `/privacy`, `/terms`, `/recording-policy`, and the actual
  callback paths used by the app; refresh and verify SPA loading. Protected
  routes still require sign-in; do not bypass auth to make a preview look complete.
- Verify `/api/v1/workspaces` does not return `index.html` when there is no backend.
- Verify generated JavaScript requests the configured hosted origin, not localhost.
- Inspect the browser console for Clerk/configuration failures and check layout
  on desktop/mobile. This local preparation has not verified hosted behavior.

## 5. Prepare a small private backend pilot

Do this after confirming balance, region, exact quote and a limited test schedule.
There is no production Azure backend manifest in this preparation. The current
development Compose must not be deployed unchanged.

### Preferred initial architecture

Keep the frontend on Static Web Apps. Start with **one suitable x86-64 Linux VM**
for a scheduled backend experiment, using private container networking and durable
volumes. This most closely matches the working Vexa/shared-file architecture and
avoids immediately buying several separate managed services.

The existing deployment plan suggests **4–8 vCPUs / 16 GiB RAM** as a benchmark
candidate, with more memory if measurements require it. That is not an established
minimum or a one-call performance guarantee. Confirm quota before selecting a
size; do not assume the student subscription allows it. CPU inference can be slow.
An ARM VM requires image/native-dependency checks, especially for pinned Vexa;
do not substitute it just because it appears in the free offer.

Start with a fresh test database and short synthetic/uploaded audio. Test one
processing job at a time before a live bot. Use an operational one-meeting limit
until server-side admission/quota controls exist; a worker concurrency setting
alone is not a complete SaaS quota policy.

### Work required before exposing the backend

1. Create a separate deployment Compose/configuration with no development source
   bind mounts, strong independent database/Redis secrets, persistent Redis,
   resource limits and log rotation. Preserve the pinned Vexa Lite integration.
2. Publish only HTTPS API traffic through a reverse proxy. Permit SSH only from
   your administrative IP. Container port publishing must also be restricted;
   an OS firewall alone is not sufficient justification for public DB ports.
   Keep PostgreSQL, Redis, Ollama, Vexa admin/terminal and noVNC private.
3. Set server-side Clerk issuer/JWKS/secrets, exact frontend CORS origin, stable
   encryption/JWT secrets and OAuth callback URLs. Validate authenticated `wss://`
   connections and microphone/audio playback through the proxy.
4. Fix the two documented access findings: meeting-origin Pilot reads inherit
   the starter's scope, and Clerk verification lacks the authorized-origin policy.
   Use synthetic data in staging until fixed and verified. Merely disabling a
   visible button does not close a reachable backend path.
   [Access audit](Workspace_Access_Audit.md).
5. Choose inference explicitly. Keep Ollama for inexpensive development experiments
   only if the rented host can carry it. Direct OpenAI costs a separate budget.
   Do not enable a paid fallback. Do not claim full semantic retrieval when the
   embedding service is absent or indexes have not been migrated.
6. Review fresh/existing database initialization (`app.database.bootstrap` plus
   Alembic), back up first, then run release migrations once. Test actual PostgreSQL
   and pgvector, not just SQLite adapters. Never point staging migrations at the
   developer's existing database by accident.
7. Back up application and engine databases, recordings and necessary private
   configuration. Restore a test backup before storing real recordings. Verify
   recording access, membership removal, retention/deletion and a worker restart.
8. After the hosted API passes its checks, change `VITE_API_BASE_URL` to that
   origin and rebuild/redeploy the frontend. Update Google/Zoom callbacks in each
   provider's console as well as in the backend.

### Optional eligible managed PostgreSQL

If the subscription confirms the introductory meters, use the **Burstable B1ms**
configuration matching the allowance, 32 GB storage, and backup settings within
allowance. Avoid HA/read replicas and automatic storage growth for this bounded
experiment; monitor space and plan a controlled change if necessary. Check the
current creation wizard carefully: its default may be a paid larger size.

Allowlist `vector` under `azure.extensions`, then enable it in the application
database with `CREATE EXTENSION IF NOT EXISTS vector;`. Use a private connection
or narrow firewall rule and TLS (`sslmode=require` at minimum, with certificate
verification preferred for production). Do not enable "all Azure services" access
as a substitute for deciding which hosts may connect.

The app currently uses PostgreSQL 16 and vector(768). Preserve vector dimensions
and provenance. Vexa currently has its own PostgreSQL 17 instance; migrating
either database is a separate verified step, and both do not get independent
unlimited free allowances. Free Azure SQL/Cosmos DB are not drop-in replacements.
[pgvector setup](https://learn.microsoft.com/en-us/azure/postgresql/extensions/how-to-use-pgvector).

## 6. Azure-hosted GPT requires additional work

`backend/app/services/openai_transport.py` deliberately posts to
`https://api.openai.com/v1/`. An Azure key cannot simply replace the current key.
Azure credit cannot pay the direct OpenAI account's bill.

To spend eligible Azure credit on Azure-hosted GPT instead, first inspect the
subscription's actual supported resource/model/region quota. Then implement
dedicated text and embedding provider adapters with server-controlled endpoints,
Azure authentication, deployment/model configuration and existing response/evidence
validation. Keep provider/model/dimension namespaces and reindex embeddings through
the controlled migration process. Do not weaken the existing fixed-origin transport
to accept arbitrary browser-supplied URLs.

The student page advertises Azure OpenAI access, but an advertisement does not
verify that your particular model has usable quota in a permitted region. This
guide creates no Foundry resource and chooses no model. Check the model's actual
metered price and deploy only after it fits the shared credit budget.
[Azure model quotas](https://learn.microsoft.com/en-us/azure/ai-foundry/openai/quotas-limits),
[provider migration](Cloud_AI.md).

Azure Speech free allowances are also not automatically wired into our current
Whisper/Piper paths. A provider adapter, quality tests and actual account allowance
checks are needed before proposing that substitution.

## 7. End every compute session deliberately

Finish or cancel meeting/processing work, verify persisted data, then use the
Azure VM **Stop** action and confirm **Stopped (deallocated)**. Shutting down the
guest OS can leave billable allocation. Deallocation stops VM compute charges;
retained disks, applicable IPs and other resources may still cost money.
[VM billing states](https://learn.microsoft.com/en-us/azure/virtual-machines/states-billing),
[retained resource costs](https://learn.microsoft.com/en-us/azure/virtual-machines/cost-optimization-plan-to-manage-costs).

An Azure auto-shutdown schedule is a useful backup after confirming its behavior,
not a guarantee that an active meeting can safely stop. Plan sessions to finish
before it. A deletion also needs explicit data handling: export/verify backups,
identify every resource in the experiment group, then remove only what is no
longer needed. Keep the separately grouped website if you still want it online.

## 8. Deployment status and next gate

- **Prepared locally:** frontend routing config, manual deployment template and
  this account-specific planning guide.
- **Source checked:** frontend types pass; the JSON/YAML configurations and workflow
  JavaScript parse. A clean, isolated frontend install from the lockfile and
  production build passed after lifting Windows sandbox file-access restrictions.
  The Azure routing configuration is present in the built output. No development
  credentials were copied into the isolated build. This is compilation/packaging
  evidence, not a Clerk login, hosted routing or backend integration test.
- **Not verified:** Azure balance/expiry/free meters/quota; any deployed URL;
  PostgreSQL migration on Azure; real bot, speech, provider cost or restore behavior.
- **Public SaaS release still needs:** the access fixes, usage accounting/admission,
  reliable recovery, backups and retention/deletion, and completed policy/provider
  disclosures already tracked in [Feature_Roadmap.md](Feature_Roadmap.md).

The next useful account action is to inspect the student subscription's balance,
expiry and free-service meters, then create the **Free frontend preview**. Add
compute only after its complete quote and scheduled usage fit the remaining credit.
