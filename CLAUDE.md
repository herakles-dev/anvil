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
└── example/                # Application workspace
    ├── applications/       # One subdirectory per company/program
    │   └── {company-slug}/
    │       ├── meta.json           # Company metadata (name, role, deadline, URL)
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

Ask these questions (skip any the user already answered):

**About them:**
1. What's your full name and contact info (email, location, GitHub/portfolio URL)?
2. What's your professional background in 2-3 sentences?
3. What are your top 3-5 projects? For each: name, what it does, tech stack, key metrics (LOC, users, tests, performance numbers).
4. Do you have a resume already? If so, where is it? (path on disk, or they can paste the content)
5. What quantifiable claims can you make? (years of experience, languages known, systems built, users served, etc.)

**About the application:**
1. What company/program are you applying to?
2. What's the role/position title?
3. What's the deadline?
4. What's the application URL?
5. Does the application have a portal with specific form fields? If so, what are they? (exact field labels and any word/character limits)
6. What makes you specifically suited for this role?
7. What's your narrative arc — why are you applying to THIS, NOW?

### Phase 2: Build the Evidence Base

Create `example/evidence/` files from the user's answers. These populate the searchable evidence sidebar (Ctrl+E in the UI).

**Files to create:**

**`example/evidence/platform-stats.md`** — Quantifiable claims:
```markdown
# Platform Stats
## Verified numbers for applications

## [Category 1]

| Metric | Value | Source |
|--------|-------|--------|
| [metric] | [value] | [how to verify] |
```

**`example/evidence/project-portfolio.md`** — Detailed project profiles:
```markdown
# Project Portfolio

## [Project Name]

**What it is:** [description]
**Tech stack:** [languages, frameworks]
**Scale:** [LOC, users, requests/day]
**Key achievement:** [most impressive metric]
**Relevance:** [why this matters for the application]
```

**`example/evidence/career-profile.md`** — Professional narrative:
```markdown
# Career Profile

## Background
[Professional summary — who they are, what they do]

## Key Stats
| Claim | Number |
|-------|--------|
| Years of experience | X |
| Languages | X |
| Production systems | X |

## Narrative Arc
[Why they're applying to this, now — the story that connects their past to this opportunity]
```

Create additional evidence files if the user has domain-specific research, publications, open-source contributions, etc.

### Phase 3: Build the Company Directory

Create `example/applications/{slug}/` with real content:

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

**`cover_letter.md`** — Write a REAL draft, not a template:
```markdown
# Cover Letter — [Company] [Role]

Dear [Hiring Team / specific name if known],

[Opening: specific hook — why THIS company, why NOW, what caught their attention]

[Middle: 2-3 paragraphs connecting their strongest projects/experience to the role requirements. Use specific numbers from the evidence base.]

[Closing: enthusiasm, availability, call to action]

Best regards,
[Name]
[email] | [portfolio]
```

**`talking_points.md`** — Interview prep with real content:
```markdown
# Talking Points — [Company]

## Why This Company
- [Specific reasons from research]
- [How their values/mission align]
- [What they know about the team/product]

## Why This Role
- [How their experience maps to requirements]
- [What they'd work on in the first 90 days]
- [Unique angle they bring]

## Key Numbers to Drop
| Claim | Number | Context |
|-------|--------|---------|
| [metric] | [value] | [when to use this in conversation] |

## Likely Questions + Prepared Answers
- "Tell me about [X]" → [concise answer with specific example]
- "How would you approach [Y]?" → [framework + example]
- "What's your experience with [Z]?" → [honest answer + bridge to strength]

## Questions to Ask Them
- [Thoughtful question about the role]
- [Question about team/culture]
- [Question about technical challenges]
```

**`project_highlights.md`** — Their best projects, tailored to this role:
```markdown
# Project Highlights — [Company]

## [Project 1 — most relevant to this role]
**What it is:** [description]
**Tech stack:** [specifics]
**Key metrics:** [numbers]
**Why it matters for [Company]:** [explicit connection to role]
**Code sample:** [if applicable, link or path]

## [Project 2]
...
```

