/**
 * Anvil — Application Writing Forge
 *
 * Client-side UI for drafting and reviewing application materials.
 * Designed for use alongside a CLI-based LLM (e.g. Claude Code):
 *   - You write and review in the browser
 *   - The LLM reads/writes the same markdown files on disk
 *   - Status tracking ensures Anthropic's "human first draft" policy compliance
 *
 * Keyboard shortcuts:
 *   Ctrl+S          — Save current document
 *   Ctrl+E          — Toggle evidence sidebar
 *   Ctrl+Shift+C    — Toggle cheat sheet / tips panel
 *   Ctrl+Shift+X    — Open export modal
 */

let state = {
  companies: [],
  activeCompany: null,
  activeDoc: null,
  notes: {},
  editMode: false,
  rawContent: '',
  blocks: [],
  dirty: false,
  fellowshipMode: false,
  evidenceVisible: false,
  evidenceData: null,
  cheatSheetVisible: false,
  fieldStatuses: {},
  resumeEditorMode: false,
};

const DOC_ICONS = {
  cover_letter: '\u2709',
  talking_points: '\u2328',
  project_highlights: '\u2605',
  form_answers: '\u2611',
  resume: '\u{1F4C4}',
  default: '\u2758',
};

const STATUS_CYCLE = ['not_started', 'first_draft', 'human_written', 'ai_refined', 'final'];
const STATUS_LABELS = {
  not_started: 'Not Started',
  first_draft: 'First Draft',
  human_written: 'Human Written',
  ai_refined: 'AI Refined',
  final: 'Final',
};
const STATUS_DOTS = {
  not_started: '\u25CB',    // empty circle
  first_draft: '\u25D2',    // half circle
  human_written: '\u25CF',  // full circle
  ai_refined: '\u2B24',     // large circle
  final: '\u2714',          // checkmark
};

function getDocIcon(id) {
  if (id && id.startsWith('constellation/')) return '\u2B50';
  return DOC_ICONS[id] || DOC_ICONS.default;
}

// --- Init ---

async function init() {
  const res = await fetch('/api/companies');
  state.companies = await res.json();
  renderTabs();

  const path = window.location.pathname;
  const match = path.match(/\/review\/(.+)/);
  const slug = match ? match[1] : state.companies[0]?.slug;
  if (slug) selectCompany(slug);

  // Global keyboard shortcuts
  document.addEventListener('keydown', (e) => {
    if (e.ctrlKey && e.key === 'e') {
      e.preventDefault();
      toggleEvidencePanel();
    }
    if (e.ctrlKey && e.shiftKey && e.key === 'C') {
      e.preventDefault();
      toggleCheatSheet();
    }
    if (e.ctrlKey && e.shiftKey && e.key === 'X') {
      e.preventDefault();
      if (state.fellowshipMode) showExportModal();
    }
  });
}

// --- Tab Bar ---

function renderTabs() {
  const bar = document.getElementById('tab-bar');
  bar.innerHTML = '';
  for (const c of state.companies) {
    const tab = document.createElement('button');
    tab.className = 'tab' + (c.slug === state.activeCompany ? ' active' : '');
    tab.textContent = c.name;
    tab.onclick = () => {
      if (state.dirty && !confirm('You have unsaved edits. Discard?')) return;
      state.dirty = false;
      history.pushState(null, '', `/review/${c.slug}`);
      selectCompany(c.slug);
    };
    if (c.pending_notes > 0) {
      const badge = document.createElement('span');
      badge.className = 'badge';
      badge.textContent = c.pending_notes;
      tab.appendChild(badge);
    }
    bar.appendChild(tab);
  }
}

// --- Company Selection ---

async function selectCompany(slug) {
  state.activeCompany = slug;
  state.activeDoc = null;
  state.editMode = false;
  state.resumeEditorMode = false;

  renderTabs();

  const notesRes = await fetch(`/api/notes/${slug}`);
  state.notes[slug] = await notesRes.json();

  const company = state.companies.find(c => c.slug === slug);

  // Detect fellowship mode
  state.fellowshipMode = !!(company?.has_constellation);

  const mainEl = document.querySelector('.main');
  if (state.fellowshipMode) {
    mainEl.classList.add('fellowship-mode');
  } else {
    mainEl.classList.remove('fellowship-mode');
  }

  renderSidebar(company);
  loadGuideBar(slug);

  // Load field statuses for fellowship mode
  if (state.fellowshipMode) {
    await loadFieldStatuses(slug);
  }

  if (company?.documents?.length > 0) {
    // In fellowship mode, select first constellation field
    if (state.fellowshipMode) {
      const firstField = company.documents.find(d => d.type === 'constellation');
      if (firstField) {
        selectDocument(firstField.id);
        return;
      }
    }
    const firstMd = company.documents.find(d => d.id !== 'resume');
    if (firstMd) selectDocument(firstMd.id);
  }
}

async function loadFieldStatuses(slug) {
  const company = state.companies.find(c => c.slug === slug);
  if (!company) return;
  for (const doc of company.documents) {
    if (doc.type === 'constellation') {
      try {
        const res = await fetch(`/api/field-status/${slug}/${doc.id}`);
        const data = await res.json();
        state.fieldStatuses[doc.id] = data;
      } catch (e) { /* ignore */ }
    }
  }
}

// --- Sidebar ---

