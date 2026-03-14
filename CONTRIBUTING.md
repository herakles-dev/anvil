# Contributing to Anvil

Thanks for your interest in contributing. Anvil is a small, focused project — contributions that keep it simple and useful are welcome.

## How to Contribute

### Reporting Bugs

1. Check [existing issues](https://github.com/herakles-dev/anvil/issues) first
2. Use the **Bug Report** template
3. Include steps to reproduce and your environment details

### Suggesting Features

1. Open a **Feature Request** issue
2. Describe the problem you're solving, not just the solution you want
3. If it's a big change, discuss it in an issue before writing code

### Submitting Code

1. Fork the repo and create a branch from `main`
2. Make your changes
3. Test locally: `docker compose up -d --build` and verify in the browser
4. Submit a PR using the template

## Development Setup

```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/anvil.git
cd anvil

# Run locally without Docker (for faster iteration)
pip install -r requirements.txt
APPLICATIONS_DIR=./example/applications EVIDENCE_DIR=./example/evidence python app.py

# Or with Docker
docker compose up -d --build
```

The app runs at http://localhost:5000 (local) or http://localhost:8135 (Docker).

## Guidelines

### Code Style

- **Python**: Clean, readable, no frameworks beyond Flask. Follow existing patterns in `app.py`.
- **JavaScript**: Vanilla JS only — no frameworks, no build step, no npm. Follow existing patterns in `review.js`.
- **CSS**: Use the existing CSS custom properties (design tokens). Add to `style.css`, don't create new files.

### What We're Looking For

- Bug fixes with clear reproduction steps
- UI/UX improvements that keep the interface simple
- New evidence sidebar features (better search, more file format support)
- Export format options (PDF, DOCX, etc.)
- Better CLI integration patterns
- Documentation improvements
- Accessibility improvements

### What We'll Probably Decline

- Adding JavaScript frameworks (React, Vue, etc.)
- Adding a build step or package manager
- Features that require a database migration tool
- Breaking changes to the file-based data model (markdown files on disk is core to the CLI workflow)
- AI/LLM integration in the app itself (the app is the *companion* to your CLI-based LLM — it doesn't need its own)

## Architecture Decisions

These are intentional and shouldn't be changed without discussion:

1. **Vanilla JS** — no framework, no build step. The entire frontend is one JS file.
2. **Files on disk** — application materials are plain markdown. This is what makes the CLI workflow possible.
3. **SQLite for state only** — notes and field status live in SQLite. Document content lives in `.md` files.
4. **Single `app.py`** — the backend is one file. It's ~920 lines. That's fine.
5. **`fields.json` for config** — form fields are data, not code. Users edit JSON, not Python.
6. **Docker-first** — Chromium for PDF generation means Docker is the primary deployment path.

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