### Phase 4: Configure Form Fields (if applicable)

If the application portal has specific form fields:

1. **Create constellation files** — one `.md` per field:
   ```
   example/applications/{slug}/constellation/
   ├── why_interested.md      (empty — user writes first draft in browser)
   ├── relevant_experience.md
   └── ...
   ```

2. **Update `fields.json`** — configure each field with:
   - `label`: Exact text from the portal
   - `guidance`: What to write about (based on what the field is really asking)
   - `reviewer_wants`: What evaluators look for (research the program if possible)
   - `word_min` / `word_max`: Limits from the portal (estimate if not specified)
   - `order`: Display order matching the portal
   - `track`: Usually `"both"`

3. **Add cheat sheets** — map the user's evidence to each field:
   ```json
   "cheatsheet": {
     "why_interested": {
       "what_to_hit": ["Their specific narrative arc points"],
       "evidence_to_cite": ["evidence/career-profile.md", "evidence/project-portfolio.md"],
       "tips": ["Specific writing advice for THIS field"]
     }
   }
   ```

   This is the highest-value part. For each field, think: "What from this person's background is the strongest answer?" and map it.

### Phase 5: Build the Resume

Create `example/applications/{slug}/resume/resume.html`:

- If the user has an existing resume, read it and convert to clean HTML
- If not, build one from the evidence base
- Use clean, printable CSS (the UI has a PDF export via headless Chromium)
- Structure: Contact → Summary → Experience → Projects → Education → Skills

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
  .skills { display: flex; flex-wrap: wrap; gap: 6px; }
  .skill { background: #f0f0f0; padding: 2px 8px; border-radius: 3px;
           font-size: 11px; }
</style>
</head>
<body>
  <h1>[Full Name]</h1>
  <div class="contact">[email] · [location] · [github/portfolio URL]</div>
  <!-- Build from evidence base -->
</body>
</html>
```

### Phase 6: Docker & Launch

1. Update `docker-compose.yml` volume mounts if evidence lives outside `example/`:
   ```yaml
   volumes:
     - ./example/applications:/data/applications
     - ./example/evidence:/data/evidence:ro
     # Add custom paths if needed:
     # - /path/to/your/research:/data/evidence:ro
   ```

2. Rebuild and launch:
   ```bash
   docker compose up -d --build
   ```

3. Verify:
   ```bash
   curl -s http://localhost:8135/api/companies | python3 -m json.tool
   ```

4. Tell the user: "Open http://localhost:8135 — your workspace is ready. Select [company] to start writing."

### Phase 7: Ongoing Assistance

After setup, the user will draft in the browser and come back to the CLI for help. Common requests:

**"Refine my [field] draft":**
```bash
# Read what they wrote
cat example/applications/{slug}/constellation/{field}.md
# Edit the file with improved prose, keeping their voice and staying within word limits
```

**"Process my review notes":**
```bash
curl -s http://localhost:8135/api/notes/export?company={slug} | python3 -m json.tool
# Read each note, apply the requested changes to the corresponding .md files
```

**"How's my progress?":**
```bash
curl -s http://localhost:8135/api/fellowship/both/progress | python3 -m json.tool
```

**"Add another company":**
Repeat Phases 3-6 for the new company. Evidence files are shared across all companies.

---

## API Reference

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/api/companies` | List all companies with docs and status |
| GET | `/api/document/{slug}/{doc}` | Render document as HTML |
| PUT | `/api/document/{slug}/{doc}` | Save document content |
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
| GET | `/api/guide/{slug}` | Submission guide section |

## Editing Rules

- **Read files before editing** — never assume contents
- **Write to the same .md files** the UI reads from
- **Don't touch the SQLite DB directly** — use the API
- **Constellation fields are for the user to first-draft** — only refine after they mark as `human_written`
- **Back up before bulk changes** — Anvil auto-backs-up on every UI save, but CLI edits bypass this
