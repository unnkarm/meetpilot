# MeetPilot AI — Frontend

The frontend for **MeetPilot AI**, an AI-powered meeting intelligence platform that turns conversations into summaries, decisions, actionable tasks, and searchable team knowledge.

## ✨ Features

* 📊 Meeting dashboard
* 🎙️ Meeting recording & uploads
* 📝 AI-generated summaries & transcripts
* ✅ Action-item & task management
* 📋 Kanban board
* ⚖️ Decision tracking
* 💬 AI meeting chat
* 🔎 Semantic search
* 👥 Team & workspace management
* 🔗 Integrations
* 🔔 Notifications
* ⚙️ Settings

## 🛠️ Tech Stack

* React
* TypeScript
* Vite
* Tailwind CSS
* SWR
* Clerk

## 🚀 Getting Started

### Install

```bash
npm install
```

### Environment

Create a `.env` file:

```env
VITE_API_URL=http://localhost:8000
```

Add any required Clerk environment variables as well.

### Run

```bash
npm run dev
```

The frontend will be available at:

```text
http://localhost:5173
```

## 📁 Structure

```text
frontend/
├── src/
│   ├── components/
│   ├── pages/
│   ├── services/
│   ├── data/
│   └── types.ts
├── public/
├── package.json
└── vite.config.ts
```

## 🔗 Backend

The frontend communicates with the **MeetPilot AI FastAPI backend** for authentication, meetings, AI processing, tasks, search, analytics, and integrations.

---

### 🎙️ MeetPilot AI

**Turn every conversation into progress.**
