# Anvil — Application Writing Forge

> A guided writing environment for high-stakes applications, designed for use alongside a CLI-based LLM.

## How Anvil Works

Anvil is a **browser UI** that reads and writes **plain markdown files on disk**. You draft in the browser with evidence at your fingertips, word counters, and field guides. Your CLI-based LLM (Claude Code, Cursor, etc.) reads and refines those same files.

```
You write in browser  ──→  .md files on disk  ←──  LLM refines via CLI
                              ↕
                        Anvil reads/writes
```

## Project Structure

```
anvil/
├── app.py                  # Flask backend (all routes)
├── fields.json             # Form field config (edit this, not code)
├── static/
│   ├── review.js           # Frontend (vanilla JS)
│   └── style.css           # Dark theme design system
├── templates/
│   └── review.html         # Single-page Jinja2 template
├── docker-compose.yml      # Container config
├── Dockerfile              # Python 3.11 + Chromium
├── requirements.txt        # Flask, markdown, gunicorn
└── example/                # Example application structure
    ├── applications/       # One subdirectory per company
    │   └── acme-corp/
    │       ├── meta.json           # Company metadata
    │       ├── cover_letter.md     # Standard documents
    │       ├── talking_points.md
    │       ├── project_highlights.md
    │       ├── constellation/      # Form fields (triggers guided mode)
    │       │   ├── why_interested.md
    │       │   └── ...
    │       └── resume/
    │           └── resume.html
    └── evidence/           # Research files for the sidebar
        ├── platform-stats.md
        └── project-portfolio.md
```

## Quick Start

```bash
docker compose up -d
# Open http://localhost:8135
```

## Key Concepts

### Companies
Each subdirectory in `applications/` is a "company" (or program, grant, fellowship). It appears as a tab in the UI. Add `meta.json` for name, role, status, deadlines.

### Constellation Fields
If a company has a `constellation/` subdirectory, Anvil activates **guided writing mode**: field-by-field editor with word counters, guidance callouts, cheat sheets, and status tracking. Configure fields in `fields.json`.

### Evidence Sidebar
Mount a directory of `.md` research files. They appear in a searchable sidebar panel (Ctrl+E) so you can reference your evidence while drafting.

### Status Tracking
Each field tracks: `not_started → first_draft → human_written → ai_refined → final`. This supports policies like "applicants must write first drafts themselves."

### Review Notes
Click any paragraph to leave a note (edit, rewrite, question, approve). Notes are stored in SQLite and can be exported as JSON for your CLI tool to process.

## Commands for CLI-Based LLM

When working with an LLM assistant, these patterns are useful:

### Read what's been written
```bash
cat applications/acme-corp/constellation/why_interested.md
```

### Check field status
```bash
curl -s http://localhost:8135/api/field-status/acme-corp/constellation/why_interested | python3 -m json.tool
```

### Get all pending review notes
```bash
curl -s http://localhost:8135/api/notes/export?company=acme-corp | python3 -m json.tool
```

### Export all fields as plain text
```bash
curl -s http://localhost:8135/api/export/acme-corp/both/plain-text | python3 -m json.tool
```

### Search evidence
```bash
curl -s "http://localhost:8135/api/evidence/search?q=machine+learning" | python3 -m json.tool
```

## Editing Rules

- **Read files before editing** — never assume contents
- **Write to the same .md files** the UI reads from
- **Don't touch the SQLite DB directly** — use the API
- **Back up before bulk changes** — Anvil auto-backs-up on every save via the UI

## API Reference

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/api/companies` | List all companies with docs and status |
| GET | `/api/document/{slug}/{doc}` | Render document as HTML |
| PUT | `/api/document/{slug}/{doc}` | Save document content |
| GET | `/api/evidence` | All evidence sources |
| GET | `/api/evidence/search?q=` | Search evidence |
| GET | `/api/evidence/stats` | Stats from markdown tables |
| GET | `/api/fellowship/{track}/fields` | Form field config |
| GET | `/api/fellowship/{track}/progress` | Completion summary |
| GET | `/api/field-status/{slug}/{doc}` | Single field status |
| PUT | `/api/field-status/{slug}/{doc}` | Update field status |
| GET | `/api/export/{slug}/{track}/plain-text` | Export for copy-paste |
| GET | `/api/cheatsheet/{field}` | Per-field writing tips |
| GET | `/api/notes/{slug}` | All notes for a company |
| POST | `/api/notes` | Create a review note |
| GET | `/api/notes/export` | Export pending notes as JSON |
| GET | `/api/resume-html/{slug}` | Resume HTML for editing |
| PUT | `/api/resume-html/{slug}` | Save resume HTML |
| POST | `/api/resume-html/{slug}/pdf` | Generate PDF via Chromium |
