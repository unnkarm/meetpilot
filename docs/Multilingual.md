# Multilingual processing

The interface remains in English. Meeting and document content is stored in its original language.

## Meeting language and display

The dashboard's Join Live Meeting, Upload Audio, and Record Audio forms have a **Meeting language** selector. New meetings default to English. Choose Bengali or Hindi for those languages, or Auto-detect / mixed languages when speakers regularly switch languages. The selection is saved per meeting and passed to the Vexa bot, local recording transcription, and Pilot Voice STT; it does not change other workspaces or meetings.

Hindi defaults to **Hinglish** display and Bengali defaults to **Benglish** display: the original words are rendered in Roman letters, with existing English words retained. Use the meeting's **Original script** option to switch back. The preference persists for that meeting. Roman spelling is approximate and is not translation. Transcript timestamps, source quotes in storage, exports, task evidence, and RAG input stay unchanged. Romanization runs in the browser and does not load another AI model.

Existing meetings keep their original-script display and automatic recognition behavior. Migration `d4e5f6a7b8c9` adds the preferences without rewriting old transcripts. Rebuild the frontend and let the backend's normal startup migrations run when restarting Docker after this update.

The configured multilingual Whisper model supports Bengali and Hindi recognition. The live-call and dashboard microphone adapters now enable `multilingual=True` and `task="transcribe"`, with `condition_on_previous_text=False`, matching the recording transcription path. Language detection is repeated for audio windows instead of assuming one language for the entire call. **Mixed / auto** is the intended setting for an English/Bengali/Hindi meeting. A Whisper language token is still a window-level choice; this cannot guarantee perfect recognition of every language change inside a sentence. [faster-whisper implementation](https://raw.githubusercontent.com/SYSTRAN/faster-whisper/v1.2.1/faster_whisper/transcribe.py).

## Mixed-language voice co-pilot

Start Pilot Voice and keep the wake name in English: **Pilot** or **Hey Pilot**. The existing permissive aliases remain supported, including native-script spellings that Whisper may produce for the spoken English name. **Yes sir** remains English. The question can be English, Bengali, Hindi, Hinglish, or Benglish. Short native questions and common Roman spellings are routed without requiring a confident language-detection result for a long sentence.

Examples:

- **“Pilot, আজ আমরা কী সিদ্ধান্ত নিয়েছি?”** — recap this meeting in Bengali.
- **“Pilot, database migration নিয়ে এইমাত্র কী ঠিক হলো?”** — answer from recent meeting speech in Bengali.
- **“Pilot, अभी हमने क्या तय किया?”** — answer from recent meeting speech in Hindi.
- **“Pilot, গত সপ্তাহের budget agreement কী ছিল?”** — search workspace memory, preserving workspace and task visibility rules.
- After a response, **“এটা ছোট করে বলো”** or **“और थोड़ा समझाओ”** — use the same speaker's bounded follow-up conversation.

Answers use the question's language, or its explicit request such as **“in English”**. `QA_LANGUAGE_MODE=question` is the default; another mode retains the existing English-output override. Native scripts are used for synthesis, while the dashboard's original/Roman display preference only changes rendering. English API names, numbers and proper nouns are preserved. Missing evidence or a failed model produces a localized `[Uncertain: ...]` response.

Hindi and Bengali replies carry their language through the private bot playback transport. The bundled English Piper voices remain the English neural voices. Hindi/Bengali use installed **espeak-ng** by default, which is local but less natural. Optional preinstalled Piper models can be configured with `PILOT_PIPER_HI_VOICE_PATH` and `PILOT_PIPER_BN_VOICE_PATH`; each needs its matching `.onnx.json` file. These settings do not download voices. A reply quoting both native scripts switches voices at letter boundaries; shared danda punctuation does not switch a Bengali sentence to Hindi. [espeak-ng supported languages](https://raw.githubusercontent.com/espeak-ng/espeak-ng/master/docs/languages.md).

Explicit decisions and first-person commitments in the three languages are captured immediately from confirmed transcript turns with their original text, speaker and timestamp. Explicit native deadlines and labelled blockers also become source-linked memory. Ambiguous proposals stay in the transcript for later analysis; lightweight rules cannot understand every phrasing. No extra LLM call runs for every live turn. All transcript windows are analyzed during final processing; long-meeting prose summaries are rolled up in bounded batches, while structured decisions/tasks are retained from the original windows. Re-running final analysis preserves captured live decisions, completed tasks and verified assignments rather than deleting them.

Task creation in Bengali/Hindi uses schema-validated local parsing behind the existing manager check. Owner, action and deadline must occur in the request, the owner must resolve uniquely in that workspace, and the original command remains as evidence. Remote meeting speech cannot authorize account actions; use the authenticated microphone or task form. A name heard in Google Meet is still not proof of a MeetPilot account identity.

## Processing path

1. The configured faster-whisper provider runs `task="transcribe"` with the per-meeting language hint (English for new meetings) or automatic language detection when selected. The optional Hugging Face diarization adapter receives the same hint and preserves speaker labels. The local default still labels all speech as Speaker 1; it does not identify distinct speakers.
2. The worker stores original Unicode text, timestamps, speaker labels, meeting language code/name/confidence, optional segment language codes, and a mixed-language flag. Low-confidence detection stays unknown and does not fail the meeting. Lingua detects language from transcript and document text when audio metadata is absent.
3. A versioned multilingual prompt asks for summary, takeaways, next steps, tasks, and decisions in the selected meeting language, falling back to the detected language for automatic or legacy meetings. It keeps API names and proper nouns intact. Due dates use the meeting date only when the spoken reference is unambiguous.
4. Tasks and decisions retain a cited original-language transcript timestamp and source segment. For non-English speech the model must provide an exact source quote; a mismatched quote is rejected.
5. Ollama `nomic-embed-text-v2-moe` produces 768-dimensional vectors from original-language source text. Documents use `search_document: ` and questions use `search_query: ` prefixes. PostgreSQL pgvector and Unicode keyword matching remain the retrieval store. Answers are requested in the question's language and citations point to original sources.

No transcript or knowledge document is translated for storage. The optional legacy Gemini transcription adapter is unchanged and is not part of the default path.

## Models and configuration

Pull `qwen3:4b-instruct` and `nomic-embed-text-v2-moe` into the Ollama instance reachable from the backend and worker. The local ASR default is multilingual faster-whisper `base` on CPU int8. Change `WHISPER_MODEL` to a larger multilingual model if accuracy is inadequate and resources allow. Avoid `.en` Whisper checkpoints for non-English speech.

Defaults live in `backend/app/core/app_config.py`. Override models and behavior in private `backend/.env` with the variables shown in `backend/.env.example`: `OLLAMA_CHAT_MODEL`, `OLLAMA_EMBEDDING_MODEL`, `WHISPER_MODEL`, `TRANSCRIPTION_PROVIDER`, `DEFAULT_LANGUAGE`, `ENABLE_LANGUAGE_DETECTION`, `MULTILINGUAL_TRANSCRIPTION`, `SUMMARY_LANGUAGE_MODE`, `QA_LANGUAGE_MODE`, and `RAG_MAX_COSINE_DISTANCE`. Restart backend and worker after changing them.

The selected multilingual embedding model emits 768 dimensions, matching the existing pgvector columns. Model changes still require re-embedding even when dimensions match:

```powershell
docker compose exec -T backend python -m alembic upgrade head
docker compose exec -T backend python -m app.database.reindex_embeddings
```

The reindex command commits in small batches and can resume after a failure. Existing source text is not changed. Old vectors are excluded from current-model retrieval until reindexed. Models with another dimension require a separate vector-column migration.

## Verification and limits

Text detection tests cover English, Bengali, Hindi, Tamil, Telugu, and Marathi; code-switched Hindi/English, Bengali/English, and Tamil/English text is preserved. A real `nomic-embed-text-v2-moe` 768-vector check gave English-query similarity 0.405 for relevant Bengali text and 0.411 for relevant Hindi text, versus 0.144 and 0.159 for unrelated text. The cosine distance cutoff was raised to 0.70 for these cross-language matches. This is a small smoke test, not a general retrieval benchmark.

The prior `qwen2.5:1.5b` model returned English overviews for Bengali and Hindi examples despite language instructions. `qwen3:4b-instruct` returned Bengali and Hindi overviews; a tightened prompt recovered an explicit Bengali decision in one retest. Short examples still showed extra or duplicate tasks, so model recall and semantic accuracy remain limited and require human review. The 4B model took roughly 70–120 seconds for those short structured examples on this local Ollama host.

The October 8 mixed-language changes were checked with Unicode text fixtures, fake speech/model providers, SQLite persistence and private HTTP/WebSocket playback contracts. No real audio model or application stack was started for these checks. The tests cover language switching settings, native question/follow-up/task routing, source quotes and timestamps, decision revisions, preservation during final analysis, and native-language transport through TTS. They do not establish speech recognition accuracy, neural voice quality or live response latency.

There are no native-language audio fixtures in this repository. Bengali/Hindi/Tamil/Telugu/Marathi ASR quality, multi-speaker diarization, and full audio-to-answer accuracy have not been verified on representative recordings. Scanned PDFs still need OCR before text ingestion; this pipeline only extracts embedded text. Automatic text detection may be uncertain for short utterances and closely related languages. Language coverage depends on the selected Whisper, Lingua, Ollama embedding, and LLM models, and must be measured per language before production use. There is no guarantee of lossless decision extraction or immediate GPT-like conversation on the CPU setup; original transcripts and recordings remain the review sources.

When ready to verify, rebuild the Python service images because the minimum faster-whisper version is now 1.2.1, rebuild the frontend, and restart backend, meeting_bot and celery_worker. Stop and rejoin an existing bot so its language setting applies. In one short **Mixed / auto** meeting, state a decision in each language, then explicitly revise one deadline. Ask Pilot for a recap in Bengali and Hindi and compare the answer's Sources with the transcript before relying on the result.
