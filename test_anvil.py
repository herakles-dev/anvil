"""
Anvil test suite.

Run:   pytest test_anvil.py -v
Cover: pytest test_anvil.py --cov=app --cov-report=term-missing
"""

import json
import os
import shutil
import tempfile
from unittest.mock import patch

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

import app  # noqa: E402 — must import after env setup


# =========================================================================
# Fixtures
# =========================================================================

def _setup_test_company():
    """Create a test company with all document types."""
    company_dir = os.path.join(_apps_dir, 'test-company')
    constellation_dir = os.path.join(company_dir, 'constellation')
    resume_dir = os.path.join(company_dir, 'resume')
    os.makedirs(constellation_dir, exist_ok=True)
    os.makedirs(resume_dir, exist_ok=True)

    with open(os.path.join(company_dir, 'meta.json'), 'w') as f:
        json.dump({
            'company': 'Test Company',
            'role': 'Test Role',
            'status': 'PREPARING',
            'salary_range': '$100K',
            'deadline': '2026-12-01',
            'apply_url': 'https://example.com/apply',
        }, f)

    with open(os.path.join(company_dir, 'cover_letter.md'), 'w') as f:
        f.write('# Cover Letter\n\nDear Hiring Team,\n\nI am writing to apply.\n\nBest regards,\nTest User')

    with open(os.path.join(company_dir, 'talking_points.md'), 'w') as f:
        f.write('# Talking Points\n\n## Why This Company\n\n- Great mission')

    for field in ('why_interested', 'relevant_background', 'anything_else'):
        with open(os.path.join(constellation_dir, f'{field}.md'), 'w') as f:
            f.write('')

    # Non-.md file should be ignored
    with open(os.path.join(constellation_dir, 'notes.txt'), 'w') as f:
        f.write('ignored')

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