function renderSidebar(company) {
  const sidebar = document.getElementById('sidebar-docs');
  const meta = document.getElementById('sidebar-meta');
  sidebar.innerHTML = '';

  if (!company) return;

  const notes = state.notes[company.slug] || [];

  if (state.fellowshipMode) {
    // Fellowship mode: grouped sidebar
    const regularDocs = company.documents.filter(d => d.type !== 'constellation' && d.id !== 'resume');
    const constellationDocs = company.documents.filter(d => d.type === 'constellation');
    const resumeDoc = company.documents.find(d => d.id === 'resume');

    // Progress summary
    const progressDiv = document.createElement('div');
    progressDiv.className = 'fellowship-progress';
    const totalFields = constellationDocs.length;
    const doneFields = constellationDocs.filter(d => {
      const s = state.fieldStatuses[d.id];
      return s && s.status === 'final';
    }).length;
    const pct = totalFields ? Math.round(doneFields / totalFields * 100) : 0;
    progressDiv.innerHTML = `
      <div class="progress-bar-container">
        <div class="progress-bar-fill" style="width: ${pct}%"></div>
      </div>
      <span class="progress-text">${doneFields}/${totalFields} fields complete (${pct}%)</span>
    `;
    sidebar.appendChild(progressDiv);

    // Constellation fields section
    if (constellationDocs.length > 0) {
      const sectionLabel = document.createElement('div');
      sectionLabel.className = 'sidebar-section';
      sectionLabel.innerHTML = '<span class="sidebar-section-icon">\u2B50</span> Constellation Fields';
      sidebar.appendChild(sectionLabel);

      for (const doc of constellationDocs) {
        const fieldStatus = state.fieldStatuses[doc.id]?.status || 'not_started';
        const item = document.createElement('div');
        item.className = 'doc-item' + (doc.id === state.activeDoc ? ' active' : '');
        item.onclick = () => {
          if (state.dirty && !confirm('You have unsaved edits. Discard?')) return;
          state.dirty = false;
          selectDocument(doc.id);
        };

        const dot = document.createElement('span');
        dot.className = `status-dot status-${fieldStatus}`;
        dot.textContent = STATUS_DOTS[fieldStatus];
        dot.title = STATUS_LABELS[fieldStatus];
        item.appendChild(dot);

        const label = document.createElement('span');
        label.className = 'doc-label-text';
        // Short label for sidebar
        const fieldId = doc.id.replace('constellation/', '');
        const shortLabels = {
          'why_interested': 'Why Interested',
          'excited_area': 'Excited Area',
          'safety_background': 'Safety Background',
          'accept_fulltime': 'Accept Full-time',
          'continue_safety': 'Continue Safety',
          'code_samples': 'Code Samples',
          'other_commitments': 'Other Commitments',
          'anything_else': 'Anything Else',
        };
        label.textContent = shortLabels[fieldId] || doc.label;
        label.style.flex = '1';
        item.appendChild(label);

        sidebar.appendChild(item);
      }
    }

    // Regular documents section
    if (regularDocs.length > 0) {
      const sectionLabel = document.createElement('div');
      sectionLabel.className = 'sidebar-section';
      sectionLabel.innerHTML = '<span class="sidebar-section-icon">\u2758</span> Materials';
      sidebar.appendChild(sectionLabel);

      for (const doc of regularDocs) {
        renderDocItem(doc, notes, sidebar);
      }
    }

    // Resume
    if (resumeDoc) {
      const sectionLabel = document.createElement('div');
      sectionLabel.className = 'sidebar-section';
      sectionLabel.innerHTML = '<span class="sidebar-section-icon">\u{1F4C4}</span> Resume';
      sidebar.appendChild(sectionLabel);
      renderDocItem(resumeDoc, notes, sidebar);
    }
  } else {
    // Standard mode
    for (const doc of company.documents) {
      renderDocItem(doc, notes, sidebar);
    }
  }

  const statusStr = (company.status || 'RESEARCHING').toLowerCase();
  meta.innerHTML = `
    <span class="meta-label">Position</span>
    <div class="meta-role">${escapeHtml(company.role || '')}</div>
    <div class="meta-salary">${escapeHtml(company.salary || '')}</div>
    <span class="meta-status ${statusStr}">${(company.status || 'RESEARCHING').toUpperCase()}</span>
  `;
}

function renderDocItem(doc, notes, container) {
  const item = document.createElement('div');
  item.className = 'doc-item' + (doc.id === state.activeDoc ? ' active' : '');
  item.onclick = () => {
    if (state.dirty && !confirm('You have unsaved edits. Discard?')) return;
    state.dirty = false;
    selectDocument(doc.id);
  };

  const icon = document.createElement('span');
  icon.className = 'doc-icon';
  icon.textContent = getDocIcon(doc.id);
  item.appendChild(icon);

  const label = document.createElement('span');
  label.style.flex = '1';
  label.textContent = doc.label;
  item.appendChild(label);

  const docNotes = notes.filter(n => n.document === doc.id && n.status === 'pending');
  if (docNotes.length > 0) {
    const count = document.createElement('span');
    count.className = 'note-count';
    count.textContent = docNotes.length;
    item.appendChild(count);
  }

  container.appendChild(item);
}

// --- Document Loading ---

async function selectDocument(docId) {
  state.activeDoc = docId;
  state.editMode = false;
  state.resumeEditorMode = false;
  state.dirty = false;
  const content = document.getElementById('content');

  renderSidebar(state.companies.find(c => c.slug === state.activeCompany));

  // Resume with editor
  if (docId === 'resume') {
    await loadResumeView();
    return;
  }

  // Constellation field
  if (docId.startsWith('constellation/')) {
    await loadConstellationField(docId);
    return;
  }

  const res = await fetch(`/api/document/${state.activeCompany}/${docId}`);
  if (!res.ok) {
    content.innerHTML = '<div class="empty-state"><h2>Document not found</h2></div>';
    return;
  }

  const data = await res.json();
  state.rawContent = data.raw;
  state.blocks = data.blocks || [];

  renderReviewMode(data.html);
}

// --- Constellation Field Loading ---

