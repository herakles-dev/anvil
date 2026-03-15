# Anvil — Application Writing Forge

> A guided writing environment for high-stakes applications, designed for use alongside a CLI-based LLM.

## How Anvil Works

Anvil is a **browser UI** that reads and writes **plain markdown files on disk**. You draft in the browser with evidence at your fingertips, word counters, and field guides. Your CLI-based LLM (Claude Code, Cursor, etc.) reads and refines those same files.

```
You write in browser  ──→  .md files on disk  ←──  LLM refines via CLI
                              ↕                          │
                        Anvil reads/writes          watchdog detects
                              ↕                          │
                        WebSocket pushes  ←──────────────┘
                        changes to browser instantly
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
├── requirements.txt        # Flask, markdown, gunicorn, flask-sock, watchdog
└── example/                # Application workspace
    ├── applications/       # One subdirectory per company/program
    │   └── {company-slug}/
    │       ├── meta.json           # Company metadata
    │       ├── cover_letter.md     # Cover letter draft
    │       ├── talking_points.md   # Interview prep + key numbers
    │       ├── project_highlights.md # Key projects with metrics
    │       ├── constellation/      # Form fields → triggers guided mode
    │       │   ├── {field_id}.md   # One file per portal form field
    │       │   └── ...
    │       └── resume/
    │           └── resume.html     # HTML resume (editable + PDF export)
    └── evidence/           # Research/evidence files for the sidebar
        ├── platform-stats.md       # Quantifiable claims table
        ├── project-portfolio.md    # Project details + metrics
        └── ...
```

## Quick Start

```bash
docker compose up -d
# Open http://localhost:8135
```

---

## Full Setup Guide for LLM Assistants

**This section is for you, the LLM.** When a user asks you to set up Anvil, follow this protocol. Don't just create skeleton files — interview the user and build real, substantive content.

### Phase 1: Interview the User

Ask these questions conversationally (skip any the user already answered). Don't dump all questions at once — group them naturally.