@pytest.fixture
def client():
    """Flask test client with fresh test data."""
    _setup_test_company()
    _setup_test_evidence()
    app.app.config['TESTING'] = True
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
        assert company['status'] == 'PREPARING'
        assert company['salary'] == '$100K'
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

    def test_company_without_meta_json(self, client):
        """Company without meta.json uses slug-derived defaults."""
        bare_dir = os.path.join(_apps_dir, 'bare-company')
        os.makedirs(bare_dir, exist_ok=True)
        with open(os.path.join(bare_dir, 'notes.md'), 'w') as f:
            f.write('# Notes')
        r = client.get('/api/companies')
        bare = next(c for c in r.get_json() if c['slug'] == 'bare-company')
        assert bare['name'] == 'Bare Company'
        assert bare['has_constellation'] is False
        shutil.rmtree(bare_dir)

    def test_company_without_constellation(self, client):
        """Company without constellation/ directory returns has_constellation=False."""
        no_const_dir = os.path.join(_apps_dir, 'no-const')
        os.makedirs(no_const_dir, exist_ok=True)
        with open(os.path.join(no_const_dir, 'letter.md'), 'w') as f:
            f.write('# Letter')
        r = client.get('/api/companies')
        nc = next(c for c in r.get_json() if c['slug'] == 'no-const')
        assert nc['has_constellation'] is False
        shutil.rmtree(no_const_dir)

    def test_pending_notes_count(self, client):
        """Pending notes count updates after creating notes."""
        client.post('/api/notes', json={
            'company_slug': 'test-company', 'document': 'cover_letter',
            'paragraph_index': 0, 'note': 'Fix this',
        })
        r = client.get('/api/companies')
        company = next(c for c in r.get_json() if c['slug'] == 'test-company')
        assert company['pending_notes'] == 1


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

    def test_get_document_404_bad_company(self, client):
        r = client.get('/api/document/nonexistent/cover_letter')
        assert r.status_code == 404

    def test_get_document_404_bad_doc(self, client):
        r = client.get('/api/document/test-company/nonexistent')
        assert r.status_code == 404

    def test_save_document(self, client):
        new_content = '# Updated Letter\n\nNew content here.'
        r = client.put('/api/document/test-company/cover_letter',
                       json={'content': new_content})
        assert r.status_code == 200
        data = r.get_json()
        assert data['raw'] == new_content
        backups = os.listdir(_backup_dir)
        assert any('cover_letter' in b for b in backups)

    def test_save_document_404_bad_company(self, client):
        r = client.put('/api/document/nonexistent/cover_letter',
                       json={'content': 'test'})
        assert r.status_code == 404

    def test_save_document_404_bad_doc(self, client):
        r = client.put('/api/document/test-company/nonexistent',
                       json={'content': 'test'})
        assert r.status_code == 404

    def test_save_empty_rejected(self, client):
        r = client.put('/api/document/test-company/cover_letter',
                       json={'content': '   '})
        assert r.status_code == 400

    def test_save_block(self, client):
        r = client.put('/api/document/test-company/cover_letter/block/1',
                       json={'content': 'Updated paragraph.'})
        assert r.status_code == 200
        assert 'Updated paragraph.' in r.get_json()['raw']

    def test_save_block_delete(self, client):
        """Empty content deletes the block."""
        r = client.put('/api/document/test-company/cover_letter/block/1',
                       json={'content': ''})
        assert r.status_code == 200
        assert 'Dear Hiring Team' not in r.get_json()['raw']

    def test_save_block_out_of_range(self, client):
        r = client.put('/api/document/test-company/cover_letter/block/999',
                       json={'content': 'nope'})
        assert r.status_code == 400

    def test_save_block_creates_backup(self, client):
        client.put('/api/document/test-company/cover_letter/block/0',
                   json={'content': '# New Heading'})
        backups = os.listdir(_backup_dir)
        assert any('cover_letter' in b for b in backups)


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

    def test_save_constellation_creates_backup(self, client):
        client.put('/api/document/test-company/constellation/why_interested',
                   json={'content': 'Draft text.'})
        backups = os.listdir(_backup_dir)
        assert any('constellation' in b for b in backups)

    def test_constellation_404_bad_field(self, client):
        r = client.get('/api/document/test-company/constellation/nonexistent')
        assert r.status_code == 404

    def test_constellation_404_bad_company(self, client):
        r = client.get('/api/document/nonexistent/constellation/why_interested')
        assert r.status_code == 404

    def test_save_constellation_404(self, client):
        r = client.put('/api/document/test-company/constellation/nonexistent',
                       json={'content': 'test'})
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

    def test_evidence_search_by_heading(self, client):
        """Search matches heading text too."""
        r = client.get('/api/evidence/search?q=Project Alpha')
        results = r.get_json()
        assert len(results) >= 1

    def test_evidence_search_empty(self, client):
        r = client.get('/api/evidence/search?q=')
        assert r.get_json() == []

    def test_evidence_search_no_results(self, client):
        r = client.get('/api/evidence/search?q=xyznonexistent')
        assert r.get_json() == []

    def test_evidence_search_truncates_text(self, client):
        """Results text is truncated to 500 chars."""
        r = client.get('/api/evidence/search?q=project')
        results = r.get_json()
        for result in results:
            assert len(result['text']) <= 500

    def test_evidence_stats(self, client):
        r = client.get('/api/evidence/stats')
        assert r.status_code == 200
        data = r.get_json()
        assert len(data) >= 2
        metrics = [s['metric'] for s in data]
        assert 'Lines of code' in metrics

    def test_evidence_stats_no_evidence_dir(self, client):
        """Stats returns empty when EVIDENCE_DIR is not set."""
        original = app.EVIDENCE_DIR
        app.EVIDENCE_DIR = ''
        r = client.get('/api/evidence/stats')
        assert r.get_json() == []
        app.EVIDENCE_DIR = original

    def test_evidence_stats_no_stats_file(self, client):
        """Stats returns empty when platform-stats.md doesn't exist."""
        os.remove(os.path.join(_evidence_dir, 'platform-stats.md'))
        r = client.get('/api/evidence/stats')
        assert r.get_json() == []
        # Recreate for other tests
        _setup_test_evidence()

    def test_evidence_empty_dir(self, client):
        """Evidence returns empty when no .md files exist."""
        original = app.EVIDENCE_DIR
        empty_dir = os.path.join(_test_dir, 'empty-evidence')
        os.makedirs(empty_dir, exist_ok=True)
        app.EVIDENCE_DIR = empty_dir
        app._evidence_cache['data'] = None
        r = client.get('/api/evidence')
        assert r.get_json() == []
        app.EVIDENCE_DIR = original
        app._evidence_cache['data'] = None
        shutil.rmtree(empty_dir)

    def test_evidence_no_dir(self, client):
        """Evidence returns empty when EVIDENCE_DIR is not set."""
        original = app.EVIDENCE_DIR
        app.EVIDENCE_DIR = ''
        app._evidence_cache['data'] = None
        r = client.get('/api/evidence')
        assert r.get_json() == []
        app.EVIDENCE_DIR = original
        app._evidence_cache['data'] = None

    def test_evidence_cache_hit(self, client):
        """Second call uses cache (no re-parse)."""
        client.get('/api/evidence')  # populate cache
        assert app._evidence_cache['data'] is not None
        # Second call should use cache
        r = client.get('/api/evidence')
        assert r.status_code == 200

    def test_evidence_cache_invalidation(self, client):
        r1 = client.get('/api/evidence')
        assert len(r1.get_json()) == 2
        with open(os.path.join(_evidence_dir, 'new-file.md'), 'w') as f:
            f.write('# New\n\n## Section\n\nContent.')
        app._evidence_cache['data'] = None
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
        assert 'evidence_to_cite' in data

    def test_cheatsheet_has_content(self, client):
        r = client.get('/api/cheatsheet/why_interested')
        data = r.get_json()
        assert len(data['what_to_hit']) > 0
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
        client.put('/api/field-status/test-company/constellation/why_interested',
                   json={'status': 'first_draft', 'word_count': 42})
        r = client.put('/api/field-status/test-company/constellation/why_interested',
                       json={'status': 'human_written', 'word_count': 150})
        data = r.get_json()
        assert data['status'] == 'human_written'
        assert data['human_written_at'] is not None
        assert data['first_draft_at'] is not None

    def test_status_final_records_timestamp(self, client):
        client.put('/api/field-status/test-company/constellation/why_interested',
                   json={'status': 'first_draft', 'word_count': 42})
        r = client.put('/api/field-status/test-company/constellation/why_interested',
                       json={'status': 'final', 'word_count': 200})
        data = r.get_json()
        assert data['status'] == 'final'
        assert data['final_at'] is not None

    def test_get_existing_status(self, client):
        """GET returns persisted data after PUT."""
        client.put('/api/field-status/test-company/constellation/why_interested',
                   json={'status': 'human_written', 'word_count': 100})
        r = client.get('/api/field-status/test-company/constellation/why_interested')
        data = r.get_json()
        assert data['status'] == 'human_written'
        assert data['word_count'] == 100

    def test_set_not_started_no_timestamp(self, client):
        """Setting not_started doesn't record a timestamp."""
        r = client.put('/api/field-status/test-company/constellation/why_interested',
                       json={'status': 'not_started', 'word_count': 0})
        data = r.get_json()
        assert data['first_draft_at'] is None


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

    def test_progress_with_completed(self, client):
        """Progress reflects status changes."""
        client.put('/api/field-status/test-company/constellation/why_interested',
                   json={'status': 'final', 'word_count': 200})
        client.put('/api/field-status/test-company/constellation/relevant_background',
                   json={'status': 'first_draft', 'word_count': 50})
        r = client.get('/api/fellowship/both/progress')
        data = r.get_json()
        assert data['completed'] == 1
        assert data['drafted'] == 1
        assert data['not_started'] == 4


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
        assert data['created_at'] is not None

    def test_create_note_default_type(self, client):
        """Omitting note_type defaults to 'edit'."""
        r = client.post('/api/notes', json={
            'company_slug': 'test-company', 'document': 'cover_letter',
            'paragraph_index': 0, 'note': 'Fix this',
        })
        assert r.get_json()['note_type'] == 'edit'

    def test_create_note_missing_fields(self, client):
        r = client.post('/api/notes', json={'note': 'incomplete'})
        assert r.status_code == 400
        assert 'Missing' in r.get_json()['error']

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
        notes = r.get_json()
        assert len(notes) == 1
        assert notes[0]['document'] == 'cover_letter'

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

    def test_update_note_empty_body(self, client):
        """Update with no fields returns 400."""
        create = client.post('/api/notes', json={
            'company_slug': 'test-company', 'document': 'cover_letter',
            'paragraph_index': 0, 'note': 'Original',
        })
        note_id = create.get_json()['id']
        r = client.put(f'/api/notes/{note_id}', json={})
        assert r.status_code == 400

    def test_delete_note(self, client):
        create = client.post('/api/notes', json={
            'company_slug': 'test-company', 'document': 'cover_letter',
            'paragraph_index': 0, 'note': 'To delete',
        })
        note_id = create.get_json()['id']
        r = client.delete(f'/api/notes/{note_id}')
        assert r.status_code == 204
        r = client.get('/api/notes/test-company')
        assert len(r.get_json()) == 0

    def test_export_notes_with_company(self, client):
        client.post('/api/notes', json={
            'company_slug': 'test-company', 'document': 'cover_letter',
            'paragraph_index': 0, 'note': 'Pending note',
        })
        r = client.get('/api/notes/export?company=test-company')
        data = r.get_json()
        assert data['count'] == 1
        assert data['notes'][0]['note'] == 'Pending note'
        assert 'exported_at' in data

    def test_export_notes_all(self, client):
        """Export without company filter returns all pending notes."""
        client.post('/api/notes', json={
            'company_slug': 'test-company', 'document': 'cover_letter',
            'paragraph_index': 0, 'note': 'Note 1',
        })
        r = client.get('/api/notes/export')
        assert r.get_json()['count'] == 1

    def test_export_excludes_applied(self, client):
        """Applied notes are excluded from export."""
        create = client.post('/api/notes', json={
            'company_slug': 'test-company', 'document': 'cover_letter',
            'paragraph_index': 0, 'note': 'Applied note',
        })
        note_id = create.get_json()['id']
        client.put(f'/api/notes/{note_id}', json={'status': 'applied'})
        r = client.get('/api/notes/export?company=test-company')
        assert r.get_json()['count'] == 0


