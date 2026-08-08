# Design System & Aesthetics — MeetPilot AI

## 1. Design Vision & Philosophy
MeetPilot AI embodies a **modern, sleek, obsidian-themed AI SaaS interface**. It emphasizes high visual contrast, subtle radial gradient lighting, glassmorphism borders, ultra-crisp typography, and smooth micro-animations.

---

## 2. Color Palette & Tokens

### 2.1 Backgrounds & Neutral Surfaces
| Token | Hex | Role |
| :--- | :--- | :--- |
| **`bg-canvas`** | `#09090B` | Deep obsidian background for application canvas and main viewports |
| **`bg-panel`** | `#111113` | Primary container surface for cards, modals, and header bars |
| **`bg-card`** | `#121217` | Elevated card surface with subtle ambient glow |
| **`bg-input`** | `#181822` | Form input backgrounds and secondary interactive pill containers |
| **`border-subtle`**| `#27272A` | Clean, low-contrast structural dividers |
| **`border-active`**| `#2D2D3B` | Interactive borders with hover transitions to purple |

### 2.2 Brand & Semantic Accents
| Token | Hex | Role |
| :--- | :--- | :--- |
| **`brand-primary`**| `#8B5CF6` | Vivid violet accent for CTAs, active badges, and focus rings |
| **`brand-gradient`**| `linear-gradient(135deg, #8B5CF6, #7C3AED)` | Premium glowing buttons and badge fills |
| **`status-success`**| `#10B981` / `#34D399` | Emerald status pills, live sync indicators, and completed tasks |
| **`status-warning`**| `#F59E0B` | High-priority task flags and pending transcription state |
| **`status-error`**| `#F43F5E` / `#FB7185` | Error alerts and failed background job indicators |

---

## 3. Typography & Font Hierarchy

- **Primary Font Family**: `Plus Jakarta Sans`, `Inter`, system-ui, -apple-system, sans-serif.
- **Monospace Code/Data**: `JetBrains Mono`, `ui-monospace`, `monospace` for timestamps, keys, and status labels.

### Type Scale
- **Display Hero (`h1`)**: `text-5xl` to `text-7xl` font-extrabold, tracking-tight, leading-[1.05].
- **Section Headers (`h2`, `h3`)**: `text-xl` to `text-3xl` font-extrabold with gradient text accents.
- **Body Text**: `text-sm` (14px) / `text-xs` (12px) text-slate-300 with high readability.
- **Micro Badges**: `text-[10px]` / `text-[11px]` font-bold font-mono tracking-wide.

---

## 4. UI Components & Micro-Interactions

1. **Logo & Brand Pill**:
   - MeetPilot Robot Icon with a 1px gradient border (`from-[#8B5CF6] to-[#A78BFA]`), smooth `hover:scale-110` micro-rotation, and glowing live indicator.
2. **Social Auth Grid**:
   - Symmetrical 2-column grid layout with row 1 spanning 100% for Google and row 2 split 50/50 for GitHub and Slack with pure white icon fills (`filter: brightness(0) invert(1)`).
3. **Live Sync Radar Pill**:
   - Real-time animated emerald ping effect (`animate-ping`) alongside monospace user status.
4. **Interactive Meeting Chat & Citations**:
   - Speech bubble chat interface with clickable violet timestamp pills (`01:24s`) that automatically scroll and highlight the transcript audio segment.
