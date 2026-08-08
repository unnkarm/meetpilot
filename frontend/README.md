# 🎙️ MeetPilot AI

> **Turn every meeting into searchable knowledge and actionable tasks.**

MeetPilot AI is an AI-powered meeting intelligence platform that transforms conversations into structured, actionable workspaces. Upload a meeting recording or transcript, and MeetPilot automatically generates summaries, extracts action items, identifies decisions, and lets you chat with your meetings using AI.

---

## ✨ Features

- 🎤 **AI Transcription**
  - Convert meeting recordings into searchable transcripts.
  - Speaker segmentation and timestamps.

- 📝 **Smart Summaries**
  - Generate concise summaries with key discussion points.
  - Highlight decisions and outcomes.

- ✅ **Action Item Extraction**
  - Detect tasks discussed during meetings.
  - Assign owners and deadlines automatically.

- 💬 **AI Chat**
  - Ask questions about any meeting.
  - Example:
    - *Who is responsible for deployment?*
    - *What decisions were made?*

- 🔍 **Semantic Search**
  - Search across all meetings using natural language.

- 📂 **Meeting Workspace**
  - Store transcripts, summaries, tasks, and AI conversations in one place.

---

## 🚀 Why MeetPilot AI?

Meetings often end with forgotten tasks, scattered notes, and unclear ownership.

MeetPilot AI ensures every meeting becomes a structured source of truth by automatically organizing conversations into summaries, decisions, and actionable next steps.

---

## 🛠️ Tech Stack

### Frontend
- Next.js
- React
- Tailwind CSS
- TypeScript
- shadcn/ui
- Framer Motion

### Backend
- FastAPI
- PostgreSQL
- Redis

### AI
- Whisper / Deepgram
- OpenAI API
- LangChain / LangGraph
- pgvector

### Deployment
- Docker
- Vercel
- Railway / Render

---

## 📦 MVP Features

- [x] User Authentication
- [x] Meeting Upload
- [x] AI Transcription
- [x] AI Summary
- [x] Action Item Extraction
- [x] Meeting Dashboard
- [x] AI Chat with Meeting
- [x] Semantic Search
- [x] Export Meeting Notes

---

## 📸 Screens

- Landing Page
- Dashboard
- Meeting Details
- AI Chat
- Tasks
- Settings

*(Screenshots coming soon.)*

---

## 📂 Project Structure

```
meetpilot-ai/
│
├── client/             # Next.js Frontend
├── server/             # FastAPI Backend
├── ai/                 # AI Pipelines
├── database/           # PostgreSQL Schema
├── docs/
├── public/
└── README.md
```

---

## 🔄 Workflow

```text
Upload Meeting
        │
        ▼
AI Transcription
        │
        ▼
Smart Summary
        │
        ▼
Extract Tasks & Decisions
        │
        ▼
Store Meeting Knowledge
        │
        ▼
Chat with Your Meeting
```

---

## 🎯 Future Roadmap

- Live Meeting Recording
- Google Meet Integration
- Zoom Integration
- Microsoft Teams Integration
- Calendar Sync
- Slack Notifications
- Team Workspaces
- Analytics Dashboard
- Mobile Application

---

## 🤝 Contributing

Contributions, issues, and feature requests are welcome.

Feel free to fork the repository and submit a pull request.

---

## 📄 License

This project is licensed under the MIT License.

---

## 💡 Vision

MeetPilot AI isn't just another meeting summarizer.

Our vision is to build an AI-powered workspace where every conversation becomes organized knowledge, every decision is preserved, and every action moves teams forward.

---

<p align="center">
Built with ❤️ using AI, FastAPI, Next.js, and modern web technologies.
</p>