# =========================================================================
# Export API
# =========================================================================

class TestExport:
    def test_export_plain_text(self, client):
        client.put('/api/document/test-company/constellation/why_interested',
                   json={'content': 'I am interested in this program.'})
        r = client.get('/api/export/test-company/both/plain-text')
        assert r.status_code == 200
        data = r.get_json()
        assert data['track'] == 'both'
        assert len(data['fields']) > 0
        written = next(f for f in data['fields'] if f['field_id'] == 'why_interested')
        assert written['word_count'] > 0
        assert written['word_min'] > 0
        assert written['word_max'] > 0

    def test_export_no_constellation(self, client):
        bare_dir = os.path.join(_apps_dir, 'bare-company')
        os.makedirs(bare_dir, exist_ok=True)
        with open(os.path.join(bare_dir, 'notes.md'), 'w') as f:
            f.write('# Notes')
        r = client.get('/api/export/bare-company/both/plain-text')
        assert r.status_code == 404
        shutil.rmtree(bare_dir)

    def test_export_field_ordering(self, client):
        """Export fields are ordered by config order."""
        r = client.get('/api/export/test-company/both/plain-text')
        data = r.get_json()
        orders = [app.CONSTELLATION_FIELDS[f['field_id']]['order'] for f in data['fields']]
        assert orders == sorted(orders)

    def test_email_export_no_smtp(self, client):
        """Email export returns 500 when SMTP is not configured."""
        r = client.post('/api/export/test-company/both/email')
        assert r.status_code == 500
        assert 'SMTP' in r.get_json()['error']