async function loadConstellationField(docId) {
  const content = document.getElementById('content');
  const fieldId = docId.replace('constellation/', '');
  const apiUrl = `/api/document/${state.activeCompany}/${docId}`;

  const res = await fetch(apiUrl);
  if (!res.ok) {
    content.innerHTML = '<div class="empty-state"><h2>Field not found</h2></div>';
    return;
  }

  const data = await res.json();
  state.rawContent = data.raw;
  state.blocks = data.blocks || [];

  const fieldConfig = data.field_config || {};
  const fieldStatus = state.fieldStatuses[docId]?.status || 'not_started';
  const wordCount = countWords(data.raw);

  // Load cheat sheet
  let cheatSheet = {};
  try {
    const csRes = await fetch(`/api/cheatsheet/${fieldId}`);
    cheatSheet = await csRes.json();
  } catch (e) { /* ignore */ }

  // Build the writing workspace
  content.innerHTML = `
    <div class="content-toolbar">
      <span class="doc-title">\u2B50 ${escapeHtml(fieldConfig.label || fieldId)}</span>
      <div class="toolbar-actions">
        <span class="field-status-pill status-${fieldStatus}" onclick="cycleFieldStatus()" title="Click to change status">
          ${STATUS_DOTS[fieldStatus]} ${STATUS_LABELS[fieldStatus]}
        </span>
        <button class="btn btn-ghost mode-btn" onclick="toggleCheatSheet()" title="Ctrl+Shift+C">Tips</button>
        <button class="btn btn-ghost mode-btn" onclick="toggleEvidencePanel()" title="Ctrl+E">Evidence</button>
        ${state.fellowshipMode ? '<button class="btn btn-ghost mode-btn" onclick="showExportModal()" title="Ctrl+Shift+X">Export</button>' : ''}
      </div>
    </div>

    ${fieldConfig.guidance ? `
    <div class="field-guide-callout">
      <div class="field-guide-header">
        <span class="field-guide-icon">\u{1F4CB}</span>
        <strong>What this field asks</strong>
      </div>
      <p>${escapeHtml(fieldConfig.guidance)}</p>
      <div class="field-guide-meta">
        <span class="field-guide-reviewer">\u{1F441} <strong>Reviewers want:</strong> ${escapeHtml(fieldConfig.reviewer_wants || '')}</span>
        <span class="field-guide-target">\u{1F3AF} Target: ${fieldConfig.word_min || '?'}\u2013${fieldConfig.word_max || '?'} words</span>
      </div>
    </div>` : ''}

    <div class="constellation-workspace">
      <div class="constellation-editor-area">
        <textarea id="constellation-editor" class="constellation-editor" spellcheck="true" placeholder="Start writing your response here...">${escapeHtml(state.rawContent)}</textarea>
        <div class="editor-footer">
          <span class="word-counter" id="word-counter">${formatWordCount(wordCount, fieldConfig.word_min, fieldConfig.word_max)}</span>
          <span class="save-status" id="save-status"></span>
          <button class="btn btn-primary" id="btn-save-field" onclick="saveConstellationField()">Save</button>
        </div>
      </div>

      <div class="cheat-sheet-panel" id="cheat-sheet-panel" style="display:none">
        ${renderCheatSheetHTML(cheatSheet)}
      </div>
    </div>
  `;

  // Setup editor events
  const editor = document.getElementById('constellation-editor');
  editor.addEventListener('input', () => {
    state.dirty = true;
    const wc = countWords(editor.value);
    document.getElementById('word-counter').innerHTML =
      formatWordCount(wc, fieldConfig.word_min, fieldConfig.word_max);
    document.getElementById('save-status').textContent = 'Unsaved changes';
    document.getElementById('save-status').className = 'save-status unsaved';
  });
  editor.addEventListener('keydown', (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key === 's') {
      e.preventDefault();
      saveConstellationField();
    }
  });
  editor.focus();

  // Show evidence panel if in right-panel container
  updateRightPanel();
}

function countWords(text) {
  const trimmed = (text || '').trim();
  if (!trimmed) return 0;
  return trimmed.split(/\s+/).length;
}

function formatWordCount(count, min, max) {
  let colorClass = 'word-count-ok';
  if (min && max) {
    if (count < min) colorClass = 'word-count-under';
    else if (count > max) colorClass = 'word-count-over';
    return `<span class="${colorClass}">${count}</span> / ${min}\u2013${max} words`;
  }
  return `${count} words`;
}

function renderCheatSheetHTML(sheet) {
  if (!sheet || !sheet.what_to_hit) return '<p class="cheat-empty">No tips for this field</p>';
  let html = '<div class="cheat-sheet-content">';
  html += '<h4>\u{1F3AF} What to hit</h4><ul>';
  for (const item of sheet.what_to_hit || []) {
    html += `<li>${escapeHtml(item)}</li>`;
  }
  html += '</ul>';
  html += '<h4>\u{1F4DA} Evidence to cite</h4><ul>';
  for (const item of sheet.evidence_to_cite || []) {
    html += `<li>${escapeHtml(item)}</li>`;
  }
  html += '</ul>';
  html += '<h4>\u{1F4A1} Tips</h4><ul>';
  for (const item of sheet.tips || []) {
    html += `<li>${escapeHtml(item)}</li>`;
  }
  html += '</ul></div>';
  return html;
}

async function saveConstellationField() {
  const editor = document.getElementById('constellation-editor');
  if (!editor) return;
  const newContent = editor.value;
  const statusEl = document.getElementById('save-status');
  statusEl.textContent = 'Saving...';
  statusEl.className = 'save-status saving';

  const res = await fetch(`/api/document/${state.activeCompany}/${state.activeDoc}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ content: newContent }),
  });

  if (res.ok) {
    const data = await res.json();
    state.rawContent = data.raw;
    state.blocks = data.blocks || [];
    state.dirty = false;
    statusEl.textContent = 'Saved';
    statusEl.className = 'save-status saved';
    showToast('Saved');
    setTimeout(() => { statusEl.textContent = ''; }, 2000);

    // Auto-update field status to first_draft if not_started
    const currentStatus = state.fieldStatuses[state.activeDoc]?.status || 'not_started';
    if (currentStatus === 'not_started' && newContent.trim()) {
      await updateFieldStatus('first_draft', data.word_count || countWords(newContent));
    }
  } else {
    statusEl.textContent = 'Save failed!';
    statusEl.className = 'save-status error';
  }
}


// --- Field Status ---

async function cycleFieldStatus() {
  const currentStatus = state.fieldStatuses[state.activeDoc]?.status || 'not_started';
  const currentIdx = STATUS_CYCLE.indexOf(currentStatus);
  const nextStatus = STATUS_CYCLE[(currentIdx + 1) % STATUS_CYCLE.length];
  const editor = document.getElementById('constellation-editor');
  const wc = editor ? countWords(editor.value) : 0;
  await updateFieldStatus(nextStatus, wc);
}

async function updateFieldStatus(newStatus, wordCount) {
  const res = await fetch(`/api/field-status/${state.activeCompany}/${state.activeDoc}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ status: newStatus, word_count: wordCount || 0 }),
  });

  if (res.ok) {
    const data = await res.json();
    state.fieldStatuses[state.activeDoc] = data;
    // Update pill
    const pill = document.querySelector('.field-status-pill');
    if (pill) {
      pill.className = `field-status-pill status-${newStatus}`;
      pill.innerHTML = `${STATUS_DOTS[newStatus]} ${STATUS_LABELS[newStatus]}`;
    }
    // Re-render sidebar to update dots
    renderSidebar(state.companies.find(c => c.slug === state.activeCompany));
    showToast(`Status: ${STATUS_LABELS[newStatus]}`);
  }
}


