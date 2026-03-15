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
    ├── pipeline.md         # Multi-company pipeline tracker
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
        ├── career-profile.md       # Professional narrative + arc
        └── ...
```

## Quick Start

```bash
docker compose up -d
# Open http://localhost:8135
```

---

## Full Setup Guide for LLM Assistants

**This section is for you, the LLM.** When a user asks you to set up Anvil, follow this protocol phase by phase. Don't just create skeleton files — interview the user, research their targets, and build real, substantive content.

### Phase 0: Environment & Capability Check

Before doing anything, verify the environment and assess your own tool capabilities.

**Prerequisites:**
```bash
# Check Docker is running
docker info > /dev/null 2>&1 && echo "Docker: OK" || echo "Docker: NOT RUNNING"

# Check disk space (need ~500MB for image + data)
df -h . | tail -1

# Check port 8135 is available
lsof -i :8135 2>/dev/null && echo "Port 8135: IN USE" || echo "Port 8135: available"
```

**Clone and prepare** (skip if already cloned):
```bash
git clone https://github.com/herakles-dev/anvil.git
cd anvil
```

**Tool capability self-assessment** — check what you can do and adapt accordingly:

| Capability | How to check | If available | If unavailable |
|------------|-------------|--------------|----------------|
| Web search | Try `WebSearch` tool | Research companies, find job postings, look up salary data | Ask user to provide company info, job posting text |
| Web fetch | Try `WebFetch` tool | Read application portals, parse form fields, fetch job descriptions | Ask user to paste portal content or describe fields |
| Gmail MCP | Check for `mcp__gmail__*` tools | Draft and send emails with attachments | Use SMTP config in docker-compose.yml, or manual export |
| File read | Always available | Read resumes (PDF, HTML, text) | — |
| PDF read | Try reading a `.pdf` file | Import PDF resumes directly | Ask user to paste resume content or provide HTML/text version |

**Graceful degradation:** Every feature works without web tools — it just requires more manual input from the user. Tell the user upfront what you can and can't do:

> "I can read files, edit code, and manage the container. [I can / I can't] search the web or fetch URLs. For company research, [I'll look it up / you'll need to tell me about the company and paste any relevant job posting text]."

### Phase 1: Import & Interview

Start by gathering existing materials, then fill gaps with an interview.

**Step 1: Import existing materials**

Ask: "Do you have an existing resume? (file path, URL, or paste it)"
- If yes: read it in whatever format (PDF, HTML, .txt, .docx text, pasted content)
- Extract: work history with dates/titles, projects with metrics, education, skills, publications
- Use as seed data for all evidence files — don't make the user repeat what's already written

Ask: "Do you have a GitHub or portfolio URL?"
- If yes and you can fetch URLs: scan their profile for repos, stars, languages, recent activity
- If yes but you can't fetch: ask them to list their top 3-5 repos with descriptions
- Auto-populate project-portfolio.md entries from discovered repos

**Step 2: Interview for gaps**

Ask these questions conversationally — skip anything already covered by imported materials. Don't dump all questions at once — group them naturally.

**About them (for evidence base + resume):**
1. What's your full name and contact info? (email, location, GitHub/portfolio URL, LinkedIn)
2. What's your professional background in 2-3 sentences?
3. What are your top 3-5 projects? For each: name, what it does, tech stack, key metrics (LOC, users, tests, performance numbers, scale).
4. What quantifiable claims can you make? (years of experience, languages known, systems built, users served, contributions made, etc.)
5. Education? (degrees, schools, relevant coursework, certifications)
6. Publications, talks, blog posts, or open-source contributions?
7. Languages spoken? Awards or recognition?

**About the application (for company directory + form fields):**
1. What company/program are you applying to? (If multiple, handle one at a time — evidence is shared.)
2. What's the role/position title?
3. What's the deadline?
4. What's the application URL? **If they give you a URL, use web search or web fetch to look up the actual application form fields, word limits, and requirements.** Don't guess — research the portal.
5. Does the application have a portal with specific form fields? If so, what are they? (Exact field labels and any word/character limits. If they don't know, research it for them.)
6. What makes you specifically suited for this role?
7. What's your narrative arc — why are you applying to THIS, NOW? (The story that connects past → present → this opportunity.)

### Phase 2: Opportunity Research

If the user provides a target company/program, research it thoroughly. If they say "help me figure out where to apply," help them explore options.

**If the user provides a job posting URL:**
1. Fetch and parse the posting (or ask the user to paste it if you can't fetch):
   - Required qualifications, preferred qualifications, responsibilities
   - Keywords and phrases that appear repeatedly
   - Team/department context
   - Compensation if listed
2. Gap analysis — map the user's evidence to each requirement:
   ```
   STRONG FIT:  Requirement X → user has Project Y (evidence: platform-stats.md)
   PARTIAL FIT: Requirement Z → user has related experience in Project W
   GAP:         Requirement Q → no direct evidence (suggest how to address)
   ```
3. Identify the top 3-5 keywords/themes to weave into all application materials

**Company research** (via web search if available, otherwise ask the user):
- Mission, size, funding stage, and recent news
- Tech stack and engineering culture (from blog posts, talks, open-source repos)
- What the team that's hiring works on specifically
- Glassdoor/Blind ratings and interview process (if available)
- Salary data from levels.fyi or similar (if available)

**Application portal analysis:**
- Identify portal type: online form with fields, document upload, email submission, or hybrid
- If online form: extract field labels, word/character limits, required vs optional fields
- Auto-configure `fields.json` from the discovered fields (Phase 5)
- Note any required attachments (resume, transcripts, references, etc.)

**Build meta.json** with researched data — see Phase 4 for format.

**Generate a match score** and share it with the user:
> "Based on what I've gathered, you're a strong fit for this role. Your DataForge project maps directly to their ML infrastructure focus (STRONG), your anomaly detection work aligns with their evaluation research (STRONG), and while you don't have publications, your open-source contributions demonstrate research-community engagement (PARTIAL). I'd estimate 75-80% match."

**If the user says "help me find opportunities":**
1. Ask: target role type, preferred company size, location/remote preference, salary expectations
2. If you can web search: find 5-10 matching openings
3. Present each with: company name, role, deadline, estimated fit based on their evidence
4. Let them pick which to pursue — then run the full research protocol for each

### Phase 3: Build the Evidence Base

Create `example/evidence/` files from imported materials + interview answers. These populate the searchable evidence sidebar (Ctrl+E in the UI). The more evidence you build here, the more useful the sidebar is during drafting.

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

### Phase 4: Build the Company Directory

Create `example/applications/{slug}/` with **real content** — not templates with `[placeholder]` brackets. Use the evidence base and research from Phase 2 to write actual drafts.

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

### Phase 5: Configure Form Fields (if applicable)

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

### Phase 6: Build the Resume

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

### Phase 7: Docker & Launch

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

### Phase 8: Ongoing Writing Assistance

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
Repeat Phases 2-7 for the new company. Evidence files in `example/evidence/` are shared across all companies — only create company-specific materials in the company directory.

**"Help me tailor my cover letter for [company]":**
Read the evidence base + the company's meta.json, then write/refine the cover letter with specific connections to that company's mission and role requirements.

**"Check my word counts":**
```bash
for f in example/applications/{slug}/constellation/*.md; do
  wc -w "$f"
done
```

### Phase 9: Pipeline Management

When managing multiple applications, use `example/pipeline.md` as the central tracker.

**Pipeline file format:**

```markdown
# Application Pipeline

## Active Applications

| Company | Role | Status | Deadline | Priority | Next Action |
|---------|------|--------|----------|----------|-------------|
| Acme Corp | Research Fellow | DRAFTING | 2026-07-01 | HIGH | Refine cover letter |
| Other Co | ML Engineer | RESEARCHING | 2026-08-15 | MEDIUM | Research portal fields |

## Status Legend

| Status | Meaning |
|--------|---------|
| RESEARCHING | Gathering info about the company and role |
| PREPARING | Building evidence base and company directory |
| DRAFTING | Writing application materials |
| REVIEWING | Refining drafts, processing review notes |
| SUBMITTED | Application sent — awaiting response |
| INTERVIEWING | In interview process |
| DECIDED | Final decision received |

## Decision Log

| Date | Company | Decision | Notes |
|------|---------|----------|-------|
```

**Priority scoring** — when asked "what should I work on?", rank by:
1. **Deadline proximity** — anything within 7 days is urgent
2. **Fit score** — higher-fit opportunities deserve more polish
3. **Effort remaining** — fewer incomplete fields = closer to done

**Daily brief protocol** (when the user asks "what's next?" or "what should I work on?"):
1. Check `pipeline.md` for deadlines within 7 days → **warn immediately**
2. Check field statuses across all companies for `human_written` fields → offer refinement
3. Check for pending review notes → process them
4. Check for incomplete constellation fields → suggest which to draft next
5. Show overall pipeline summary:
   ```bash
   # Quick pipeline status
   echo "=== Pipeline Status ==="
   cat example/pipeline.md | head -20

   # Per-company progress
   for company in example/applications/*/; do
     slug=$(basename "$company")
     echo "--- $slug ---"
     curl -s "http://localhost:8135/api/fellowship/both/progress" 2>/dev/null || echo "  (container not running)"
   done
   ```

**Adding a new company** to the pipeline:
1. Run Phases 2-7 for the new company (evidence is shared)
2. Add a row to `pipeline.md`
3. Add an entry to the Decision Log

### Phase 10: Submission & Follow-Up

When the user is ready to submit an application:

**Pre-submission checklist:**
```
[ ] All constellation fields at "final" status
[ ] Word counts within limits for every field
[ ] Cover letter tailored and proofread
[ ] Resume current and formatted correctly
[ ] meta.json deadline has not passed
[ ] Export preview reviewed (Ctrl+Shift+X in the browser)
[ ] All review notes processed (none pending)
```

Run the checklist programmatically:
```bash
slug="company-slug"

