# Cloud AI: development defaults and the GPT migration

**Product decision, 8 October 2026:** MeetPilot's final product is hosted SaaS.
Ollama is the inexpensive development provider. Production text intelligence will
use OpenAI GPT APIs; customers use the web dashboard without running models.

## What is implemented

- `AI_PROVIDER=ollama|openai` selects the existing shared generation interface.
  The OpenAI adapter uses the Responses API, explicit server model selection,
  JSON schema output and the existing Pydantic/evidence validation. Summaries,
  meeting/workspace answers and AI-based task parsing share this boundary.
  [Text generation](https://developers.openai.com/api/docs/guides/text),
  [Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs).
- `EMBEDDING_PROVIDER=ollama|openai` is independent. OpenAI `text-embedding-3-small`
  and `text-embedding-3-large` support the dimensions parameter; the adapter
  requests **768**, matching the current PostgreSQL schema. It validates vector
  count, index ordering, dimensions and finite numeric values.
  [Embedding dimensions](https://developers.openai.com/api/docs/guides/embeddings).
- Keys are server-only masked settings. Requests use the official fixed origin
  without redirects. No request is made merely by importing or selecting a
  provider. Missing credentials/models fail explicitly; there is no automatic
  paid fallback from Ollama.
- Responses use `store=false`. This does **not** mean zero retention of every
  category of provider data or compliance certification. Review applicable
  provider controls and disclose remote processing to customers before rollout.
  [OpenAI data controls](https://developers.openai.com/api/docs/guides/your-data).
- Provider/model/dimension provenance separates cloud vectors from existing
  local indexes. Old Ollama model labels are preserved for compatibility.

## Current development settings

```dotenv
AI_PROVIDER=ollama
OLLAMA_CHAT_MODEL=qwen3:4b-instruct
EMBEDDING_PROVIDER=ollama
OLLAMA_EMBEDDING_MODEL=nomic-embed-text-v2-moe
OPENAI_API_KEY=
OPENAI_CHAT_MODEL=
```

Keep these while developing without an API budget. The development `.env` is read
from the backend working directory; injected environment variables take priority.
Docker injects `backend/.env` into the API and both worker services. Changes require
restarting all processes that use the providers.

## Later: switch chat first

When a funded OpenAI project is available, configure the following **on the server**:

```dotenv
AI_PROVIDER=openai
OPENAI_API_KEY=<server-secret-from-your-OpenAI-project>
OPENAI_CHAT_MODEL=<Responses-API-model-available-to-that-project>
EMBEDDING_PROVIDER=ollama
```

The angle-bracket values are placeholders, not runnable credentials or model IDs.
No chat model is chosen automatically: select and benchmark a currently available
model for multilingual evidence accuracy, cost and latency. A chat-only switch
does not require embedding reindexing. Do not paste this key into frontend `.env`,
`VITE_*`, a browser settings form, a log, or source control.

The adapter deliberately omits Ollama options and model-specific temperature or
reasoning parameters. Output tokens are bounded by `AIConfig.max_tokens` (currently
2048). Incomplete/refused/empty responses are rejected. Evaluate the chosen model's
output/reasoning budget before changing those limits; schema validity does not
prove factual correctness.

GPT API use is not a free hosting tier. Check the actual project limits and current
[API pricing](https://developers.openai.com/api/docs/pricing) when budgeting. Usage
accounting, workspace caps and concurrency admission still need implementation
before exposing cloud inference to public signup.

## Later: migrate retrieval embeddings

1. Back up the application database and schedule a controlled migration.
2. Pause source ingestion/reindex jobs, and set the same provider/model in **all**
   API and worker processes:

   ```dotenv
   EMBEDDING_PROVIDER=openai
   OPENAI_EMBEDDING_MODEL=text-embedding-3-small
   OPENAI_API_KEY=<server-secret>
   ```

3. Restart those processes with the new configuration. Vector retrieval ignores
   old namespaces; keyword retrieval may still find original authorized text.
   During reindexing, vector coverage is incomplete: do not claim full retrieval.
4. Run the resumable batch reindex in the configured backend environment:

   ```powershell
   # From backend/, with its dependencies and database available:
   python -m app.database.reindex_embeddings
   # Or, in an already configured running development container:
   docker compose exec -T backend python -m app.database.reindex_embeddings
   ```

5. Verify all transcript/document rows have the active namespace, such as
   `openai:text-embedding-3-small:768`. Run grounded retrieval/permission tests on
   English, Bengali, Hindi and mixed-language examples, then resume ingestion.

Equal vector dimensions do **not** make two embedding models interchangeable.
The script commits completed batches and can resume after failure. Reverting the
provider requires reindexing again: old vector values are not retained in a second
column. Restoring a backup is another controlled rollback option. Reindexing makes
API requests and can cost money; it is never run automatically by this change.

## Hosting boundaries and unfinished production work

The adapter change does not deploy the product. Current Compose still starts and
depends on Ollama, uses development database addresses/source mounts, and is not a
production manifest. Prepare a production deployment without the Ollama service
once both text and embeddings use cloud providers. Whisper/Piper can run on
MeetPilot's hosted speech workers; the `local` transcription configuration describes
the engine implementation, not customer-device processing.

Before public signup implement cost/usage accounting and limits, redaction policies,
shared private objects, durable task/bot recovery, secret rotation, production auth,
retention/deletion and staging verification. Speech API/Realtime adapters are a
later evaluation, not implemented by this text provider switch.

All current provider tests use mocked HTTP/fixtures. No live paid API request,
deployment, model download or full Docker startup is needed to verify these
contracts. See [the complete feature roadmap](Feature_Roadmap.md).