// --- Resume View ---

async function loadResumeView() {
  const content = document.getElementById('content');

  content.innerHTML = `
    <div class="content-toolbar">
      <span class="doc-title">${getDocIcon('resume')} Resume</span>
      <div class="toolbar-actions">
        <button class="btn btn-ghost mode-btn" id="btn-preview" onclick="switchResumeMode('preview')">Preview</button>
        <button class="btn btn-ghost mode-btn" id="btn-edit-resume" onclick="switchResumeMode('edit')">Edit HTML</button>
        <button class="btn btn-primary" onclick="generateResumePDF()">Generate PDF</button>
        <a href="/api/resume/${state.activeCompany}/pdf" class="btn btn-ghost" download>Download PDF</a>
      </div>
    </div>
    <div id="resume-body">
      <div class="resume-actions">
        <span style="color: var(--text-dim); font-size: 12px;">Preview mode. Click "Edit HTML" for split-pane editing.</span>
      </div>
      <iframe class="resume-frame" src="/api/resume/${state.activeCompany}"></iframe>
    </div>
    <div style="margin-top: 14px;">
      <div class="note-form" id="resume-note-form">
        <textarea id="resume-note-text" placeholder="Add notes about the resume..."></textarea>
        <div class="note-form-controls">
          <select id="resume-note-type">
            <option value="edit">Edit</option>
            <option value="rewrite">Rewrite</option>
            <option value="question">Question</option>
            <option value="approve">Approve</option>
          </select>
          <button class="btn btn-primary" onclick="saveResumeNote()">Save Note</button>
        </div>
      </div>
      <div id="resume-notes-list"></div>
    </div>`;
  renderResumeNotes();
}

async function switchResumeMode(mode) {
  if (mode === 'edit') {
    state.resumeEditorMode = true;
    const resumeBody = document.getElementById('resume-body');

    // Fetch raw HTML
    const res = await fetch(`/api/resume-html/${state.activeCompany}`);
    if (!res.ok) {
      showToast('Could not load resume HTML');
      return;
    }
    const data = await res.json();

    resumeBody.innerHTML = `
      <div class="resume-split-pane">
        <div class="resume-editor-pane">
          <textarea id="resume-html-editor" class="source-editor" spellcheck="false">${escapeHtml(data.html)}</textarea>
        </div>
        <div class="resume-preview-pane">
          <iframe id="resume-preview-frame" class="resume-frame"></iframe>
        </div>
      </div>
      <div class="editor-footer">
        <span class="save-status" id="resume-save-status"></span>
        <button class="btn btn-primary" onclick="saveResumeHTML()">Save HTML</button>
      </div>
    `;

    const editor = document.getElementById('resume-html-editor');
    const previewFrame = document.getElementById('resume-preview-frame');

    // Update preview
    let debounceTimer;
    function updatePreview() {
      const doc = previewFrame.contentDocument || previewFrame.contentWindow.document;
      doc.open();
      doc.write(editor.value);
      doc.close();
    }
    updatePreview();

    editor.addEventListener('input', () => {
      state.dirty = true;
      document.getElementById('resume-save-status').textContent = 'Unsaved';
      document.getElementById('resume-save-status').className = 'save-status unsaved';
      clearTimeout(debounceTimer);
      debounceTimer = setTimeout(updatePreview, 500);
    });
    editor.addEventListener('keydown', (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 's') {
        e.preventDefault();
        saveResumeHTML();
      }
    });

    // Active button state
    document.getElementById('btn-preview').classList.remove('active');
    document.getElementById('btn-edit-resume').classList.add('active');
  } else {
    state.resumeEditorMode = false;
    state.dirty = false;
    loadResumeView();
  }
}