# =========================================================================
# Resume API
# =========================================================================

class TestResume:
    def test_get_resume(self, client):
        r = client.get('/api/resume/test-company')
        assert r.status_code == 200
        assert b'Test User' in r.data

    def test_get_resume_404(self, client):
        r = client.get('/api/resume/nonexistent')
        assert r.status_code == 404

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
        backups = os.listdir(_backup_dir)
        assert any('resume' in b for b in backups)

    def test_save_resume_persists(self, client):
        """Saved HTML persists across reads."""
        new_html = '<html><body><h1>Persisted</h1></body></html>'
        client.put('/api/resume-html/test-company', json={'html': new_html})
        r = client.get('/api/resume-html/test-company')
        assert 'Persisted' in r.get_json()['html']

    def test_save_resume_empty_rejected(self, client):
        r = client.put('/api/resume-html/test-company', json={'html': ''})
        assert r.status_code == 400

    def test_resume_pdf_404_no_pdf(self, client):
        """PDF download returns 404 when no .pdf file exists."""
        r = client.get('/api/resume/test-company/pdf')
        assert r.status_code == 404

    def test_resume_pdf_download(self, client):
        """PDF download works when .pdf file exists."""
        resume_dir = os.path.join(_apps_dir, 'test-company', 'resume')
        with open(os.path.join(resume_dir, 'resume.pdf'), 'wb') as f:
            f.write(b'%PDF-1.4 fake pdf content')
        r = client.get('/api/resume/test-company/pdf')
        assert r.status_code == 200
        os.remove(os.path.join(resume_dir, 'resume.pdf'))

    def test_resume_pdf_generate_no_chromium(self, client):
        """PDF generation returns 500 when Chromium is not available."""
        original = app.CHROMIUM_PATH
        app.CHROMIUM_PATH = '/nonexistent/chromium'
        r = client.post('/api/resume-html/test-company/pdf')
        assert r.status_code == 500
        assert 'PDF generation failed' in r.get_json()['error']
        app.CHROMIUM_PATH = original

    def test_resume_import_no_fellowship_dir(self, client):
        """Import returns empty when FELLOWSHIP_DIR is not set."""
        r = client.get('/api/resume-import/test-company')
        data = r.get_json()
        assert data['html'] == ''
        assert data['source'] is None

    def test_resume_import_with_fellowship_dir(self, client):
        """Import returns HTML when fellowship dir has a resume file."""
        fellowship_dir = os.path.join(_test_dir, 'fellowship')
        os.makedirs(fellowship_dir, exist_ok=True)
        with open(os.path.join(fellowship_dir, 'resume.html'), 'w') as f:
            f.write('<html><body>Fellowship Resume</body></html>')
        original = app.FELLOWSHIP_DIR
        app.FELLOWSHIP_DIR = fellowship_dir
        r = client.get('/api/resume-import/test-company')
        data = r.get_json()
        assert 'Fellowship Resume' in data['html']
        assert data['source'] == 'fellowship'
        app.FELLOWSHIP_DIR = original
        shutil.rmtree(fellowship_dir)


