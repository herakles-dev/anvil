# Anvil

**Application writing forge** — a guided writing environment for fellowships, grants, and job applications, designed for use alongside a CLI-based LLM.

You draft in the browser with your evidence at your fingertips. Your LLM refines the same markdown files from the terminal. Status tracking keeps you honest about what's human-written vs AI-refined.

![Tests](https://github.com/herakles-dev/anvil/actions/workflows/test.yml/badge.svg)
![Stack](https://img.shields.io/badge/stack-Flask%20%2B%20Vanilla%20JS%20%2B%20SQLite-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Docker](https://img.shields.io/badge/runs%20in-Docker-2496ED)

## Features

- **Block-level editing** — hover any paragraph to edit inline or leave review notes
- **Constellation mode** — guided form-field writing with word counters, tips, and field guides (auto-activates when a `constellation/` directory exists)
- **Evidence sidebar** — search your research files while drafting (Ctrl+E)
- **Status tracking** — `not_started → first_draft → human_written → ai_refined → final` per field
- **Resume editor** — split-pane HTML editor with live preview + PDF export via headless Chromium
- **Export** — copy-paste-ready text for application portals, or email to yourself
- **CLI-friendly** — all data is plain markdown on disk + a REST API for automation
- **Auto-backups** — every save creates a timestamped backup
- **Live collaboration** — CLI edits appear instantly in the browser via WebSocket
- **Change highlighting** — orange for CLI-modified blocks, purple for new blocks (auto-fades)
- **Edit history** — timeline of all edits with source attribution (Ctrl+H)
- **Undo/Redo** — per-save undo stack with version restore (Ctrl+Z / Ctrl+Shift+Z)
- **Version browser** — one-click restore from any backup
- **Conflict protection** — external edit banner when you have unsaved changes

## Quick Start

```bash
git clone https://github.com/herakles-dev/anvil.git
cd anvil
docker compose up -d
# Open http://localhost:8135
```

The example application (`acme-corp`) loads automatically so you can explore the UI.

## Setting Up Your Own Applications

### Option 1: Use your CLI-based LLM (recommended)

Paste this prompt into Claude Code, Cursor, or any CLI-based LLM running in the `anvil/` directory. It will interview you and build everything out:

````
I want to set up Anvil — the application writing forge. Here's what to do:

1. Clone the repo and read the setup guide:
   ```
   git clone https://github.com/herakles-dev/anvil.git
   cd anvil
   ```
2. Read CLAUDE.md (especially "Full Setup Guide for LLM Assistants") and follow the setup protocol.
3. Interview me to gather what you need, then build out my complete workspace:
   - Evidence base from my background and projects
   - Company directories with real application materials
   - Form fields configured for the specific portal I'm applying to
   - Resume HTML built from my experience
   - Cheat sheets with my actual evidence mapped to each field
4. Start the container when ready:
   ```
   docker compose up -d --build
   ```

Here's my starting context:
- I'm applying to: [COMPANY/PROGRAM — or "multiple, let's discuss"]
- My background: [2-3 sentences about your career/expertise]
- My key projects: [list your top 3-5 projects]
- Deadline: [date, or "not sure yet"]
````

The LLM will ask follow-up questions about your experience, research the application requirements, then build out your complete workspace — not just skeleton files.

### Option 2: Manual setup

<details>
<summary>Click to expand manual setup instructions</summary>

1. **Create a company directory:**
   ```
   example/applications/your-company/
   ├── meta.json
   ├── cover_letter.md
   ├── talking_points.md
   └── project_highlights.md
   ```

2. **Add form fields** (optional — activates guided mode):
   ```
   example/applications/your-company/constellation/
   ├── why_interested.md
   ├── relevant_background.md
   └── anything_else.md
   ```
   Then edit `fields.json` to configure labels, word limits, and tips for each field.

3. **Add evidence files** (optional — populates the sidebar):
   ```
   example/evidence/
   ├── platform-stats.md
   ├── project-portfolio.md
   └── research-notes.md
   ```

4. **Add a resume** (optional — enables the HTML editor + PDF export):
   ```
   example/applications/your-company/resume/
   └── resume.html
   ```

5. **Rebuild:**
   ```bash
   docker compose up -d --build
   ```

</details>

## How the CLI Workflow Works

```
┌─────────────────────┐     ┌──────────────┐     ┌─────────────────────┐
│   You (browser)     │◀═══▶│  .md files   │◀────│   LLM (terminal)    │
│                     │ ws  │  on disk     │     │                     │
│ - Draft text        │     │              │     │ - Refine prose      │
│ - Leave notes       │     │ Single source│     │ - Fix word counts   │
│ - Track status      │     │ of truth     │     │ - Process notes     │
│ - Search evidence   │     │              │     │ - Research evidence │
└─────────────────────┘     └──────────────┘     └─────────────────────┘
        ▲                          │
        └──── WebSocket push ──────┘
              (instant reload)
```

1. **You** write first drafts in the browser (guided mode shows word targets and tips)
2. Mark fields as `human_written` when your draft is done
3. **Your LLM** reads the files, refines the prose, fixes word counts
4. Changes appear instantly in your browser — CLI-modified blocks highlight in orange, new blocks in purple
5. If you have unsaved changes when the CLI edits a file, a conflict banner lets you choose what to keep
6. Review the changes, mark as `ai_refined`
7. Final review → mark as `final` → export for the portal

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+S` | Save current document |
| `Ctrl+E` | Toggle evidence sidebar |
| `Ctrl+Shift+C` | Toggle cheat sheet / tips |
| `Ctrl+Shift+X` | Open export modal |
| `Ctrl+H` | Toggle edit history panel |
| `Ctrl+Z` | Undo last save (when not in editor) |
| `Ctrl+Shift+Z` | Redo |
| `Ctrl+Enter` | Save inline block edit |
| `Esc` | Cancel inline edit |

## Configuration

### `fields.json`

All form field configuration lives here — no code changes needed:

```json
{
  "fields": {
    "your_field_id": {
      "label": "What the portal asks",
      "guidance": "What to write about",
      "reviewer_wants": "What reviewers look for",
      "word_min": 100,
      "word_max": 200,
      "order": 1,
      "track": "both"
    }
  },
  "cheatsheet": {
    "your_field_id": {
      "what_to_hit": ["Key point 1", "Key point 2"],
      "evidence_to_cite": ["evidence/file.md"],
      "tips": ["Writing tip"]
    }
  }
}
```

### `meta.json`

Per-company metadata shown in the UI:

```json
{
  "company": "Company Name",
  "role": "Position Title",
  "status": "PREPARING",
  "salary_range": "$X-$Y",
  "deadline": "2026-07-01",
  "apply_url": "https://example.com/apply"
}
```

### Environment Variables

See `.env.example` for all options. Key ones:

| Variable | Purpose | Default |
|----------|---------|---------|
| `APPLICATIONS_DIR` | Where company directories live | `/data/applications` |
| `EVIDENCE_DIR` | Research files for the sidebar | (empty) |
| `CHROMIUM_PATH` | For resume PDF generation | `/usr/bin/chromium` |
| `SMTP_HOST` | For "email to self" export | (disabled) |

## API

Anvil exposes a REST API for CLI automation. See `CLAUDE.md` for the full reference.

Quick examples:

```bash
# Get all pending review notes as JSON
curl -s http://localhost:8135/api/notes/export | python3 -m json.tool

# Search your evidence
curl -s "http://localhost:8135/api/evidence/search?q=kubernetes" | python3 -m json.tool

# Export all form fields as plain text
curl -s http://localhost:8135/api/export/acme-corp/both/plain-text | python3 -m json.tool

# Check if a file was modified externally
curl -s http://localhost:8135/api/document/acme-corp/cover_letter/check

# Get edit history
curl -s http://localhost:8135/api/document/acme-corp/cover_letter/history

# List backup versions
curl -s http://localhost:8135/api/document/acme-corp/cover_letter/versions
```

## Tech Stack

- **Backend:** Flask 3.1, SQLite, Python 3.11, flask-sock (WebSocket), watchdog (file watcher)
- **Frontend:** Vanilla JS (no framework), CSS custom properties
- **PDF:** Headless Chromium (installed in Docker image)
- **Container:** Docker with gunicorn

No build step. No npm. No webpack. Just files.

## License

MIT