async function saveResumeHTML() {
  const editor = document.getElementById('resume-html-editor');
  if (!editor) return;
  const statusEl = document.getElementById('resume-save-status');
  statusEl.textContent = 'Saving...';
  statusEl.className = 'save-status saving';

  const res = await fetch(`/api/resume-html/${state.activeCompany}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ html: editor.value }),
  });

  if (res.ok) {
    state.dirty = false;
    statusEl.textContent = 'Saved';
    statusEl.className = 'save-status saved';
    showToast('Resume saved');
    setTimeout(() => { statusEl.textContent = ''; }, 2000);
  } else {
    statusEl.textContent = 'Save failed!';
    statusEl.className = 'save-status error';
  }
}

async function generateResumePDF() {
  showToast('Generating PDF...');
  const res = await fetch(`/api/resume-html/${state.activeCompany}/pdf`, { method: 'POST' });
  if (res.ok) {
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `resume-${state.activeCompany}.pdf`;
    a.click();
    URL.revokeObjectURL(url);
    showToast('PDF downloaded');
  } else {
    const err = await res.json();
    showToast('PDF failed: ' + (err.error || 'unknown error'));
  }
}


// --- Evidence Panel ---

async function toggleEvidencePanel() {
  state.evidenceVisible = !state.evidenceVisible;
  updateRightPanel();
}

async function updateRightPanel() {
  let panel = document.getElementById('right-panel');

  if (!state.evidenceVisible) {
    if (panel) panel.style.display = 'none';
    return;
  }

  if (!panel) {
    panel = document.createElement('div');
    panel.id = 'right-panel';
    panel.className = 'right-panel';
    document.querySelector('.main').appendChild(panel);
  }
  panel.style.display = 'flex';

  // Load evidence if needed
  if (!state.evidenceData) {
    panel.innerHTML = '<div class="evidence-loading">Loading evidence...</div>';
    try {
      const [evidenceRes, statsRes] = await Promise.all([
        fetch('/api/evidence'),
        fetch('/api/evidence/stats'),
      ]);
      state.evidenceData = {
        sources: await evidenceRes.json(),
        stats: await statsRes.json(),
      };
    } catch (e) {
      panel.innerHTML = '<div class="evidence-loading">Failed to load evidence</div>';
      return;
    }
  }

  renderEvidencePanel(panel);
}

function renderEvidencePanel(panel) {
  const data = state.evidenceData;
  if (!data) return;

  const categories = [...new Set(data.sources.map(s => s.category))];

  panel.innerHTML = `
    <div class="evidence-header">
      <span class="evidence-title">\u{1F4DA} Evidence Base</span>
      <button class="btn btn-ghost evidence-close" onclick="toggleEvidencePanel()">\u2715</button>
    </div>
    <div class="evidence-search">
      <input type="text" id="evidence-search-input" placeholder="Search evidence..." oninput="searchEvidence(this.value)">
    </div>
    <div class="evidence-tabs" id="evidence-tabs">
      <button class="evidence-tab active" onclick="filterEvidence('all', this)">All</button>
      <button class="evidence-tab" onclick="filterEvidence('stats', this)">Stats</button>
      ${categories.map(c => `<button class="evidence-tab" onclick="filterEvidence('${escapeAttr(c)}', this)">${escapeHtml(c)}</button>`).join('')}
    </div>
    <div class="evidence-body" id="evidence-body">
      ${renderStatsCards(data.stats)}
      ${renderEvidenceSections(data.sources)}
    </div>
  `;
}

function renderStatsCards(stats) {
  if (!stats || stats.length === 0) return '';
  // Show key stats as quick-reference cards
  const keyStats = stats.filter(s =>
    /LOC|containers|agents|repos|models|GPU|findings|sessions/i.test(s.metric)
  ).slice(0, 12);

  if (keyStats.length === 0) return '';

  let html = '<div class="stats-grid" id="stats-grid">';
  for (const s of keyStats) {
    html += `
      <div class="stat-card" onclick="copyEvidence('${escapeAttr(s.metric)}: ${escapeAttr(s.value)}')">
        <div class="stat-value">${escapeHtml(s.value)}</div>
        <div class="stat-label">${escapeHtml(s.metric)}</div>
      </div>
    `;
  }
  html += '</div>';
  return html;
}

function renderEvidenceSections(sources) {
  let html = '<div class="evidence-sections" id="evidence-sections">';
  for (const source of sources) {
    html += `<div class="evidence-source" data-category="${escapeAttr(source.category)}">`;
    html += `<div class="evidence-source-header" onclick="this.parentElement.classList.toggle('expanded')">`;
    html += `<span class="evidence-expand-icon">\u25B6</span>`;
    html += `<span class="evidence-source-name">${escapeHtml(source.category)}</span>`;
    html += `<span class="evidence-section-count">${source.sections.length} sections</span>`;
    html += '</div>';
    html += '<div class="evidence-source-body">';
    for (const section of source.sections) {
      const preview = section.text.substring(0, 200).replace(/\n/g, ' ');
      html += `
        <div class="evidence-card">
          <div class="evidence-card-heading">${escapeHtml(section.heading)}</div>
          <div class="evidence-card-preview">${escapeHtml(preview)}...</div>
          <button class="btn btn-ghost evidence-copy-btn" onclick="copyEvidence(${JSON.stringify(section.text).replace(/'/g, '\\u0027')})">Copy</button>
        </div>`;
    }
    html += '</div></div>';
  }
  html += '</div>';
  return html;
}

function filterEvidence(category, btn) {
  // Update active tab
  document.querySelectorAll('.evidence-tab').forEach(t => t.classList.remove('active'));
  if (btn) btn.classList.add('active');

  const statsGrid = document.getElementById('stats-grid');
  const sections = document.querySelectorAll('.evidence-source');

  if (category === 'all') {
    if (statsGrid) statsGrid.style.display = '';
    sections.forEach(s => s.style.display = '');
  } else if (category === 'stats') {
    if (statsGrid) statsGrid.style.display = '';
    sections.forEach(s => s.style.display = 'none');
  } else {
    if (statsGrid) statsGrid.style.display = 'none';
    sections.forEach(s => {
      s.style.display = s.dataset.category === category ? '' : 'none';
    });
  }
}

async function searchEvidence(query) {
  if (!query || query.length < 2) {
    // Reset to normal view
    const sections = document.querySelectorAll('.evidence-source');
    sections.forEach(s => s.style.display = '');
    const statsGrid = document.getElementById('stats-grid');
    if (statsGrid) statsGrid.style.display = '';
    return;
  }

  try {
    const res = await fetch(`/api/evidence/search?q=${encodeURIComponent(query)}`);
    const results = await res.json();

    const body = document.getElementById('evidence-body');
    if (!body) return;

    let html = `<div class="evidence-search-results">`;
    html += `<div class="search-result-count">${results.length} results for "${escapeHtml(query)}"</div>`;
    for (const r of results) {
      html += `
        <div class="evidence-card">
          <div class="evidence-card-category">${escapeHtml(r.category)}</div>
          <div class="evidence-card-heading">${escapeHtml(r.heading)}</div>
          <div class="evidence-card-preview">${escapeHtml(r.text)}</div>
          <button class="btn btn-ghost evidence-copy-btn" onclick="copyEvidence(${JSON.stringify(r.text).replace(/'/g, '\\u0027')})">Copy</button>
        </div>`;
    }
    html += '</div>';
    body.innerHTML = html;
  } catch (e) { /* ignore */ }
}

function copyEvidence(text) {
  // If constellation editor is focused, insert at cursor
  const editor = document.getElementById('constellation-editor');
  if (editor && document.activeElement === editor) {
    const start = editor.selectionStart;
    const end = editor.selectionEnd;
    editor.value = editor.value.substring(0, start) + text + editor.value.substring(end);
    editor.selectionStart = editor.selectionEnd = start + text.length;
    editor.dispatchEvent(new Event('input'));
    showToast('Inserted at cursor');
    return;
  }

  navigator.clipboard.writeText(text).then(() => {
    showToast('Copied to clipboard');
  }).catch(() => {
    showToast('Copy failed');
  });
}


// --- Cheat Sheet Toggle ---

function toggleCheatSheet() {
  state.cheatSheetVisible = !state.cheatSheetVisible;
  const panel = document.getElementById('cheat-sheet-panel');
  if (panel) {
    panel.style.display = state.cheatSheetVisible ? '' : 'none';
  }
}


// --- Export Modal ---

async function showExportModal() {
  if (!state.fellowshipMode) return;

  const res = await fetch(`/api/export/${state.activeCompany}/both/plain-text`);
  if (!res.ok) return;
  const data = await res.json();

  const overlay = document.createElement('div');
  overlay.className = 'modal-overlay';
  overlay.onclick = (e) => { if (e.target === overlay) overlay.remove(); };

  let fieldsHtml = '';
  for (const field of data.fields) {
    const wcClass = field.word_count >= field.word_min && field.word_count <= field.word_max
      ? 'word-count-ok' : field.word_count < field.word_min ? 'word-count-under' : 'word-count-over';
    fieldsHtml += `
      <div class="export-field">
        <div class="export-field-header">
          <strong>${escapeHtml(field.label)}</strong>
          <span class="${wcClass}">${field.word_count} / ${field.word_min}-${field.word_max} words</span>
          <button class="btn btn-ghost" onclick="copyExportField(this, '${escapeAttr(field.field_id)}')">Copy</button>
        </div>
        <pre class="export-field-content" id="export-${field.field_id}">${escapeHtml(field.content || '[Not yet written]')}</pre>
      </div>`;
  }

  overlay.innerHTML = `
    <div class="modal export-modal">
      <div class="modal-header">
        <h2>Export for Constellation Portal</h2>
        <button class="btn btn-ghost" onclick="this.closest('.modal-overlay').remove()">\u2715</button>
      </div>
      <div class="modal-body">
        ${fieldsHtml}
      </div>
      <div class="modal-footer">
        <button class="btn btn-primary" onclick="copyAllExport()">Copy All</button>
        <button class="btn btn-ghost" onclick="emailExport()">Email to Self</button>
        <button class="btn btn-ghost" onclick="this.closest('.modal-overlay').remove()">Close</button>
      </div>
    </div>`;

  document.body.appendChild(overlay);
}

function copyExportField(btn, fieldId) {
  const pre = document.getElementById(`export-${fieldId}`);
  if (pre) {
    navigator.clipboard.writeText(pre.textContent).then(() => {
      btn.textContent = 'Copied!';
      setTimeout(() => { btn.textContent = 'Copy'; }, 1500);
    });
  }
}

async function copyAllExport() {
  const res = await fetch(`/api/export/${state.activeCompany}/both/plain-text`);
  const data = await res.json();
  let text = '';
  for (const field of data.fields) {
    text += `--- ${field.label} ---\n${field.content || '[Not yet written]'}\n\n`;
  }
  navigator.clipboard.writeText(text).then(() => {
    showToast('All fields copied');
  });
}

async function emailExport() {
  const res = await fetch(`/api/export/${state.activeCompany}/both/email`, { method: 'POST' });
  if (res.ok) {
    const data = await res.json();
    showToast(`Emailed to ${data.to}`);
  } else {
    const err = await res.json();
    showToast('Email failed: ' + (err.error || 'unknown'));
  }
}


// --- Review Mode ---

function renderReviewMode(html) {
  const content = document.getElementById('content');
  const docLabel = state.companies.find(c => c.slug === state.activeCompany)
    ?.documents.find(d => d.id === state.activeDoc)?.label || state.activeDoc;
  const icon = getDocIcon(state.activeDoc);

  content.innerHTML = `
    <div class="content-toolbar">
      <span class="doc-title">${icon} ${escapeHtml(docLabel)}</span>
      <div class="toolbar-actions">
        <button class="btn btn-ghost mode-btn active" id="btn-review" onclick="switchMode('review')">Review</button>
        <button class="btn btn-ghost mode-btn" id="btn-source" onclick="switchMode('source')">Source</button>
        ${state.fellowshipMode ? '<button class="btn btn-ghost mode-btn" onclick="toggleEvidencePanel()" title="Ctrl+E">Evidence</button>' : ''}
      </div>
    </div>
    <div id="doc-body">${html}</div>`;

  document.querySelectorAll('.reviewable').forEach(el => {
    const actions = document.createElement('div');
    actions.className = 'para-actions';

    const editBtn = document.createElement('button');
    editBtn.className = 'para-btn edit-para-btn';
    editBtn.innerHTML = '&#9998;';
    editBtn.title = 'Edit this paragraph';
    editBtn.onclick = (e) => { e.stopPropagation(); startInlineEdit(el); };

    const noteBtn = document.createElement('button');
    noteBtn.className = 'para-btn add-note-btn';
    noteBtn.textContent = '+';
    noteBtn.title = 'Add a note';
    noteBtn.onclick = (e) => { e.stopPropagation(); showNoteForm(el); };

    actions.appendChild(editBtn);
    actions.appendChild(noteBtn);
    el.appendChild(actions);
  });

  renderDocNotes();
}

// --- Source Mode ---

function switchMode(mode) {
  if (mode === 'source' && state.editMode) return;
  if (mode === 'review' && !state.editMode) return;

  if (mode === 'source') {
    state.editMode = true;
    const content = document.getElementById('content');
    const docLabel = state.companies.find(c => c.slug === state.activeCompany)
      ?.documents.find(d => d.id === state.activeDoc)?.label || state.activeDoc;
    const icon = getDocIcon(state.activeDoc);

    content.innerHTML = `
      <div class="content-toolbar">
        <span class="doc-title">${icon} ${escapeHtml(docLabel)}</span>
        <div class="toolbar-actions">
          <button class="btn btn-ghost mode-btn" id="btn-review" onclick="switchMode('review')">Review</button>
          <button class="btn btn-ghost mode-btn active" id="btn-source" onclick="switchMode('source')">Source</button>
          <button class="btn btn-primary" id="btn-save-source" onclick="saveSource()">Save</button>
          <span class="save-status" id="save-status"></span>
        </div>
      </div>
      <textarea id="source-editor" class="source-editor" spellcheck="false">${escapeHtml(state.rawContent)}</textarea>`;

    const editor = document.getElementById('source-editor');
    editor.addEventListener('input', () => {
      state.dirty = true;
      document.getElementById('save-status').textContent = 'Unsaved changes';
      document.getElementById('save-status').className = 'save-status unsaved';
    });
    editor.addEventListener('keydown', (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 's') {
        e.preventDefault();
        saveSource();
      }
    });
    editor.focus();
  } else {
    if (state.dirty && !confirm('You have unsaved source edits. Discard?')) return;
    state.editMode = false;
    state.dirty = false;
    selectDocument(state.activeDoc);
  }
}

async function saveSource() {
  const editor = document.getElementById('source-editor');
  const newContent = editor.value;
  const statusEl = document.getElementById('save-status');
  statusEl.textContent = 'Saving...';
  statusEl.className = 'save-status saving';

  const res = await fetch(`/api/document/${state.activeCompany}/${state.activeDoc}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ content: newContent }),
  });

  if (res.ok) {
    const data = await res.json();
    state.rawContent = data.raw;
    state.blocks = data.blocks || [];
    state.dirty = false;
    statusEl.textContent = 'Saved';
    statusEl.className = 'save-status saved';
    showToast('Saved');
    setTimeout(() => { statusEl.textContent = ''; }, 2000);
  } else {
    statusEl.textContent = 'Save failed!';
    statusEl.className = 'save-status error';
  }
}

