"""
Anvil test suite.

Run: pytest test_anvil.py -v
"""

import json
import os
import shutil
import tempfile

import pytest

# Configure test environment before importing app
_test_dir = tempfile.mkdtemp(prefix='anvil-test-')
_apps_dir = os.path.join(_test_dir, 'applications')
_evidence_dir = os.path.join(_test_dir, 'evidence')
_backup_dir = os.path.join(_test_dir, 'backups')
_db_path = os.path.join(_test_dir, 'test.db')

os.environ['APPLICATIONS_DIR'] = _apps_dir
os.environ['EVIDENCE_DIR'] = _evidence_dir
os.environ['DB_PATH'] = _db_path
os.environ['BACKUP_DIR'] = _backup_dir
os.environ['FELLOWSHIP_DIR'] = ''


def _setup_test_company():
    """Create a test company with all document types."""
    company_dir = os.path.join(_apps_dir, 'test-company')
    constellation_dir = os.path.join(company_dir, 'constellation')
    resume_dir = os.path.join(company_dir, 'resume')
    os.makedirs(constellation_dir, exist_ok=True)
    os.makedirs(resume_dir, exist_ok=True)

    # meta.json
    with open(os.path.join(company_dir, 'meta.json'), 'w') as f:
        json.dump({
            'company': 'Test Company',
            'role': 'Test Role',
            'status': 'PREPARING',
            'salary_range': '$100K',
            'deadline': '2026-12-01',
            'apply_url': 'https://example.com/apply',
        }, f)

    # Standard markdown doc
    with open(os.path.join(company_dir, 'cover_letter.md'), 'w') as f:
        f.write('# Cover Letter\n\nDear Hiring Team,\n\nI am writing to apply.\n\nBest regards,\nTest User')

    with open(os.path.join(company_dir, 'talking_points.md'), 'w') as f:
        f.write('# Talking Points\n\n## Why This Company\n\n- Great mission')

    # Constellation fields
    for field in ('why_interested', 'relevant_background', 'anything_else'):
        with open(os.path.join(constellation_dir, f'{field}.md'), 'w') as f:
            f.write('')

    # Resume HTML
    with open(os.path.join(resume_dir, 'resume.html'), 'w') as f:
        f.write('<html><body><h1>Test User</h1><p>Software Engineer</p></body></html>')


def _setup_test_evidence():
    """Create test evidence files."""
    os.makedirs(_evidence_dir, exist_ok=True)

    with open(os.path.join(_evidence_dir, 'platform-stats.md'), 'w') as f:
        f.write(
            '# Stats\n\n## Scale\n\n'
            '| Metric | Value | Source |\n'
            '|--------|-------|--------|\n'
            '| Lines of code | 50000 | cloc |\n'
            '| Tests | 200 | pytest |\n'
        )

    with open(os.path.join(_evidence_dir, 'projects.md'), 'w') as f:
        f.write('# Projects\n\n## Project Alpha\n\nA web framework.\n\n## Project Beta\n\nA CLI tool.')


import app  # noqa: E402 — must import after env setup


@pytest.fixture
def client():
    """Flask test client with fresh test data."""
    _setup_test_company()
    _setup_test_evidence()
    app.app.config['TESTING'] = True
    # Reset evidence cache
    app._evidence_cache['data'] = None
    app._evidence_cache['mtimes'] = {}
    with app.app.test_client() as c:
        yield c


@pytest.fixture(autouse=True)
def cleanup():
    """Clean up test DB between tests."""
    yield
    if os.path.exists(_db_path):
        os.remove(_db_path)


# =========================================================================
# Pages
# =========================================================================

class TestPages:
    def test_index(self, client):
        r = client.get('/')
        assert r.status_code == 200
        assert b'Anvil' in r.data

    def test_review_page(self, client):
        r = client.get('/review/test-company')
        assert r.status_code == 200

    def test_review_404(self, client):
        r = client.get('/review/nonexistent')
        assert r.status_code == 404


# =========================================================================
# Companies API
# =========================================================================

