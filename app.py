"""
Anvil — Application writing forge.

A guided writing environment for high-stakes applications (fellowships,
grants, jobs). Designed to be used alongside a CLI-based LLM like Claude Code:
you write and review in the browser, the LLM reads and refines the markdown
files on disk.

Part of the Herakles ecosystem.  https://github.com/herakles-dev
"""

import json
import os
import re
import smtplib
import sqlite3
import subprocess
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

from flask import Flask, abort, jsonify, render_template, request, send_file
import markdown
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from flask_sock import Sock

# =============================================================================
# Configuration
# =============================================================================

app = Flask(__name__)
sock = Sock(app)

APPLICATIONS_DIR = os.environ.get(
    'APPLICATIONS_DIR',
    str(Path(__file__).parent.parent / 'templates' / 'applications'),
)
DB_PATH = os.environ.get(
    'DB_PATH',
    str(Path(__file__).parent.parent / 'data' / 'review_notes.db'),
)
BACKUP_DIR = os.environ.get(
    'BACKUP_DIR',
    str(Path(__file__).parent.parent / 'data' / 'backups'),
)
EVIDENCE_DIR = os.environ.get('EVIDENCE_DIR', '')
FELLOWSHIP_DIR = os.environ.get('FELLOWSHIP_DIR', '')
CHROMIUM_PATH = os.environ.get('CHROMIUM_PATH', '/usr/bin/chromium')

os.makedirs(BACKUP_DIR, exist_ok=True)

# Load field config from fields.json (editable without touching code)
_fields_path = os.path.join(os.path.dirname(__file__), 'fields.json')
if os.path.exists(_fields_path):
    with open(_fields_path) as _f:
        _fields_config = json.load(_f)
    CONSTELLATION_FIELDS = _fields_config.get('fields', {})
    EVIDENCE_CHEATSHEET = _fields_config.get('cheatsheet', {})
else:
    CONSTELLATION_FIELDS = {}
    EVIDENCE_CHEATSHEET = {}

# =============================================================================
# WebSocket clients & file watcher
# =============================================================================

_ws_clients = []
_served_mtimes = {}


class _FileChangeHandler(FileSystemEventHandler):
    def on_modified(self, event):
        if event.is_directory:
            return
        if not event.src_path.endswith('.md') and not event.src_path.endswith('.html'):
            return
        try:
            rel = os.path.relpath(event.src_path, APPLICATIONS_DIR)
        except ValueError:
            return
        parts = rel.split(os.sep)
        if len(parts) < 2:
            return
        slug = parts[0]
        doc_path = '/'.join(parts[1:])
        # Strip extension
        for ext in ('.md', '.html'):
            if doc_path.endswith(ext):
                doc_path = doc_path[:-len(ext)]
                break
        msg = json.dumps({'type': 'file_changed', 'slug': slug, 'document': doc_path})
        for ws in _ws_clients[:]:
            try:
                ws.send(msg)
            except Exception:
                try:
                    _ws_clients.remove(ws)
                except ValueError:
                    pass


_observer = None
if os.path.isdir(APPLICATIONS_DIR):
    _observer = Observer()
    _observer.schedule(_FileChangeHandler(), path=APPLICATIONS_DIR, recursive=True)
    _observer.daemon = True
    _observer.start()

# =============================================================================
# Database
# =============================================================================