// --- Inline Paragraph Editing ---

function startInlineEdit(el) {
  document.querySelectorAll('.inline-edit-form').forEach(f => {
    const parent = f.previousElementSibling;
    if (parent) parent.style.display = '';
    f.remove();
  });

  const idx = parseInt(el.dataset.idx);
  const raw = el.dataset.raw || '';

  el.style.display = 'none';

  const form = document.createElement('div');
  form.className = 'inline-edit-form';
  form.innerHTML = `
    <textarea class="inline-editor" spellcheck="false">${escapeHtml(raw)}</textarea>
    <div class="inline-edit-controls">
      <button class="btn btn-primary" onclick="saveInlineEdit(this, ${idx})">Save</button>
      <button class="btn btn-ghost" onclick="cancelInlineEdit(this)">Cancel</button>
      <span class="edit-hint">Block ${idx + 1} &middot; Ctrl+Enter to save</span>
    </div>`;

  el.after(form);

  const textarea = form.querySelector('textarea');
  textarea.focus();
  textarea.style.height = Math.max(80, textarea.scrollHeight) + 'px';
  textarea.addEventListener('input', () => {
    textarea.style.height = 'auto';
    textarea.style.height = textarea.scrollHeight + 'px';
  });
  textarea.addEventListener('keydown', (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
      e.preventDefault();
      saveInlineEdit(form.querySelector('.btn-primary'), idx);
    }
    if (e.key === 'Escape') {
      cancelInlineEdit(form.querySelector('.btn-ghost'));
    }
  });
}