**About them (for evidence base + resume):**
1. What's your full name and contact info? (email, location, GitHub/portfolio URL, LinkedIn)
2. What's your professional background in 2-3 sentences?
3. What are your top 3-5 projects? For each: name, what it does, tech stack, key metrics (LOC, users, tests, performance numbers, scale).
4. Do you have an existing resume? If yes: where is it on disk? (You'll read it and convert to HTML.) If they can paste content, that works too.
5. What quantifiable claims can you make? (years of experience, languages known, systems built, users served, contributions made, etc.)
6. Education? (degrees, schools, relevant coursework, certifications)
7. Publications, talks, blog posts, or open-source contributions?
8. Languages spoken? Awards or recognition?

**About the application (for company directory + form fields):**
1. What company/program are you applying to? (If multiple, handle one at a time — evidence is shared.)
2. What's the role/position title?
3. What's the deadline?
4. What's the application URL? **If they give you a URL, use web search or web fetch to look up the actual application form fields, word limits, and requirements.** Don't guess — research the portal.
5. Does the application have a portal with specific form fields? If so, what are they? (Exact field labels and any word/character limits. If they don't know, research it for them.)
6. What makes you specifically suited for this role?
7. What's your narrative arc — why are you applying to THIS, NOW? (The story that connects past → present → this opportunity.)

### Phase 2: Build the Evidence Base

Create `example/evidence/` files from the user's answers. These populate the searchable evidence sidebar (Ctrl+E in the UI). The more evidence you build here, the more useful the sidebar is during drafting.

**If the user has an existing resume on disk**, read it first — it's a goldmine of structured data (dates, titles, achievements, metrics) that seeds everything else.

**If the user has a GitHub profile**, consider scanning their pinned repos for project metrics (stars, forks, LOC, languages).

**Files to create:**

**`example/evidence/platform-stats.md`** — All quantifiable claims in table format:
```markdown
# Verified Stats
## Numbers you can cite in applications

## Professional

| Metric | Value | Source |
|--------|-------|--------|
| Years of experience | [X] | Resume |
| Languages proficient in | [list] | GitHub/projects |
| Production systems built | [X] | Project list |

## [Project Name]

| Metric | Value | Source |
|--------|-------|--------|
| Lines of code | [X] | cloc or estimate |
| Test count | [X] | Test suite |
| Users/scale | [X] | Analytics |
```

**`example/evidence/project-portfolio.md`** — Detailed project profiles:
```markdown
# Project Portfolio

## [Project Name]

**What it is:** [description]
**Tech stack:** [languages, frameworks, infrastructure]
**Scale:** [LOC, users, requests/day, data volume]
**Key achievement:** [most impressive metric or outcome]
**Relevance:** [why this matters for applications]
**Code samples:** [paths to notable files, or repo URLs]
**Demo/live URL:** [if applicable]
```
Create one section per project. Include ALL projects from the interview, not just the top ones.

**`example/evidence/career-profile.md`** — Professional narrative + career arc:
```markdown
# Career Profile

## Summary
[Who they are professionally in 2-3 sentences]

## Career Arc
[The chronological story: where they started → key transitions → where they are now]

## Narrative Arc
[Why they're applying to this specific thing now — the emotional/intellectual journey]

## Education & Credentials
- [Degree] — [School], [Year]
- [Certification] — [Issuer], [Year]

## Key Differentiators
- [What makes them unusual/memorable as a candidate]
- [Unconventional background angles]
- [Unique perspectives they bring]
```

**Additional evidence files** — create these if the user has the material:
- `open-source-contributions.md` — PRs, repos, community involvement
- `publications-and-talks.md` — papers, conference talks, blog posts
- `domain-research.md` — if they have domain-specific knowledge (e.g., security research, ML papers read, industry analysis)

### Phase 3: Build the Company Directory

Create `example/applications/{slug}/` with **real content** — not templates with `[placeholder]` brackets. Use the evidence base to write actual drafts.

**`meta.json`:**
```json
{
  "company": "Company Name",
  "role": "Position Title",
  "status": "PREPARING",
  "salary_range": "",
  "deadline": "2026-07-01",
  "apply_url": "https://...",
  "notes": ""
}
```

**`cover_letter.md`** — Write a REAL first draft using the evidence base:
- Opening: specific hook connecting their background to THIS role
- Middle: 2-3 paragraphs mapping their strongest projects to the role's requirements, with specific numbers
- Closing: enthusiasm + availability
- Sign off with their name and contact info

**`talking_points.md`** — Real interview prep:
- "Why This Company" with researched reasons (look up the company if needed)
- "Why This Role" with experience mapping
- Key numbers table (which stats to drop in conversation and when)
- 5+ likely interview questions with prepared answers using their actual experience
- 3+ questions for them to ask the interviewer

**`project_highlights.md`** — Top 3-5 projects, **tailored to this role**:
- Emphasize different aspects of the same projects depending on what the role values
- Include specific metrics from the evidence base
- Explain WHY each project matters for THIS company

### Phase 4: Configure Form Fields (if applicable)

If the application portal has specific form fields:

1. **Research the portal** — if the user gave you an application URL, look up the exact form fields, word limits, and any instructions. Don't guess.

2. **Create constellation files** — one `.md` per field, **left empty** for the user to first-draft in the browser:
   ```
   example/applications/{slug}/constellation/
   ├── {field_id}.md    (empty — user writes first draft in browser)
   └── ...
   ```
   Use snake_case filenames matching the field topic (e.g., `why_interested.md`, `relevant_experience.md`).

3. **Update `fields.json`** with the actual portal fields:
   - `label`: Exact question text from the portal
   - `guidance`: What to write about (interpret what the field is really asking)
   - `reviewer_wants`: What evaluators look for (research the program/company)
   - `word_min` / `word_max`: From the portal (estimate 75-150 if not specified)
   - `order`: Match the portal's field order
   - `track`: Usually `"both"` unless the program has separate tracks

4. **Build cheat sheets** — this is the highest-value part. For EACH field, map the user's specific evidence:
   ```json
   "cheatsheet": {
     "why_interested": {
       "what_to_hit": ["Their specific narrative arc points from Phase 1"],
       "evidence_to_cite": ["evidence/career-profile.md (Narrative Arc section)",
                            "evidence/project-portfolio.md (Project X)"],
       "tips": ["Specific writing advice for THIS person and THIS field"]
     }
   }
   ```
   Think: "What from this person's background is the STRONGEST answer to this question?" and map it explicitly.

### Phase 5: Build the Resume

Create `example/applications/{slug}/resume/resume.html`.

**If the user has an existing resume:**
- Read it (whatever format — .html, .pdf text, .docx, pasted text)
- Convert to clean, printable HTML
- Preserve their content, improve the formatting
- Tailor the summary/objective to this specific role

**If building from scratch**, use the evidence base:
- Structure: Name/Contact → Summary → Experience → Projects → Education → Skills
- Use clean, printable CSS (will be rendered in an iframe and exported to PDF)
- Keep font sizes readable (12-13px body)
- Single-column layout, max 800px width

```html
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>[Name] — Resume</title>
<style>
  body { font-family: 'Helvetica Neue', Arial, sans-serif; max-width: 800px;
         margin: 40px auto; padding: 0 20px; color: #333; line-height: 1.5;
         font-size: 13px; }
  h1 { font-size: 22px; margin-bottom: 2px; }
  h2 { font-size: 14px; color: #555; border-bottom: 1px solid #ddd;
       padding-bottom: 3px; margin-top: 18px; text-transform: uppercase;
       letter-spacing: 0.5px; }
  .contact { color: #666; font-size: 12px; margin-bottom: 16px; }
  .entry { margin-bottom: 12px; }
  .entry-header { display: flex; justify-content: space-between; }
  .entry-title { font-weight: 600; }
  .entry-date { color: #888; font-size: 12px; }
  ul { margin: 3px 0 0 18px; }
  li { margin: 2px 0; }
  .skills { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 4px; }
  .skill { background: #f0f0f0; padding: 2px 8px; border-radius: 3px; font-size: 11px; }
</style>
</head>
<body>
  <!-- Build from evidence base — real content, not placeholders -->
</body>
</html>
```

### Phase 6: Docker & Launch

1. **Remove the example company** if the user doesn't want it:
   ```bash
   rm -rf example/applications/acme-corp
   ```

2. Update `docker-compose.yml` if evidence lives outside `example/`:
   ```yaml
   volumes:
     - ./example/applications:/data/applications
     - ./example/evidence:/data/evidence:ro
     # Or mount external directories:
     # - /path/to/your/research:/data/evidence:ro
   ```

3. Rebuild and launch:
   ```bash
   docker compose up -d --build
   ```

4. Verify everything loaded:
   ```bash
   # Check companies appeared
   curl -s http://localhost:8135/api/companies | python3 -c "
   import json,sys
   for c in json.load(sys.stdin):
       print(f'{c[\"slug\"]}: {len(c[\"documents\"])} docs, constellation={c[\"has_constellation\"]}')
   "

   # Check evidence loaded
   curl -s http://localhost:8135/api/evidence | python3 -c "
   import json,sys
   d=json.load(sys.stdin)
   print(f'{len(d)} evidence sources, {sum(len(s[\"sections\"]) for s in d)} total sections')
   "

   # Check fields configured
   curl -s http://localhost:8135/api/fellowship/both/fields | python3 -c "
   import json,sys
   d=json.load(sys.stdin)
   print(f'{len(d)} form fields configured')
   "
   ```

5. Tell the user: **"Open http://localhost:8135 — your workspace is ready. Select [company] to start writing. The constellation fields are empty for you to first-draft in the browser. When you're done with a draft, mark it as 'human_written' and come back to the CLI for refinement."**

### Phase 7: Ongoing Assistance

After setup, the user will draft in the browser and come back to the CLI for help:

**"Refine my [field] draft":**
```bash
cat example/applications/{slug}/constellation/{field}.md
```
Read it, then edit the file with improved prose. Keep their voice. Stay within word limits. Reference their evidence for stronger claims.

**"Process my review notes":**
```bash
curl -s http://localhost:8135/api/notes/export?company={slug} | python3 -m json.tool
```
Read each note, find the corresponding .md file, apply the change.

**"How's my progress?":**
```bash
curl -s http://localhost:8135/api/fellowship/both/progress | python3 -m json.tool
```

**"Add another company":**
Repeat Phases 3-6 for the new company. Evidence files in `example/evidence/` are shared across all companies — only create company-specific materials in the company directory.

**"Help me tailor my cover letter for [company]":**
Read the evidence base + the company's meta.json, then write/refine the cover letter with specific connections to that company's mission and role requirements.

**"Check my word counts":**
```bash
for f in example/applications/{slug}/constellation/*.md; do
  wc -w "$f"
done
```

### Live Collaboration Protocol

When you edit files via CLI, the browser updates instantly:

1. **Edit the .md file** -- write, refine, fix word counts as usual
2. **The browser highlights your changes** -- orange borders on modified blocks, purple on new blocks
3. **If the user has unsaved work** -- they see a conflict banner instead of auto-reload
4. **History tracks everything** -- Ctrl+H shows both browser and CLI edits with timestamps

**Live collaboration is now built-in.** When you edit a .md file via CLI:
- The browser auto-reloads if the user has no unsaved changes (orange highlight on changed blocks)
- If the user IS editing (unsaved changes), a banner appears: "Updated externally -- Reload / Dismiss"
- The user can press Ctrl+H to see the full edit history with source attribution
- Every save (browser or CLI) creates a backup accessible via Ctrl+H then Versions

API endpoints for collaboration:
- `GET /api/document/{slug}/{doc}/check` -- poll mtime (fallback when WebSocket is down)
- `GET /api/document/{slug}/{doc}/history` -- see recent edits with source attribution
- `GET /api/document/{slug}/{doc}/versions` -- list available backup versions
- `POST /api/document/{slug}/{doc}/restore` -- restore a backup (creates a new backup first)

The WebSocket connection to `/api/ws` sends JSON messages:
```json
{"type": "file_changed", "slug": "acme-corp", "document": "cover_letter"}
```

---

## Troubleshooting Guide

### Docker Issues

**Container won't start — port 8135 already in use:**
```bash
# Find what's using the port
lsof -i :8135
# Either stop that process, or change the port in docker-compose.yml:
# ports: "8200:5000"
```

**`docker compose` command not found:**
- You might have Docker Compose v1 (`docker-compose`) instead of v2 (`docker compose`)
- Try: `docker-compose up -d` (with hyphen)
- Or install Docker Compose v2: https://docs.docker.com/compose/install/

**Build fails on Chromium install:**
- This can happen on ARM/Apple Silicon. Chromium is only needed for PDF export.
- To skip it, remove the Chromium line from `Dockerfile` and the `CHROMIUM_PATH` env var.
- PDF generation will be disabled, but everything else works.

**Container starts but immediately exits:**
```bash
docker compose logs anvil
```
Common causes:
- `fields.json` has a JSON syntax error → validate with `python3 -m json.tool fields.json`
- `app.py` has a syntax error → run `python3 -c "import app"` locally to check
- Volume mount path doesn't exist → `ls` the paths in docker-compose.yml

### UI Issues

**No companies appear in the tab bar:**
- The `applications/` directory must contain at least one subdirectory with a `.md` file
- Check: `ls example/applications/*/` — each company dir needs at least one `.md`
- Verify the volume mount in docker-compose.yml points to the right path

**Company appears but constellation mode doesn't activate:**
- The company directory needs a `constellation/` subdirectory with `.md` files inside
- Check: `ls example/applications/{slug}/constellation/`
- The subdirectory must contain at least one `.md` file
- Constellation field filenames must be snake_case and match keys in `fields.json`

**Evidence sidebar is empty (Ctrl+E shows nothing):**
- Check `EVIDENCE_DIR` environment variable is set in docker-compose.yml
- Check the volume mount points to a directory with `.md` files
- Verify from inside the container: `docker exec anvil ls /data/evidence/`
- Evidence files must be `.md` format with `## Heading` delimiters for sections

**Stats cards don't appear in evidence sidebar:**
- Stats are parsed specifically from a file named `platform-stats.md`
- The file must contain markdown tables with `| Metric | Value | Source |` format
- Table separator rows (`|---|---|---|`) are skipped automatically

**Word counter shows wrong/no count:**
- Word count is calculated on the client side from textarea content
- It splits on whitespace — HTML comments and markdown syntax are counted as words
- If writing in the browser, the counter updates live on every keystroke

**Changes made via CLI don't appear in the browser:**
- Changes should appear instantly via WebSocket. Check that the WebSocket indicator (green dot in top-right) is connected.
- If the dot is gray, the connection is down -- changes will appear on next page reload (F5).
- If editing constellation fields via CLI, the browser will show the new content when you click the field.

**WebSocket dot is gray (disconnected):**
- The container may have restarted -- WebSocket auto-reconnects every 3 seconds
- If persistently gray, check container logs: `docker compose logs anvil`
- Flask-sock requires single-worker gunicorn (already configured in Dockerfile)

**Edit/note buttons don't appear on paragraphs:**
- Hover over a paragraph — buttons appear on the right side
- If buttons still don't appear, check browser console for JS errors (F12 → Console)

### Form Field Issues

**Field appears in sidebar but shows no guidance/word counter:**
- The field's `id` (filename without `.md`) must match a key in `fields.json` under `"fields"`
- Example: `constellation/why_interested.md` → needs `"why_interested"` in fields.json
- Check for typos in the filename or the JSON key

**Cheat sheet panel is empty when clicking "Tips":**
- The field needs a matching entry in the `"cheatsheet"` section of `fields.json`
- The cheatsheet key must match the field key exactly

**fields.json changes don't take effect:**
- The file is read at container startup. After editing, restart:
  ```bash
  docker compose restart anvil
  ```
- Validate JSON syntax first: `python3 -m json.tool fields.json`

### Resume Issues

**Resume tab doesn't appear:**
- The company directory needs a `resume/` subdirectory with an `.html` file
- Check: `ls example/applications/{slug}/resume/`

**PDF generation fails:**
- Chromium must be installed in the container (it is by default in the Dockerfile)
- Check: `docker exec anvil which chromium` — should return `/usr/bin/chromium`
- If running on ARM/Apple Silicon, Chromium may not be available — see Docker Issues above
- Check container logs: `docker compose logs anvil | grep -i pdf`

**Resume preview is blank in the editor:**
- The HTML file must be valid HTML. Check for unclosed tags.
- The iframe preview debounces at 500ms — wait a moment after typing.

### Export Issues

**Export modal shows "[Not yet written]" for all fields:**
- The constellation `.md` files are empty — you need to write content in the browser first
- Or write content via CLI: `echo "Your text" > example/applications/{slug}/constellation/{field}.md`

**"Email to self" fails:**
- SMTP must be configured in docker-compose.yml environment variables
- Required: `SMTP_HOST`, `SMTP_USER`, `SMTP_PASS`
- Optional: `SMTP_PORT` (defaults to 587), `EMAIL_TO` (defaults to SMTP_USER)
- Test SMTP separately to rule out credential issues

### Data & Backup Issues

**Where is the database?**
- SQLite file at the path specified by `DB_PATH` (default: `data/anvil.db`)
- Contains review notes, field status, and edit history -- NOT document content (that's in .md files)

**Where are backups?**
- Every save (browser or CLI) creates a timestamped backup in `BACKUP_DIR`
- Format: `{slug}__{document}__{YYYYMMDD_HHMMSS}.md`
- View and restore backups from the browser via Ctrl+H (History panel) then Versions

**How to reset everything:**
```bash
# Delete database (notes + status tracking)
rm -f data/anvil.db
# Delete backups
rm -rf data/backups/*
# Restart container to recreate tables
docker compose restart anvil
```

### Common Mistakes

| Mistake | Fix |
|---------|-----|
| Editing files while container is stopped | Start container first — or edits are fine, just won't show until container runs |
| Putting `.txt` files in evidence dir | Must be `.md` files |
| Using spaces in company directory names | Use kebab-case: `acme-corp` not `Acme Corp` |
| Forgetting to rebuild after Dockerfile changes | `docker compose up -d --build` |
| JSON syntax error in fields.json | Validate: `python3 -m json.tool fields.json` |
| Constellation filenames don't match fields.json keys | `why_interested.md` → key must be `"why_interested"` |
| Mounting a file instead of a directory | Volume mounts must point to directories, not files |

---

## API Reference

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/api/companies` | List all companies with docs and status |
| GET | `/api/document/{slug}/{doc}` | Render document as HTML (includes `external_edit` flag) |
| PUT | `/api/document/{slug}/{doc}` | Save document content |
| PUT | `/api/document/{slug}/{doc}/block/{idx}` | Save single paragraph |
| GET | `/api/document/{slug}/constellation/{field}` | Get constellation field + config |
| PUT | `/api/document/{slug}/constellation/{field}` | Save constellation field |
| GET | `/api/evidence` | All evidence sources with sections |
| GET | `/api/evidence/search?q=` | Search evidence by substring |
| GET | `/api/evidence/stats` | Stats from markdown tables as JSON |
| GET | `/api/fellowship/{track}/fields` | Form field config |
| GET | `/api/fellowship/{track}/progress` | Completion summary |
| GET | `/api/field-status/{slug}/{doc}` | Single field status |
| PUT | `/api/field-status/{slug}/{doc}` | Update field status |
| GET | `/api/export/{slug}/{track}/plain-text` | Export fields for copy-paste |
| POST | `/api/export/{slug}/{track}/email` | Email export to self |
| GET | `/api/cheatsheet/{field}` | Per-field writing tips |
| GET | `/api/notes/{slug}` | All notes for a company |
| POST | `/api/notes` | Create a review note |
| PUT | `/api/notes/{id}` | Update a note |
| DELETE | `/api/notes/{id}` | Delete a note |
| GET | `/api/notes/export` | Export pending notes as JSON |
| GET | `/api/resume/{slug}` | Resume HTML for iframe |
| GET | `/api/resume/{slug}/pdf` | Download resume PDF |
| GET | `/api/resume-html/{slug}` | Raw resume HTML for editing |
| PUT | `/api/resume-html/{slug}` | Save resume HTML |
| POST | `/api/resume-html/{slug}/pdf` | Generate PDF via Chromium |
| GET | `/api/resume-import/{slug}` | Import resume from fellowship dir |
| GET | `/api/guide/{slug}` | Submission guide section |
| GET | `/api/ws` | WebSocket -- live file change notifications |
| GET | `/api/document/{slug}/{doc}/history` | Edit history (last 20 entries) |
| GET | `/api/document/{slug}/{doc}/versions` | List backup files for restore |
| POST | `/api/document/{slug}/{doc}/restore` | Restore from backup version |
| GET | `/api/document/{slug}/{doc}/check` | Mtime check + external edit flag |

## Editing Rules

- **Read files before editing** -- never assume contents
- **Write to the same .md files** the UI reads from
- **Don't touch the SQLite DB directly** -- use the API for notes and status
- **Constellation fields are for the user to first-draft** -- only refine after they mark as `human_written`
- **Respect word limits** -- check `fields.json` for min/max before editing constellation fields
- **Keep the user's voice** -- when refining, improve clarity and strength without changing their personality
- **CLI edits are now detected automatically** -- the file watcher (watchdog) notifies the browser via WebSocket. You don't need to tell the user to refresh.
- **Edit history tracks everything** -- every save (browser, CLI, or restore) is logged with word count deltas. Users can see the timeline via Ctrl+H.
- **Undo is available** -- users can Ctrl+Z to undo saves (max 30 entries in the undo stack). Your CLI edits are also undoable from the browser.