# =========================================================================
# Guide API
# =========================================================================

class TestGuide:
    def test_guide_no_file(self, client):
        r = client.get('/api/guide/test-company')
        assert r.status_code == 200
        assert r.get_json()['html'] == ''

    def test_guide_with_file(self, client):
        """Guide returns rendered HTML when submission_guide.md exists."""
        guide_path = os.path.join(_apps_dir, 'submission_guide.md')
        with open(guide_path, 'w') as f:
            f.write('# Guide\n\n==========\n\ntest-company section\n\n## Steps\n\n1. Apply\n2. Wait')
        r = client.get('/api/guide/test-company')
        data = r.get_json()
        assert data['html'] != ''
        assert 'Steps' in data['raw']
        os.remove(guide_path)

    def test_guide_company_not_found(self, client):
        """Guide returns empty when company section not found."""
        guide_path = os.path.join(_apps_dir, 'submission_guide.md')
        with open(guide_path, 'w') as f:
            f.write('# Guide\n\n==========\n\nother-company section')
        r = client.get('/api/guide/test-company')
        assert r.get_json()['html'] == ''
        os.remove(guide_path)


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

    def test_split_blocks_empty(self):
        assert app.split_md_blocks('') == []
        assert app.split_md_blocks('   \n\n  ') == []

    def test_split_blocks_single(self):
        blocks = app.split_md_blocks('Just one paragraph.')
        assert len(blocks) == 1

    def test_split_blocks_preserves_list(self):
        text = "# Heading\n\n- Item 1\n- Item 2\n- Item 3"
        blocks = app.split_md_blocks(text)
        assert len(blocks) == 2  # heading + list

    def test_render_paragraphs(self):
        text = "# Hello\n\nWorld."
        html, blocks = app.render_md_with_paragraphs(text)
        assert 'data-idx="0"' in html
        assert 'data-idx="1"' in html
        assert len(blocks) == 2

    def test_render_paragraphs_escapes_raw_attribute(self):
        """Raw content in data-raw attribute is HTML-escaped to prevent injection."""
        text = '# Hello <script>alert("xss")</script>'
        html, _ = app.render_md_with_paragraphs(text)
        # The data-raw attribute must have escaped angle brackets
        assert '&lt;script&gt;' in html
        assert 'data-raw="# Hello &lt;script&gt;' in html

    def test_render_paragraphs_empty(self):
        html, blocks = app.render_md_with_paragraphs('')
        assert html == ''
        assert blocks == []