def get_db():
    """Open a connection and ensure all tables exist."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("""CREATE TABLE IF NOT EXISTS review_notes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_slug TEXT NOT NULL,
        document TEXT NOT NULL,
        paragraph_index INTEGER NOT NULL,
        anchor_text TEXT,
        note TEXT NOT NULL,
        note_type TEXT DEFAULT 'edit',
        status TEXT DEFAULT 'pending',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        applied_at TEXT
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS field_status (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_slug TEXT NOT NULL,
        document TEXT NOT NULL,
        track TEXT DEFAULT 'both',
        status TEXT DEFAULT 'not_started',
        word_count INTEGER DEFAULT 0,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
        first_draft_at TEXT,
        human_written_at TEXT,
        ai_refined_at TEXT,
        final_at TEXT,
        UNIQUE(company_slug, document, track)
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS evidence_bookmarks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        source_file TEXT NOT NULL,
        section_heading TEXT,
        snippet TEXT,
        category TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS edit_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_slug TEXT NOT NULL,
        document TEXT NOT NULL,
        source TEXT NOT NULL DEFAULT 'browser',
        word_count_before INTEGER DEFAULT 0,
        word_count_after INTEGER DEFAULT 0,
        summary TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")
    conn.commit()
    return conn

# =============================================================================
# Path helpers
# =============================================================================

def _company_dir(slug):
    """Absolute path to a company's application directory."""
    return os.path.join(APPLICATIONS_DIR, slug)


def _require_company(slug):
    """Abort 404 if the company directory does not exist."""
    d = _company_dir(slug)
    if not os.path.isdir(d):
        abort(404)
    return d


def _find_resume_file(slug):
    """Return (dir_path, filename) of the first .html resume, or abort 404."""
    resume_dir = os.path.join(_company_dir(slug), 'resume')
    if os.path.isdir(resume_dir):
        for fname in os.listdir(resume_dir):
            if fname.endswith('.html'):
                return resume_dir, fname
    abort(404)


def _backup(filepath, slug, label):
    """Write a timestamped backup copy before any overwrite."""
    ext = os.path.splitext(filepath)[1]
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_name = f'{slug}__{label}__{ts}{ext}'
    with open(filepath) as f:
        with open(os.path.join(BACKUP_DIR, backup_name), 'w') as bf:
            bf.write(f.read())


def _log_edit(slug, doc_id, source, old_content, new_content):
    """Record an edit in edit_history and trim to 50 entries per document."""
    wc_before = len(old_content.split()) if old_content else 0
    wc_after = len(new_content.split()) if new_content else 0
    delta = wc_after - wc_before
    if delta >= 0:
        summary = f'+{delta} words'
    else:
        summary = f'{delta} words'
    db = get_db()
    db.execute(
        """INSERT INTO edit_history (company_slug, document, source, word_count_before, word_count_after, summary)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (slug, doc_id, source, wc_before, wc_after, summary),
    )
    db.execute(
        """DELETE FROM edit_history WHERE id NOT IN (
               SELECT id FROM edit_history WHERE company_slug=? AND document=?
               ORDER BY created_at DESC LIMIT 50
           ) AND company_slug=? AND document=?""",
        (slug, doc_id, slug, doc_id),
    )
    db.commit()
    db.close()

# =============================================================================
# Company & document discovery
# =============================================================================

def discover_companies():
    """Return sorted list of company slugs that contain at least one .md."""
    if not os.path.isdir(APPLICATIONS_DIR):
        return []
    return sorted(
        entry for entry in os.listdir(APPLICATIONS_DIR)
        if os.path.isdir(os.path.join(APPLICATIONS_DIR, entry))
        and any(f.endswith('.md') for f in os.listdir(os.path.join(APPLICATIONS_DIR, entry)))
    )


def _has_constellation(slug):
    """True if the company has a constellation/ subdirectory."""
    return os.path.isdir(os.path.join(APPLICATIONS_DIR, slug, 'constellation'))


def get_company_meta(slug):
    """Load optional meta.json for a company."""
    meta_path = os.path.join(APPLICATIONS_DIR, slug, 'meta.json')
    if os.path.exists(meta_path):
        with open(meta_path) as f:
            return json.load(f)
    return {}


def get_company_documents(slug):
    """Build the full document list: markdown files + constellation fields + resume."""
    company_dir = _company_dir(slug)
    if not os.path.isdir(company_dir):
        return []

    docs = []

    # Standard markdown documents
    for fname in sorted(os.listdir(company_dir)):
        if fname.endswith('.md'):
            name = fname.replace('.md', '')
            docs.append({
                'id': name,
                'filename': fname,
                'label': name.replace('_', ' ').title(),
            })

    # Constellation form fields (sorted by configured order)
    constellation_dir = os.path.join(company_dir, 'constellation')
    if os.path.isdir(constellation_dir):
        field_docs = []
        for fname in os.listdir(constellation_dir):
            if not fname.endswith('.md'):
                continue
            name = fname.replace('.md', '')
            conf = CONSTELLATION_FIELDS.get(name, {})
            field_docs.append({
                'id': f'constellation/{name}',
                'filename': fname,
                'label': conf.get('label', name.replace('_', ' ').title()),
                'type': 'constellation',
                'order': conf.get('order', 99),
            })
        field_docs.sort(key=lambda d: d['order'])
        docs.extend(field_docs)

    # Resume (first .html found)
    resume_dir = os.path.join(company_dir, 'resume')
    if os.path.isdir(resume_dir):
        for fname in os.listdir(resume_dir):
            if fname.endswith('.html'):
                docs.append({'id': 'resume', 'filename': fname, 'label': 'Resume', 'type': 'html'})
                break

    return docs

# =============================================================================
# Markdown rendering
# =============================================================================

def split_md_blocks(md_text):
    """Split markdown into logical blocks separated by blank lines (respecting fenced code)."""
    blocks, current, in_code = [], [], False

    for line in md_text.split('\n'):
        if line.strip().startswith('```'):
            if in_code:
                current.append(line)
                blocks.append('\n'.join(current))
                current, in_code = [], False
            else:
                if current and any(l.strip() for l in current):
                    blocks.append('\n'.join(current))
                current = [line]
                in_code = True
            continue
        if in_code:
            current.append(line)
            continue
        if line.strip() == '':
            if current and any(l.strip() for l in current):
                blocks.append('\n'.join(current))
            current = []
        else:
            current.append(line)

    if current and any(l.strip() for l in current):
        blocks.append('\n'.join(current))

    return [b for b in blocks if b.strip()]


def render_md_with_paragraphs(md_text):
    """Render markdown to annotatable HTML. Each block gets a data-idx and data-raw."""
    blocks = split_md_blocks(md_text)
    parts = []
    for i, block in enumerate(blocks):
        rendered = markdown.markdown(block, extensions=['fenced_code', 'tables', 'nl2br'])
        text_only = re.sub(r'<[^>]+>', '', rendered).strip()
        anchor = text_only[:80] if text_only else ''
        raw_esc = (block
                   .replace('&', '&amp;')
                   .replace('"', '&quot;')
                   .replace('<', '&lt;')
                   .replace('>', '&gt;'))
        parts.append(
            f'<div class="reviewable" data-idx="{i}" data-anchor="{anchor}" '
            f'data-raw="{raw_esc}">{rendered}</div>'
        )
    return '\n'.join(parts), blocks


def parse_submission_guide(slug):
    """Extract the section matching `slug` from the shared submission_guide.md."""
    guide_path = os.path.join(APPLICATIONS_DIR, 'submission_guide.md')
    if not os.path.exists(guide_path):
        return None
    with open(guide_path) as f:
        content = f.read()

    sections = re.split(r'={10,}', content)
    slug_norm = slug.lower().replace('-', '').replace(' ', '')
    for i, section in enumerate(sections):
        if slug_norm in section.lower().replace('-', '').replace(' ', '').replace('_', ''):
            full = section + (sections[i + 1] if i + 1 < len(sections) else '')
            return full.strip()
    return None

# =============================================================================
# Evidence cache (mtime-invalidated in-memory cache)
# =============================================================================

_evidence_cache = {'data': None, 'mtimes': {}}


def _load_evidence():
    """Parse all .md files from EVIDENCE_DIR into sections, cached by mtime."""
    if not EVIDENCE_DIR or not os.path.isdir(EVIDENCE_DIR):
        return []

    # Check if cache is still valid
    current_mtimes = {}
    for fname in os.listdir(EVIDENCE_DIR):
        fpath = os.path.join(EVIDENCE_DIR, fname)
        if os.path.isfile(fpath) and fname.endswith('.md'):
            current_mtimes[fname] = os.path.getmtime(fpath)

    if _evidence_cache['data'] is not None and _evidence_cache['mtimes'] == current_mtimes:
        return _evidence_cache['data']

    # Parse each file into heading-delimited sections
    evidence = []
    for fname in sorted(current_mtimes):
        with open(os.path.join(EVIDENCE_DIR, fname)) as f:
            content = f.read()

        base = fname.replace('.md', '')
        category = base.replace('-', ' ').title()
        sections, heading, lines = [], category, []

        for line in content.split('\n'):
            if line.startswith('## '):
                if lines:
                    text = '\n'.join(lines).strip()
                    if text:
                        sections.append({'heading': heading, 'text': text, 'source_file': fname})
                heading = line.lstrip('#').strip()
                lines = []
            else:
                lines.append(line)

        if lines:
            text = '\n'.join(lines).strip()
            if text:
                sections.append({'heading': heading, 'text': text, 'source_file': fname})

        evidence.append({'file': fname, 'category': category, 'sections': sections})

    _evidence_cache['data'] = evidence
    _evidence_cache['mtimes'] = current_mtimes
    return evidence


def _parse_stats_tables():
    """Extract | Metric | Value | Source | rows from platform-stats.md."""
    if not EVIDENCE_DIR:
        return []
    stats_path = os.path.join(EVIDENCE_DIR, 'platform-stats.md')
    if not os.path.exists(stats_path):
        return []

    with open(stats_path) as f:
        content = f.read()

    stats, group = [], ''
    for line in content.split('\n'):
        if line.startswith('## '):
            group = line.lstrip('#').strip()
        m = re.match(r'\|\s*(.+?)\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|', line)
        if m:
            metric = m.group(1).strip()
            if metric.startswith('---') or metric in ('Metric',):
                continue
            stats.append({
                'group': group,
                'metric': metric,
                'value': m.group(2).strip(),
                'source': m.group(3).strip(),
            })
    return stats


def _build_export_data(slug, track):
    """Collect all constellation field contents for export."""
    constellation_dir = os.path.join(APPLICATIONS_DIR, slug, 'constellation')
    if not os.path.isdir(constellation_dir):
        return None

    fields = []
    for key, conf in sorted(CONSTELLATION_FIELDS.items(), key=lambda x: x[1]['order']):
        if conf['track'] not in (track, 'both'):
            continue
        filepath = os.path.join(constellation_dir, f'{key}.md')
        content = ''
        if os.path.exists(filepath):
            with open(filepath) as f:
                content = f.read().strip()
        fields.append({
            'field_id': key,
            'label': conf['label'],
            'content': content,
            'word_count': len(content.split()) if content else 0,
            'word_min': conf['word_min'],
            'word_max': conf['word_max'],
        })
    return {'track': track, 'fields': fields}

# =============================================================================
# Routes — Pages
# =============================================================================

@app.route('/')
def index():
    companies = discover_companies()
    return render_template('review.html', companies=companies, active=companies[0] if companies else '')


@app.route('/review/<slug>')
def review(slug):
    companies = discover_companies()
    if slug not in companies:
        abort(404)
    return render_template('review.html', companies=companies, active=slug)

# =============================================================================
# Routes — Companies
# =============================================================================

@app.route('/api/companies')
def api_companies():
    """List all companies with their documents, note counts, and constellation status."""
    db = get_db()
    result = []
    for slug in discover_companies():
        meta = get_company_meta(slug)
        pending = db.execute(
            "SELECT COUNT(*) as c FROM review_notes WHERE company_slug=? AND status='pending'",
            (slug,),
        ).fetchone()['c']
        result.append({
            'slug': slug,
            'name': meta.get('company', slug.replace('-', ' ').title()),
            'role': meta.get('role', ''),
            'status': meta.get('status', 'RESEARCHING'),
            'salary': meta.get('salary_range', meta.get('salary', '')),
            'documents': get_company_documents(slug),
            'pending_notes': pending,
            'has_constellation': _has_constellation(slug),
        })
    db.close()
    return jsonify(result)

# =============================================================================
# Routes — Documents (read, save, block-edit)
# =============================================================================

@app.route('/api/document/<slug>/<path:doc>/history')
def api_document_history(slug, doc):
    """Recent edit history for a document."""
    _require_company(slug)
    db = get_db()
    rows = db.execute(
        "SELECT * FROM edit_history WHERE company_slug=? AND document=? ORDER BY created_at DESC LIMIT 20",
        (slug, doc),
    ).fetchall()
    db.close()
    return jsonify([dict(r) for r in rows])


@app.route('/api/document/<slug>/<path:doc>/versions')
def api_document_versions(slug, doc):
    """List backup versions of a document."""
    _require_company(slug)
    doc_safe = doc.replace('/', '__')
    prefix = f'{slug}__{doc_safe}__'
    versions = []
    for fname in sorted(os.listdir(BACKUP_DIR), reverse=True):
        if fname.startswith(prefix):
            fpath = os.path.join(BACKUP_DIR, fname)
            versions.append({
                'filename': fname,
                'size': os.path.getsize(fpath),
                'modified': os.path.getmtime(fpath),
            })
    return jsonify(versions[:30])


@app.route('/api/document/<slug>/<path:doc>/restore', methods=['POST'])
def api_document_restore(slug, doc):
    """Restore a document from a backup version."""
    _require_company(slug)
    filename = request.json.get('filename', '')
    if not filename or '/' in filename or '..' in filename or '\\' in filename:
        return jsonify({'error': 'Invalid filename'}), 400
    backup_path = os.path.join(BACKUP_DIR, filename)
    if not os.path.exists(backup_path):
        return jsonify({'error': 'Backup not found'}), 404
    # Resolve document filepath
    filepath = os.path.join(_company_dir(slug), f'{doc}.md')
    if not os.path.exists(filepath):
        abort(404)
    # Read old content, backup current, restore from backup
    with open(filepath) as f:
        old_content = f.read()
    _backup(filepath, slug, doc.replace('/', '__'))
    with open(backup_path) as f:
        restored = f.read()
    with open(filepath, 'w') as f:
        f.write(restored)
    _log_edit(slug, doc, 'restore', old_content, restored)
    html, blocks = render_md_with_paragraphs(restored)
    return jsonify({'html': html, 'raw': restored, 'blocks': blocks})


@app.route('/api/document/<slug>/<path:doc>/check')
def api_document_check(slug, doc):
    """Check if a document has been modified externally."""
    _require_company(slug)
    filepath = os.path.join(_company_dir(slug), f'{doc}.md')
    if not os.path.exists(filepath):
        abort(404)
    mtime = os.path.getmtime(filepath)
    mtime_key = f'{slug}/{doc}'
    external_edit = (mtime_key in _served_mtimes and mtime > _served_mtimes[mtime_key])
    return jsonify({'mtime': mtime, 'external_edit': external_edit})


@app.route('/api/document/<slug>/<doc_id>')
def api_document(slug, doc_id):
    """Render a markdown document as annotatable HTML blocks."""
    _require_company(slug)
    filepath = os.path.join(_company_dir(slug), f'{doc_id}.md')
    if not os.path.exists(filepath):
        abort(404)
    with open(filepath) as f:
        raw = f.read()
    mtime = os.path.getmtime(filepath)
    mtime_key = f'{slug}/{doc_id}'
    external_edit = (mtime_key in _served_mtimes and mtime > _served_mtimes[mtime_key])
    _served_mtimes[mtime_key] = mtime
    html, blocks = render_md_with_paragraphs(raw)
    return jsonify({'html': html, 'raw': raw, 'blocks': blocks, 'external_edit': external_edit})


@app.route('/api/document/<slug>/constellation/<field_id>')
def api_constellation_document(slug, field_id):
    """Render a constellation form field with its config metadata."""
    _require_company(slug)
    filepath = os.path.join(_company_dir(slug), 'constellation', f'{field_id}.md')
    if not os.path.exists(filepath):
        abort(404)
    with open(filepath) as f:
        raw = f.read()
    mtime = os.path.getmtime(filepath)
    mtime_key = f'{slug}/constellation/{field_id}'
    external_edit = (mtime_key in _served_mtimes and mtime > _served_mtimes[mtime_key])
    _served_mtimes[mtime_key] = mtime
    html, blocks = render_md_with_paragraphs(raw)
    return jsonify({
        'html': html, 'raw': raw, 'blocks': blocks,
        'field_config': CONSTELLATION_FIELDS.get(field_id, {}),
        'external_edit': external_edit,
    })


@app.route('/api/document/<slug>/<doc_id>', methods=['PUT'])
def api_save_document(slug, doc_id):
    """Overwrite a markdown document (with backup)."""
    _require_company(slug)
    filepath = os.path.join(_company_dir(slug), f'{doc_id}.md')
    if not os.path.exists(filepath):
        abort(404)
    content = request.json.get('content', '')
    if not content.strip():
        return jsonify({'error': 'Empty content'}), 400
    with open(filepath) as f:
        old_content = f.read()
    _backup(filepath, slug, doc_id)
    with open(filepath, 'w') as f:
        f.write(content)
    _log_edit(slug, doc_id, 'browser', old_content, content)
    html, blocks = render_md_with_paragraphs(content)
    return jsonify({'html': html, 'raw': content, 'blocks': blocks})


@app.route('/api/document/<slug>/constellation/<field_id>', methods=['PUT'])
def api_save_constellation_document(slug, field_id):
    """Save a constellation field (with backup). Returns word count."""
    _require_company(slug)
    filepath = os.path.join(_company_dir(slug), 'constellation', f'{field_id}.md')
    if not os.path.exists(filepath):
        abort(404)
    content = request.json.get('content', '')
    with open(filepath) as f:
        old_content = f.read()
    _backup(filepath, slug, f'constellation__{field_id}')
    with open(filepath, 'w') as f:
        f.write(content)
    _log_edit(slug, f'constellation/{field_id}', 'browser', old_content, content)
    html, blocks = render_md_with_paragraphs(content)
    return jsonify({
        'html': html, 'raw': content, 'blocks': blocks,
        'word_count': len(content.split()),
    })


@app.route('/api/document/<slug>/<doc_id>/block/<int:block_idx>', methods=['PUT'])
def api_save_block(slug, doc_id, block_idx):
    """Replace a single paragraph block within a document."""
    _require_company(slug)
    filepath = os.path.join(_company_dir(slug), f'{doc_id}.md')
    if not os.path.exists(filepath):
        abort(404)
    new_block = request.json.get('content', '')
    if new_block is None:
        return jsonify({'error': 'Missing content'}), 400

    with open(filepath) as f:
        raw = f.read()
    blocks = split_md_blocks(raw)
    if block_idx < 0 or block_idx >= len(blocks):
        return jsonify({'error': f'Block {block_idx} out of range (0-{len(blocks)-1})'}), 400

    if new_block.strip() == '':
        new_raw = raw.replace(blocks[block_idx], '', 1)
        while '\n\n\n' in new_raw:
            new_raw = new_raw.replace('\n\n\n', '\n\n')
    else:
        new_raw = raw.replace(blocks[block_idx], new_block, 1)

    _backup(filepath, slug, doc_id)
    with open(filepath, 'w') as f:
        f.write(new_raw)
    _log_edit(slug, doc_id, 'browser', raw, new_raw)
    html, new_blocks = render_md_with_paragraphs(new_raw)
    return jsonify({'html': html, 'raw': new_raw, 'blocks': new_blocks})

# =============================================================================
# Routes — Resume (preview, edit HTML, PDF generation)
# =============================================================================

@app.route('/api/resume/<slug>')
def api_resume(slug):
    """Serve resume HTML for iframe preview."""
    _require_company(slug)
    d, fname = _find_resume_file(slug)
    return send_file(os.path.join(d, fname))


@app.route('/api/resume/<slug>/pdf')
def api_resume_pdf(slug):
    """Serve an existing resume PDF for download."""
    _require_company(slug)
    resume_dir = os.path.join(_company_dir(slug), 'resume')
    if os.path.isdir(resume_dir):
        for fname in os.listdir(resume_dir):
            if fname.endswith('.pdf'):
                return send_file(os.path.join(resume_dir, fname), as_attachment=True)
    abort(404)


@app.route('/api/resume-html/<slug>')
def api_resume_html_get(slug):
    """Get raw resume HTML for the split-pane editor."""
    _require_company(slug)
    d, fname = _find_resume_file(slug)
    with open(os.path.join(d, fname)) as f:
        return jsonify({'html': f.read(), 'filename': fname})


@app.route('/api/resume-html/<slug>', methods=['PUT'])
def api_resume_html_put(slug):
    """Save edited resume HTML (with backup)."""
    _require_company(slug)
    d, fname = _find_resume_file(slug)
    html_content = request.json.get('html', '')
    if not html_content.strip():
        return jsonify({'error': 'Empty content'}), 400
    filepath = os.path.join(d, fname)
    with open(filepath) as f:
        old_html = f.read()
    _backup(filepath, slug, 'resume')
    with open(filepath, 'w') as f:
        f.write(html_content)
    _log_edit(slug, 'resume', 'browser', old_html, html_content)
    return jsonify({'saved': True, 'filename': fname})


@app.route('/api/resume-html/<slug>/pdf', methods=['POST'])
def api_resume_html_pdf(slug):
    """Generate a PDF from resume HTML via headless Chromium."""
    _require_company(slug)
    d, fname = _find_resume_file(slug)
    html_file = os.path.join(d, fname)
    pdf_path = html_file.replace('.html', '.pdf')
    try:
        subprocess.run(
            [CHROMIUM_PATH, '--headless', '--disable-gpu', '--no-sandbox',
             f'--print-to-pdf={pdf_path}', '--no-pdf-header-footer', html_file],
            check=True, timeout=30, capture_output=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired) as e:
        return jsonify({'error': f'PDF generation failed: {e}'}), 500
    return send_file(pdf_path, as_attachment=True, download_name=f'resume-{slug}.pdf',
                     mimetype='application/pdf')


@app.route('/api/resume-import/<slug>')
def api_resume_import(slug):
    """Import resume HTML from the fellowship directory (if mounted)."""
    if FELLOWSHIP_DIR:
        for fname in ('resume-ai-safety.html', 'resume.html'):
            fpath = os.path.join(FELLOWSHIP_DIR, fname)
            if os.path.exists(fpath):
                with open(fpath) as f:
                    return jsonify({'html': f.read(), 'filename': fname, 'source': 'fellowship'})
    return jsonify({'html': '', 'filename': '', 'source': None})

# =============================================================================
# Routes — Evidence & cheat sheets
# =============================================================================

@app.route('/api/evidence')
def api_evidence():
    """All evidence sources, parsed into heading-delimited sections."""
    return jsonify(_load_evidence())


@app.route('/api/evidence/search')
def api_evidence_search():
    """Substring search across all evidence sections. Returns up to 50 hits."""
    q = request.args.get('q', '').lower().strip()
    if not q:
        return jsonify([])
    results = []
    for source in _load_evidence():
        for section in source['sections']:
            if q in section['text'].lower() or q in section['heading'].lower():
                results.append({
                    'file': source['file'],
                    'category': source['category'],
                    'heading': section['heading'],
                    'text': section['text'][:500],
                    'source_file': section['source_file'],
                })
    return jsonify(results[:50])


@app.route('/api/evidence/stats')
def api_evidence_stats():
    """Platform stats as structured JSON (parsed from markdown tables)."""
    return jsonify(_parse_stats_tables())


@app.route('/api/cheatsheet/<doc_id>')
def api_cheatsheet(doc_id):
    """Per-field writing tips: what to hit, evidence to cite, tips."""
    field_id = doc_id.replace('constellation/', '')
    return jsonify(EVIDENCE_CHEATSHEET.get(field_id, {}))


@app.route('/api/guide/<slug>')
def api_guide(slug):
    """Submission guide section for a company (if submission_guide.md exists)."""
    guide = parse_submission_guide(slug)
    if guide:
        return jsonify({'html': markdown.markdown(guide), 'raw': guide})
    return jsonify({'html': '', 'raw': ''})

# =============================================================================
# Routes — Field status tracking
# =============================================================================

@app.route('/api/fellowship/<track>/fields')
def api_fellowship_fields(track):
    """Field config for a given track (security, safety, or both)."""
    return jsonify({
        k: v for k, v in CONSTELLATION_FIELDS.items()
        if v['track'] in (track, 'both')
    })


@app.route('/api/fellowship/<track>/progress')
def api_fellowship_progress(track):
    """Progress summary: completed, drafted, not started counts."""
    db = get_db()
    rows = db.execute(
        "SELECT * FROM field_status WHERE track IN (?, 'both')", (track,)
    ).fetchall()
    db.close()
    total = len(CONSTELLATION_FIELDS)
    completed = sum(1 for r in rows if r['status'] == 'final')
    drafted = sum(1 for r in rows if r['status'] in ('first_draft', 'human_written', 'ai_refined'))
    return jsonify({
        'total_fields': total,
        'completed': completed,
        'drafted': drafted,
        'not_started': total - completed - drafted,
        'statuses': {r['document']: dict(r) for r in rows},
        'percentage': round(completed / total * 100) if total else 0,
    })


@app.route('/api/field-status/<slug>/<path:doc_id>')
def api_field_status_get(slug, doc_id):
    """Get the current status of a single field."""
    db = get_db()
    row = db.execute(
        "SELECT * FROM field_status WHERE company_slug=? AND document=?", (slug, doc_id)
    ).fetchone()
    db.close()
    if row:
        return jsonify(dict(row))
    return jsonify({'company_slug': slug, 'document': doc_id, 'status': 'not_started', 'word_count': 0})


# Status → timestamp column mapping
_STATUS_TS = {
    'first_draft': 'first_draft_at',
    'human_written': 'human_written_at',
    'ai_refined': 'ai_refined_at',
    'final': 'final_at',
}


@app.route('/api/field-status/<slug>/<path:doc_id>', methods=['PUT'])
def api_field_status_put(slug, doc_id):
    """Advance (or set) the status of a field. Records transition timestamps."""
    data = request.json
    new_status = data.get('status', 'not_started')
    word_count = data.get('word_count', 0)
    now = datetime.now().isoformat()

    db = get_db()
    existing = db.execute(
        "SELECT id FROM field_status WHERE company_slug=? AND document=?", (slug, doc_id)
    ).fetchone()

    if existing:
        parts = ["status=?", "word_count=?", "updated_at=?"]
        vals = [new_status, word_count, now]
        if new_status in _STATUS_TS:
            parts.append(f"{_STATUS_TS[new_status]}=?")
            vals.append(now)
        vals.extend([slug, doc_id])
        db.execute(f"UPDATE field_status SET {','.join(parts)} WHERE company_slug=? AND document=?", vals)
    else:
        ts = {v: (now if new_status in _STATUS_TS and _STATUS_TS[new_status] == v else None)
              for v in _STATUS_TS.values()}
        db.execute(
            """INSERT INTO field_status
               (company_slug, document, track, status, word_count, updated_at,
                first_draft_at, human_written_at, ai_refined_at, final_at)
               VALUES (?, ?, 'both', ?, ?, ?, ?, ?, ?, ?)""",
            (slug, doc_id, new_status, word_count, now,
             ts['first_draft_at'], ts['human_written_at'], ts['ai_refined_at'], ts['final_at']),
        )

    db.commit()
    row = db.execute(
        "SELECT * FROM field_status WHERE company_slug=? AND document=?", (slug, doc_id)
    ).fetchone()
    db.close()
    return jsonify(dict(row))

# =============================================================================
# Routes — Export
# =============================================================================

@app.route('/api/export/<slug>/<track>/plain-text')
def api_export_plain_text(slug, track):
    """All constellation field contents as plain text (for copy-paste into portals)."""
    data = _build_export_data(slug, track)
    if data is None:
        return jsonify({'error': 'No constellation fields found'}), 404
    return jsonify(data)


@app.route('/api/export/<slug>/<track>/email', methods=['POST'])
def api_export_email(slug, track):
    """Email all field contents to self via SMTP."""
    smtp_host = os.environ.get('SMTP_HOST', '')
    smtp_port = int(os.environ.get('SMTP_PORT', '587'))
    smtp_user = os.environ.get('SMTP_USER', '')
    smtp_pass = os.environ.get('SMTP_PASS', '')
    email_to = os.environ.get('EMAIL_TO', smtp_user)
    if not all([smtp_host, smtp_user, smtp_pass]):
        return jsonify({'error': 'SMTP not configured (set SMTP_HOST, SMTP_USER, SMTP_PASS)'}), 500

    export_data = _build_export_data(slug, track)
    if export_data is None:
        return jsonify({'error': 'No constellation fields found'}), 404

    body_lines = [f"Anvil Export — {track.upper()} Track\n{'=' * 50}\n"]
    for field in export_data['fields']:
        body_lines.append(f"\n--- {field['label']} ---")
        body_lines.append(f"({field['word_count']} words, target: {field['word_min']}-{field['word_max']})\n")
        body_lines.append(field['content'] or '[Not yet written]')
        body_lines.append('')

    msg = MIMEMultipart()
    msg['From'] = smtp_user
    msg['To'] = email_to
    msg['Subject'] = f'Anvil Export: {slug}/{track} — {datetime.now().strftime("%Y-%m-%d %H:%M")}'
    msg.attach(MIMEText('\n'.join(body_lines), 'plain'))

    try:
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)
        return jsonify({'sent': True, 'to': email_to})
    except Exception as e:
        return jsonify({'error': f'Email failed: {e}'}), 500

# =============================================================================
# Routes — Review notes
# =============================================================================

@app.route('/api/notes/<slug>')
def api_notes_for_company(slug):
    """All review notes for a company, ordered by document and position."""
    db = get_db()
    rows = db.execute(
        "SELECT * FROM review_notes WHERE company_slug=? ORDER BY document, paragraph_index", (slug,)
    ).fetchall()
    db.close()
    return jsonify([dict(r) for r in rows])


@app.route('/api/notes/<slug>/<doc_id>')
def api_notes_for_doc(slug, doc_id):
    """Notes for a single document."""
    db = get_db()
    rows = db.execute(
        "SELECT * FROM review_notes WHERE company_slug=? AND document=? ORDER BY paragraph_index",
        (slug, doc_id),
    ).fetchall()
    db.close()
    return jsonify([dict(r) for r in rows])


@app.route('/api/notes', methods=['POST'])
def api_create_note():
    """Create a new review note on a paragraph."""
    data = request.json
    for key in ('company_slug', 'document', 'paragraph_index', 'note'):
        if key not in data:
            return jsonify({'error': f'Missing required field: {key}'}), 400

    db = get_db()
    cursor = db.execute(
        """INSERT INTO review_notes (company_slug, document, paragraph_index, anchor_text, note, note_type)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (data['company_slug'], data['document'], data['paragraph_index'],
         data.get('anchor_text', ''), data['note'], data.get('note_type', 'edit')),
    )
    db.commit()
    row = db.execute("SELECT * FROM review_notes WHERE id=?", (cursor.lastrowid,)).fetchone()
    db.close()
    return jsonify(dict(row)), 201


@app.route('/api/notes/<int:note_id>', methods=['PUT'])
def api_update_note(note_id):
    """Update note text, type, or status."""
    data = request.json
    db = get_db()
    sets, vals = [], []
    for field in ('note', 'note_type', 'status'):
        if field in data:
            sets.append(f"{field}=?")
            vals.append(data[field])
    if data.get('status') == 'applied':
        sets.append("applied_at=?")
        vals.append(datetime.now().isoformat())
    if not sets:
        return jsonify({'error': 'Nothing to update'}), 400
    vals.append(note_id)
    db.execute(f"UPDATE review_notes SET {','.join(sets)} WHERE id=?", vals)
    db.commit()
    row = db.execute("SELECT * FROM review_notes WHERE id=?", (note_id,)).fetchone()
    db.close()
    return jsonify(dict(row)) if row else ('', 404)


@app.route('/api/notes/<int:note_id>', methods=['DELETE'])
def api_delete_note(note_id):
    """Delete a review note."""
    db = get_db()
    db.execute("DELETE FROM review_notes WHERE id=?", (note_id,))
    db.commit()
    db.close()
    return '', 204


@app.route('/api/notes/export')
def api_export_notes():
    """Export all pending notes as JSON (for CLI consumption)."""
    slug = request.args.get('company')
    db = get_db()
    query = "SELECT * FROM review_notes WHERE status='pending'"
    params = ()
    if slug:
        query += " AND company_slug=?"
        params = (slug,)
    query += " ORDER BY company_slug, document, paragraph_index"
    rows = db.execute(query, params).fetchall()
    db.close()
    return jsonify({
        'exported_at': datetime.now().isoformat(),
        'count': len(rows),
        'notes': [dict(r) for r in rows],
    })

# =============================================================================
# Routes — WebSocket
# =============================================================================

@sock.route('/api/ws')
def ws_watch(ws):
    """WebSocket endpoint for live file-change notifications."""
    _ws_clients.append(ws)
    try:
        while True:
            ws.receive()
    except Exception:
        pass
    finally:
        try:
            _ws_clients.remove(ws)
        except ValueError:
            pass

# =============================================================================
# Entry point
# =============================================================================

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
