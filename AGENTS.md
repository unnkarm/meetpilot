# MeetPilot repository guidance

## Product direction

MeetPilot's production target is a hosted, multi-tenant web SaaS. Customers use a
browser without installing models, Docker or meeting bots. Local Ollama, Whisper,
Piper and filesystem services are temporary, affordable development choices.
Production text intelligence will use OpenAI GPT APIs through provider interfaces.

Read `docs/Memory.md` and `docs/Feature_Roadmap.md` before changing product scope;
use `docs/Cloud_AI.md` for provider configuration and embedding migrations. Keep
planned, source-implemented and real-deployment-verified features distinct.

## Working constraints

- Preserve workspace/role filters, verified identity boundaries and source evidence
  when adding cloud providers, RAG, media, connectors or tools.
- Official Vexa Lite is the current working meeting engine, restored at the
  founder's request. Preserve the active integration during the SaaS transition.
- Keep credentials on the server and outside source control. Keep development
  inference defaults inexpensive; never activate paid fallbacks automatically.
- Do not start the full Docker/model stack for routine source verification: the
  developer reported overheating. Use isolated tests and compilation; schedule
  live/hosted verification with the developer.
- Preserve existing uncommitted work. Never mark a roadmap feature shipped merely
  because a mock, placeholder or build succeeds.