# =========================================================================
# Helper functions
# =========================================================================

class TestHelpers:
    def test_discover_companies_empty(self, client):
        """discover_companies returns empty when APPLICATIONS_DIR doesn't exist."""
        original = app.APPLICATIONS_DIR
        app.APPLICATIONS_DIR = '/nonexistent'
        assert app.discover_companies() == []
        app.APPLICATIONS_DIR = original

    def test_get_company_documents_nonexistent(self, client):
        """get_company_documents returns empty for nonexistent company."""
        assert app.get_company_documents('nonexistent') == []

    def test_get_company_meta_no_file(self, client):
        """get_company_meta returns {} when no meta.json."""
        bare_dir = os.path.join(_apps_dir, 'no-meta')
        os.makedirs(bare_dir, exist_ok=True)
        with open(os.path.join(bare_dir, 'doc.md'), 'w') as f:
            f.write('# Doc')
        assert app.get_company_meta('no-meta') == {}
        shutil.rmtree(bare_dir)

    def test_has_constellation(self, client):
        assert app._has_constellation('test-company') is True

    def test_has_no_constellation(self, client):
        bare_dir = os.path.join(_apps_dir, 'no-const')
        os.makedirs(bare_dir, exist_ok=True)
        with open(os.path.join(bare_dir, 'doc.md'), 'w') as f:
            f.write('# Doc')
        assert app._has_constellation('no-const') is False
        shutil.rmtree(bare_dir)

    def test_backup_creates_file(self, client):
        """_backup creates a timestamped copy."""
        filepath = os.path.join(_apps_dir, 'test-company', 'cover_letter.md')
        app._backup(filepath, 'test-company', 'cover_letter')
        backups = os.listdir(_backup_dir)
        assert len(backups) >= 1
        assert any('test-company__cover_letter__' in b for b in backups)

    def test_build_export_data_no_constellation(self, client):
        """_build_export_data returns None when no constellation/ exists."""
        assert app._build_export_data('nonexistent', 'both') is None

    def test_build_export_data_fields(self, client):
        """_build_export_data includes all matching fields."""
        data = app._build_export_data('test-company', 'both')
        assert data is not None
        assert data['track'] == 'both'
        assert len(data['fields']) > 0


# =========================================================================
# Edit History API
# =========================================================================

class TestEditHistory:
    def test_history_recorded_on_save(self, client):
        """Saving a document creates an edit history entry."""
        client.put('/api/document/test-company/cover_letter',
                   json={'content': '# Updated\n\nNew content.'})
        r = client.get('/api/document/test-company/cover_letter/history')
        assert r.status_code == 200
        history = r.get_json()
        assert len(history) >= 1
        assert history[0]['source'] == 'browser'
        assert history[0]['company_slug'] == 'test-company'
        assert history[0]['document'] == 'cover_letter'

    def test_history_word_count(self, client):
        """History tracks word count before and after."""
        client.put('/api/document/test-company/cover_letter',
                   json={'content': 'three word doc'})
        r = client.get('/api/document/test-company/cover_letter/history')
        entry = r.get_json()[0]
        assert entry['word_count_after'] == 3
        assert entry['word_count_before'] > 0  # had content before

    def test_history_trimming(self, client):
        """History trims to 50 entries per document."""
        for i in range(55):
            client.put('/api/document/test-company/cover_letter',
                       json={'content': f'Version {i} content here.'})
        r = client.get('/api/document/test-company/cover_letter/history')
        # API returns max 20, but DB should have max 50
        history = r.get_json()
        assert len(history) <= 20  # endpoint limits to 20

    def test_history_empty(self, client):
        """History returns empty list for document with no edits."""
        r = client.get('/api/document/test-company/talking_points/history')
        assert r.status_code == 200
        assert r.get_json() == []

    def test_history_404_bad_company(self, client):
        """History returns 404 for nonexistent company."""
        r = client.get('/api/document/nonexistent/cover_letter/history')
        assert r.status_code == 404

    def test_check_endpoint(self, client):
        """Check endpoint returns mtime and external_edit flag."""
        # First load the document (sets _served_mtimes)
        client.get('/api/document/test-company/cover_letter')
        r = client.get('/api/document/test-company/cover_letter/check')
        assert r.status_code == 200
        data = r.get_json()
        assert 'mtime' in data
        assert 'external_edit' in data

    def test_external_edit_detection(self, client):
        """Check detects external file modification."""
        import time
        # Load document to set baseline mtime
        client.get('/api/document/test-company/cover_letter')
        # Simulate CLI edit by writing directly to file
        time.sleep(0.1)  # ensure mtime changes
        filepath = os.path.join(_apps_dir, 'test-company', 'cover_letter.md')
        with open(filepath, 'w') as f:
            f.write('# CLI Edited\n\nThis was changed by CLI.')
        r = client.get('/api/document/test-company/cover_letter/check')
        data = r.get_json()
        assert data['external_edit'] is True

    def test_constellation_field_history(self, client):
        """Constellation field saves are recorded in history."""
        client.put('/api/document/test-company/constellation/why_interested',
                   json={'content': 'I am very interested.'})
        r = client.get('/api/document/test-company/constellation/why_interested/history')
        assert r.status_code == 200
        history = r.get_json()
        assert len(history) >= 1
        assert 'constellation' in history[0]['document']

    def test_check_404_bad_company(self, client):
        """Check returns 404 for nonexistent company."""
        r = client.get('/api/document/nonexistent/cover_letter/check')
        assert r.status_code == 404