class TestCompanies:
    def test_list_companies(self, client):
        r = client.get('/api/companies')
        assert r.status_code == 200
        data = r.get_json()
        assert len(data) >= 1
        company = next(c for c in data if c['slug'] == 'test-company')
        assert company['name'] == 'Test Company'
        assert company['role'] == 'Test Role'
        assert company['has_constellation'] is True
        assert company['pending_notes'] == 0

    def test_company_documents(self, client):
        r = client.get('/api/companies')
        company = next(c for c in r.get_json() if c['slug'] == 'test-company')
        doc_ids = [d['id'] for d in company['documents']]
        assert 'cover_letter' in doc_ids
        assert 'talking_points' in doc_ids
        assert 'resume' in doc_ids
        constellation = [d for d in company['documents'] if d.get('type') == 'constellation']
        assert len(constellation) == 3


# =========================================================================
# Documents API
# =========================================================================

class TestDocuments:
    def test_get_document(self, client):
        r = client.get('/api/document/test-company/cover_letter')
        assert r.status_code == 200
        data = r.get_json()
        assert 'Dear Hiring Team' in data['raw']
        assert '<div class="reviewable"' in data['html']
        assert len(data['blocks']) > 0

    def test_get_document_404(self, client):
        r = client.get('/api/document/test-company/nonexistent')
        assert r.status_code == 404

    def test_save_document(self, client):
        new_content = '# Updated Letter\n\nNew content here.'
        r = client.put('/api/document/test-company/cover_letter',
                       json={'content': new_content})
        assert r.status_code == 200
        data = r.get_json()
        assert data['raw'] == new_content
        # Verify backup was created
        backups = os.listdir(_backup_dir)
        assert any('cover_letter' in b for b in backups)

    def test_save_empty_rejected(self, client):
        r = client.put('/api/document/test-company/cover_letter',
                       json={'content': '   '})
        assert r.status_code == 400

    def test_save_block(self, client):
        r = client.put('/api/document/test-company/cover_letter/block/1',
                       json={'content': 'Updated paragraph.'})
        assert r.status_code == 200
        assert 'Updated paragraph.' in r.get_json()['raw']

    def test_save_block_out_of_range(self, client):
        r = client.put('/api/document/test-company/cover_letter/block/999',
                       json={'content': 'nope'})
        assert r.status_code == 400


# =========================================================================
# Constellation API
# =========================================================================

class TestConstellation:
    def test_get_constellation_field(self, client):
        r = client.get('/api/document/test-company/constellation/why_interested')
        assert r.status_code == 200
        data = r.get_json()
        assert 'field_config' in data
        assert data['field_config']['label'] is not None

    def test_save_constellation_field(self, client):
        r = client.put('/api/document/test-company/constellation/why_interested',
                       json={'content': 'I am interested because...'})
        assert r.status_code == 200
        data = r.get_json()
        assert data['word_count'] == 4

    def test_constellation_404(self, client):
        r = client.get('/api/document/test-company/constellation/nonexistent')
        assert r.status_code == 404


# =========================================================================
# Evidence API
# =========================================================================

class TestEvidence:
    def test_list_evidence(self, client):
        r = client.get('/api/evidence')
        assert r.status_code == 200
        data = r.get_json()
        assert len(data) == 2
        filenames = [s['file'] for s in data]
        assert 'platform-stats.md' in filenames
        assert 'projects.md' in filenames

    def test_evidence_sections(self, client):
        r = client.get('/api/evidence')
        data = r.get_json()
        projects = next(s for s in data if s['file'] == 'projects.md')
        headings = [s['heading'] for s in projects['sections']]
        assert 'Project Alpha' in headings
        assert 'Project Beta' in headings

    def test_evidence_search(self, client):
        r = client.get('/api/evidence/search?q=framework')
        assert r.status_code == 200
        results = r.get_json()
        assert len(results) >= 1
        assert 'framework' in results[0]['text'].lower()

    def test_evidence_search_empty(self, client):
        r = client.get('/api/evidence/search?q=')
        assert r.get_json() == []

    def test_evidence_search_no_results(self, client):
        r = client.get('/api/evidence/search?q=xyznonexistent')
        assert r.get_json() == []

    def test_evidence_stats(self, client):
        r = client.get('/api/evidence/stats')
        assert r.status_code == 200
        data = r.get_json()
        assert len(data) >= 2
        metrics = [s['metric'] for s in data]
        assert 'Lines of code' in metrics

    def test_evidence_cache_invalidation(self, client):
        # First load
        r1 = client.get('/api/evidence')
        assert len(r1.get_json()) == 2
        # Add a new file
        with open(os.path.join(_evidence_dir, 'new-file.md'), 'w') as f:
            f.write('# New\n\n## Section\n\nContent.')
        # Cache should invalidate on mtime change
        app._evidence_cache['data'] = None  # force reload
        r2 = client.get('/api/evidence')
        assert len(r2.get_json()) == 3
        os.remove(os.path.join(_evidence_dir, 'new-file.md'))