# Check field statuses
echo "=== Field Statuses ==="
curl -s "http://localhost:8135/api/fellowship/both/progress" | python3 -m json.tool

# Check word counts against limits
echo "=== Word Counts ==="
for f in example/applications/$slug/constellation/*.md; do
  field=$(basename "$f" .md)
  words=$(wc -w < "$f")
  echo "$field: $words words"
done

# Check for pending notes
echo "=== Pending Notes ==="
curl -s "http://localhost:8135/api/notes/export?company=$slug" | python3 -c "
import json,sys
notes=json.load(sys.stdin)
if notes: print(f'{len(notes)} notes still pending')
else: print('All clear — no pending notes')
"

# Check deadline
echo "=== Deadline Check ==="
python3 -c "
import json, datetime
meta=json.load(open('example/applications/$slug/meta.json'))
deadline=datetime.date.fromisoformat(meta['deadline'])
today=datetime.date.today()
days=(deadline-today).days
print(f'Deadline: {meta[\"deadline\"]} ({days} days away)')
if days < 0: print('WARNING: DEADLINE HAS PASSED')
elif days < 3: print('WARNING: Less than 3 days remaining')
elif days < 7: print('NOTE: Less than 1 week remaining')
"
```

**Export for portal submission:**

Option 1 — Copy-paste from export modal:
1. Open the browser, select the company
2. Press Ctrl+Shift+X to open the export modal
3. Copy each field's text and paste into the application portal

Option 2 — API export:
```bash
# Get all fields as plain text for copy-paste
curl -s "http://localhost:8135/api/export/$slug/both/plain-text" | python3 -m json.tool
```

Option 3 — Email submission (if SMTP configured):
```bash
# Send via the API
curl -X POST "http://localhost:8135/api/export/$slug/both/email"
```

Option 4 — Gmail MCP (if available):
```
# Draft an email with the application materials
1. Export plain text via API
2. Use mcp__gmail__draft_email to create the draft
3. Attach resume PDF: curl -o resume.pdf "http://localhost:8135/api/resume/$slug/pdf"
4. User reviews draft in Gmail → sends manually
```

**Post-submission:**
1. Update `pipeline.md`: change status to `SUBMITTED`, update Next Action
2. Update `meta.json`: set `"status": "SUBMITTED"`
3. Add entry to Decision Log with submission date

**Follow-up protocol:**
- If no response after 1-2 weeks: draft a polite follow-up email
  ```
  Subject: Following Up — [Role Title] Application

  Dear [Team/Name],

  I submitted my application for the [Role] position on [date] and wanted to
  confirm it was received. I remain very enthusiastic about the opportunity
  and am happy to provide any additional information.

  Best regards,
  [Name]
  ```
- If interview scheduled: update pipeline status to `INTERVIEWING`, review talking_points.md
- If accepted/rejected: update pipeline status to `DECIDED`, log in Decision Log

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

## Pipeline File Format

The pipeline tracker lives at `example/pipeline.md` and is the central dashboard for multi-company applications.

**Required sections:**

1. **Active Applications table** — one row per company with: Company, Role, Status, Deadline, Priority, Next Action
2. **Status Legend** — defines the 7 statuses (RESEARCHING → DECIDED)
3. **Decision Log** — append-only log of key decisions with dates

**Statuses flow in order:**
```
RESEARCHING → PREPARING → DRAFTING → REVIEWING → SUBMITTED → INTERVIEWING → DECIDED
```

**Priority values:** HIGH, MEDIUM, LOW — based on deadline proximity, fit score, and strategic importance.

**Update rules:**
- Update pipeline.md whenever a status changes
- Add to Decision Log whenever you start or complete a major milestone
- The LLM should read pipeline.md at the start of every session to understand current state

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