async function saveInlineEdit(btn, blockIdx) {
  const form = btn.closest('.inline-edit-form');
  const textarea = form.querySelector('textarea');
  const newContent = textarea.value;

  btn.disabled = true;
  btn.textContent = 'Saving...';

  const res = await fetch(
    `/api/document/${state.activeCompany}/${state.activeDoc}/block/${blockIdx}`,
    {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content: newContent }),
    }
  );

  if (res.ok) {
    const data = await res.json();
    state.rawContent = data.raw;
    state.blocks = data.blocks || [];
    renderReviewMode(data.html);

    const edited = document.querySelector(`.reviewable[data-idx="${blockIdx}"]`);
    if (edited) {
      edited.classList.add('just-edited');
      setTimeout(() => edited.classList.remove('just-edited'), 1500);
    }
    showToast('Block saved');
  } else {
    btn.disabled = false;
    btn.textContent = 'Save';
    alert('Save failed');
  }
}

function cancelInlineEdit(btn) {
  const form = btn.closest('.inline-edit-form');
  const prev = form.previousElementSibling;
  if (prev) prev.style.display = '';
  form.remove();
}

// --- Note Rendering ---

function renderDocNotes() {
  const slug = state.activeCompany;
  const docId = state.activeDoc;
  const notes = (state.notes[slug] || []).filter(n => n.document === docId);

  document.querySelectorAll('.note-block').forEach(el => el.remove());

  for (const note of notes) {
    const target = document.querySelector(`.reviewable[data-idx="${note.paragraph_index}"]`);
    if (!target) continue;
    const block = createNoteBlock(note);
    target.after(block);
  }
}

function createNoteBlock(note) {
  const block = document.createElement('div');
  block.className = `note-block ${note.note_type} ${note.status === 'applied' ? 'applied' : ''}`;
  block.dataset.noteId = note.id;
  block.innerHTML = `
    <div class="note-text">${escapeHtml(note.note)}</div>
    <div class="note-meta">
      <span class="note-type-badge">${note.note_type}</span>
      <span>${note.status}</span>
      <span>${formatDate(note.created_at)}</span>
    </div>
    <div class="note-actions">
      ${note.status === 'pending' ? `<button onclick="deleteNote(${note.id})" title="Delete">&times;</button>` : ''}
    </div>`;
  return block;
}

function renderResumeNotes() {
  const container = document.getElementById('resume-notes-list');
  if (!container) return;
  const notes = (state.notes[state.activeCompany] || []).filter(n => n.document === 'resume');
  container.innerHTML = '';
  for (const note of notes) {
    container.appendChild(createNoteBlock(note));
  }
}

// --- Note Form ---