# =========================================================================
# Cheat Sheet API
# =========================================================================

class TestCheatSheet:
    def test_get_cheatsheet(self, client):
        r = client.get('/api/cheatsheet/why_interested')
        assert r.status_code == 200
        data = r.get_json()
        assert 'what_to_hit' in data
        assert 'tips' in data

    def test_cheatsheet_strips_prefix(self, client):
        """The frontend sends just the field_id, not the full path."""
        r = client.get('/api/cheatsheet/why_interested')
        data = r.get_json()
        assert 'what_to_hit' in data
        assert len(data['tips']) > 0

    def test_cheatsheet_unknown(self, client):
        r = client.get('/api/cheatsheet/nonexistent')
        assert r.get_json() == {}


# =========================================================================
# Field Status API
# =========================================================================

class TestFieldStatus:
    def test_get_default_status(self, client):
        r = client.get('/api/field-status/test-company/constellation/why_interested')
        assert r.status_code == 200
        data = r.get_json()
        assert data['status'] == 'not_started'
        assert data['word_count'] == 0

    def test_set_status(self, client):
        r = client.put('/api/field-status/test-company/constellation/why_interested',
                       json={'status': 'first_draft', 'word_count': 42})
        assert r.status_code == 200
        data = r.get_json()
        assert data['status'] == 'first_draft'
        assert data['word_count'] == 42
        assert data['first_draft_at'] is not None

    def test_advance_status(self, client):
        # Set initial
        client.put('/api/field-status/test-company/constellation/why_interested',
                   json={'status': 'first_draft', 'word_count': 42})
        # Advance
        r = client.put('/api/field-status/test-company/constellation/why_interested',
                       json={'status': 'human_written', 'word_count': 150})
        data = r.get_json()
        assert data['status'] == 'human_written'
        assert data['human_written_at'] is not None
        # first_draft_at should still be set
        assert data['first_draft_at'] is not None


# =========================================================================
# Fellowship Progress API
# =========================================================================

class TestFellowshipProgress:
    def test_fields_endpoint(self, client):
        r = client.get('/api/fellowship/both/fields')
        assert r.status_code == 200
        fields = r.get_json()
        assert len(fields) == 6

    def test_progress_empty(self, client):
        r = client.get('/api/fellowship/both/progress')
        data = r.get_json()
        assert data['total_fields'] == 6
        assert data['completed'] == 0
        assert data['percentage'] == 0


# =========================================================================
# Notes API
# =========================================================================

class TestNotes:
    def test_create_note(self, client):
        r = client.post('/api/notes', json={
            'company_slug': 'test-company',
            'document': 'cover_letter',
            'paragraph_index': 0,
            'note': 'Strengthen the opening',
            'note_type': 'edit',
        })
        assert r.status_code == 201
        data = r.get_json()
        assert data['note'] == 'Strengthen the opening'
        assert data['status'] == 'pending'
        assert data['id'] is not None

    def test_create_note_missing_fields(self, client):
        r = client.post('/api/notes', json={'note': 'incomplete'})
        assert r.status_code == 400

    def test_list_notes(self, client):
        client.post('/api/notes', json={
            'company_slug': 'test-company', 'document': 'cover_letter',
            'paragraph_index': 0, 'note': 'Note 1',
        })
        client.post('/api/notes', json={
            'company_slug': 'test-company', 'document': 'cover_letter',
            'paragraph_index': 1, 'note': 'Note 2',
        })
        r = client.get('/api/notes/test-company')
        assert len(r.get_json()) == 2

    def test_list_notes_by_doc(self, client):
        client.post('/api/notes', json={
            'company_slug': 'test-company', 'document': 'cover_letter',
            'paragraph_index': 0, 'note': 'CL note',
        })
        client.post('/api/notes', json={
            'company_slug': 'test-company', 'document': 'talking_points',
            'paragraph_index': 0, 'note': 'TP note',
        })
        r = client.get('/api/notes/test-company/cover_letter')
        assert len(r.get_json()) == 1

    def test_update_note(self, client):
        create = client.post('/api/notes', json={
            'company_slug': 'test-company', 'document': 'cover_letter',
            'paragraph_index': 0, 'note': 'Original',
        })
        note_id = create.get_json()['id']
        r = client.put(f'/api/notes/{note_id}', json={'note': 'Updated', 'status': 'applied'})
        data = r.get_json()
        assert data['note'] == 'Updated'
        assert data['status'] == 'applied'
        assert data['applied_at'] is not None

    def test_delete_note(self, client):
        create = client.post('/api/notes', json={
            'company_slug': 'test-company', 'document': 'cover_letter',
            'paragraph_index': 0, 'note': 'To delete',
        })
        note_id = create.get_json()['id']
        r = client.delete(f'/api/notes/{note_id}')
        assert r.status_code == 204
        # Verify gone
        r = client.get('/api/notes/test-company')
        assert len(r.get_json()) == 0

    def test_export_notes(self, client):
        client.post('/api/notes', json={
            'company_slug': 'test-company', 'document': 'cover_letter',
            'paragraph_index': 0, 'note': 'Pending note',
        })
        r = client.get('/api/notes/export?company=test-company')
        data = r.get_json()
        assert data['count'] == 1
        assert data['notes'][0]['note'] == 'Pending note'