# =========================================================================
# Versions API
# =========================================================================

class TestVersions:
    def test_list_versions(self, client):
        """Saving creates a backup visible in versions list."""
        client.put('/api/document/test-company/cover_letter',
                   json={'content': '# Backup Test\n\nContent.'})
        r = client.get('/api/document/test-company/cover_letter/versions')
        assert r.status_code == 200
        versions = r.get_json()
        assert len(versions) >= 1
        assert 'filename' in versions[0]
        assert 'size' in versions[0]

    def test_restore_version(self, client):
        """Restoring a version replaces current content."""
        # Save twice to create a backup of original
        original_content = '# Original\n\nOriginal content.'
        client.put('/api/document/test-company/cover_letter',
                   json={'content': original_content})
        # Get the backup filename
        r = client.get('/api/document/test-company/cover_letter/versions')
        versions = r.get_json()
        assert len(versions) >= 1
        backup_filename = versions[0]['filename']
        # Save again with different content
        client.put('/api/document/test-company/cover_letter',
                   json={'content': '# Changed\n\nDifferent content.'})
        # Restore from backup
        r = client.post('/api/document/test-company/cover_letter/restore',
                        json={'filename': backup_filename})
        assert r.status_code == 200
        # Verify the content contains something from the backup
        data = r.get_json()
        assert 'raw' in data
        assert 'html' in data

    def test_restore_path_traversal_blocked(self, client):
        """Path traversal in restore filename is blocked."""
        r = client.post('/api/document/test-company/cover_letter/restore',
                        json={'filename': '../../../etc/passwd'})
        assert r.status_code == 400

    def test_restore_nonexistent_backup(self, client):
        """Restoring nonexistent backup returns 404."""
        r = client.post('/api/document/test-company/cover_letter/restore',
                        json={'filename': 'nonexistent__backup__20990101_000000.md'})
        assert r.status_code == 404

    def test_restore_empty_filename(self, client):
        """Restoring with empty filename returns 400."""
        r = client.post('/api/document/test-company/cover_letter/restore',
                        json={'filename': ''})
        assert r.status_code == 400

    def test_versions_404_bad_company(self, client):
        """Versions returns 404 for nonexistent company."""
        r = client.get('/api/document/nonexistent/cover_letter/versions')
        assert r.status_code == 404

    def test_restore_404_bad_company(self, client):
        """Restore returns 404 for nonexistent company."""
        r = client.post('/api/document/nonexistent/cover_letter/restore',
                        json={'filename': 'test.md'})
        assert r.status_code == 404


# =========================================================================
# Cleanup
# =========================================================================

def teardown_module():
    """Remove test temp directory."""
    shutil.rmtree(_test_dir, ignore_errors=True)