function showNoteForm(el) {
  document.querySelectorAll('.note-form:not(#resume-note-form)').forEach(f => f.remove());

  const idx = el.dataset.idx;
  const anchor = el.dataset.anchor;

  const form = document.createElement('div');
  form.className = 'note-form';
  form.innerHTML = `
    <textarea placeholder="What should change here?" autofocus></textarea>
    <div class="note-form-controls">
      <select>
        <option value="edit">Edit</option>
        <option value="rewrite">Rewrite</option>
        <option value="remove">Remove</option>
        <option value="question">Question</option>
        <option value="approve">Approve</option>
      </select>
      <button class="btn btn-primary" onclick="saveNote(this, ${idx}, '${escapeAttr(anchor)}')">Save</button>
      <button class="btn btn-ghost" onclick="this.closest('.note-form').remove()">Cancel</button>
    </div>`;
  el.after(form);
  form.querySelector('textarea').focus();
}

// --- Note CRUD ---

async function saveNote(btn, idx, anchor) {
  const form = btn.closest('.note-form');
  const text = form.querySelector('textarea').value.trim();
  const type = form.querySelector('select').value;
  if (!text) return;

  const res = await fetch('/api/notes', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      company_slug: state.activeCompany,
      document: state.activeDoc,
      paragraph_index: idx,
      anchor_text: anchor,
      note: text,
      note_type: type,
    }),
  });

  if (res.ok) {
    const note = await res.json();
    if (!state.notes[state.activeCompany]) state.notes[state.activeCompany] = [];
    state.notes[state.activeCompany].push(note);
    form.remove();
    renderDocNotes();
    refreshCounts();
  }
}

async function saveResumeNote() {
  const text = document.getElementById('resume-note-text')?.value.trim();
  const type = document.getElementById('resume-note-type')?.value || 'edit';
  if (!text) return;

  const res = await fetch('/api/notes', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      company_slug: state.activeCompany,
      document: 'resume',
      paragraph_index: 0,
      anchor_text: '',
      note: text,
      note_type: type,
    }),
  });

  if (res.ok) {
    const note = await res.json();
    if (!state.notes[state.activeCompany]) state.notes[state.activeCompany] = [];
    state.notes[state.activeCompany].push(note);
    document.getElementById('resume-note-text').value = '';
    renderResumeNotes();
    refreshCounts();
    showToast('Note saved');
  }
}

async function deleteNote(id) {
  await fetch(`/api/notes/${id}`, { method: 'DELETE' });
  for (const slug in state.notes) {
    state.notes[slug] = state.notes[slug].filter(n => n.id !== id);
  }
  const el = document.querySelector(`[data-note-id="${id}"]`);
  if (el) el.remove();
  refreshCounts();
}

async function refreshCounts() {
  const res = await fetch('/api/companies');
  state.companies = await res.json();
  renderTabs();
  renderSidebar(state.companies.find(c => c.slug === state.activeCompany));
}

// --- Guide Bar ---

async function loadGuideBar(slug) {
  const bar = document.getElementById('guidebar');
  const company = state.companies.find(c => c.slug === slug);
  if (!company) return;

  if (state.fellowshipMode) {
    // Fellowship mode guide bar: progress dashboard
    let totalFields = 0, doneFields = 0, draftedFields = 0;
    for (const doc of company.documents) {
      if (doc.type === 'constellation') {
        totalFields++;
        const s = state.fieldStatuses[doc.id];
        if (s?.status === 'final') doneFields++;
        else if (s?.status && s.status !== 'not_started') draftedFields++;
      }
    }
    const pct = totalFields ? Math.round(doneFields / totalFields * 100) : 0;

    bar.innerHTML = `
      <span class="guide-label">Fellowship Application</span>
      <div class="guide-sep"></div>
      <span class="status-badge open">SECURITY FELLOW</span>
      <div class="guide-sep"></div>
      <span class="guide-progress-mini">
        <span style="color:var(--green)">${doneFields}</span> final
        <span style="color:var(--text-dim)">/</span>
        <span style="color:var(--yellow)">${draftedFields}</span> drafting
        <span style="color:var(--text-dim)">/</span>
        <span style="color:var(--text-muted)">${totalFields - doneFields - draftedFields}</span> todo
      </span>
      <div class="guide-sep"></div>
      <span class="guide-deadline">July 2026 cohort</span>
      <div class="guide-notes">
        <span class="count">${pct}%</span> complete
      </div>`;
    return;
  }

  // Guide bar data comes from each company's meta.json (no hardcoded URLs)
  const meta = company || {};
  const url = meta.apply_url || '';
  const deadline = meta.deadline || '';
  const statusClass = (meta.status || 'open').toLowerCase();

  bar.innerHTML = `
    <span class="guide-label">${escapeHtml(company.name)}</span>
    <div class="guide-sep"></div>
    <span class="status-badge ${statusClass}">${statusClass.toUpperCase()}</span>
    <div class="guide-sep"></div>
    <span class="guide-salary">${escapeHtml(company.salary || '')}</span>
    <div class="guide-sep"></div>
    <span class="guide-deadline">Deadline: ${escapeHtml(deadline)}</span>
    <div class="guide-sep"></div>
    ${url ? `<a href="${url}" target="_blank" rel="noopener">Apply \u2192</a>` : '<span style="color:var(--red)">Role delisted</span>'}
    <div class="guide-notes">
      <span class="count">${company.pending_notes}</span> pending notes
    </div>`;
}


// --- Toast Notifications ---

function showToast(message) {
  let container = document.getElementById('toast-container');
  if (!container) {
    container = document.createElement('div');
    container.id = 'toast-container';
    container.className = 'toast-container';
    document.body.appendChild(container);
  }

  const toast = document.createElement('div');
  toast.className = 'toast';
  toast.textContent = message;
  container.appendChild(toast);

  // Trigger animation
  requestAnimationFrame(() => toast.classList.add('toast-visible'));

  setTimeout(() => {
    toast.classList.remove('toast-visible');
    toast.classList.add('toast-exit');
    setTimeout(() => toast.remove(), 300);
  }, 2000);
}


// --- Helpers ---

function escapeHtml(str) {
  const div = document.createElement('div');
  div.textContent = str;
  return div.innerHTML;
}

function escapeAttr(str) {
  return str.replace(/'/g, "\\'").replace(/"/g, '\\"');
}

function formatDate(iso) {
  if (!iso) return '';
  const d = new Date(iso);
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
}

// --- Start ---
document.addEventListener('DOMContentLoaded', init);