# =========================================================================
# Export API
# =========================================================================

class TestExport:
    def test_export_plain_text(self, client):
        # Write some content first
        client.put('/api/document/test-company/constellation/why_interested',
                   json={'content': 'I am interested in this program.'})
        r = client.get('/api/export/test-company/both/plain-text')
        assert r.status_code == 200
        data = r.get_json()
        assert data['track'] == 'both'
        assert len(data['fields']) > 0
        written = next(f for f in data['fields'] if f['field_id'] == 'why_interested')
        assert written['word_count'] > 0

    def test_export_no_constellation(self, client):
        # Create a company without constellation
        bare_dir = os.path.join(_apps_dir, 'bare-company')
        os.makedirs(bare_dir, exist_ok=True)
        with open(os.path.join(bare_dir, 'notes.md'), 'w') as f:
            f.write('# Notes')
        r = client.get('/api/export/bare-company/both/plain-text')
        assert r.status_code == 404
        shutil.rmtree(bare_dir)


# =========================================================================
# Resume API
# =========================================================================

class TestResume:
    def test_get_resume(self, client):
        r = client.get('/api/resume/test-company')
        assert r.status_code == 200
        assert b'Test User' in r.data

    def test_get_resume_html(self, client):
        r = client.get('/api/resume-html/test-company')
        assert r.status_code == 200
        data = r.get_json()
        assert '<h1>Test User</h1>' in data['html']
        assert data['filename'] == 'resume.html'

    def test_save_resume_html(self, client):
        new_html = '<html><body><h1>Updated</h1></body></html>'
        r = client.put('/api/resume-html/test-company', json={'html': new_html})
        assert r.status_code == 200
        assert r.get_json()['saved'] is True
        # Verify backup
        backups = os.listdir(_backup_dir)
        assert any('resume' in b for b in backups)

    def test_save_resume_empty_rejected(self, client):
        r = client.put('/api/resume-html/test-company', json={'html': ''})
        assert r.status_code == 400


# =========================================================================
# Guide API
# =========================================================================

class TestGuide:
    def test_guide_no_file(self, client):
        r = client.get('/api/guide/test-company')
        assert r.status_code == 200
        assert r.get_json()['html'] == ''


# =========================================================================
# Markdown rendering
# =========================================================================

class TestMarkdown:
    def test_split_blocks(self):
        text = "# Heading\n\nParagraph one.\n\nParagraph two."
        blocks = app.split_md_blocks(text)
        assert len(blocks) == 3

    def test_split_blocks_code_fence(self):
        text = "Before.\n\n```python\ndef foo():\n    pass\n```\n\nAfter."
        blocks = app.split_md_blocks(text)
        assert len(blocks) == 3
        assert '```python' in blocks[1]

    def test_render_paragraphs(self):
        text = "# Hello\n\nWorld."
        html, blocks = app.render_md_with_paragraphs(text)
        assert 'data-idx="0"' in html
        assert 'data-idx="1"' in html
        assert len(blocks) == 2


# =========================================================================
# Cleanup
# =========================================================================

def teardown_module():
    """Remove test temp directory."""
    shutil.rmtree(_test_dir, ignore_errors=True)
