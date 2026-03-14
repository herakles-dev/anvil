# Security Policy

## Important Context

Anvil is a **local development tool** designed to run on your own machine or private server. It stores sensitive personal data (resumes, cover letters, application materials) in plain files on disk and an unencrypted SQLite database.

**Anvil is NOT designed to be exposed to the public internet.**

## Reporting a Vulnerability

If you discover a security issue, please report it responsibly:

1. **Do not** open a public issue
2. Email the maintainer or use [GitHub Security Advisories](https://github.com/herakles-dev/anvil/security/advisories/new)
3. Include steps to reproduce and potential impact

## Scope

Security issues we care about:
- Path traversal allowing reads/writes outside the applications directory
- Injection vulnerabilities in the API (SQL injection, command injection)
- Cross-site scripting (XSS) in rendered markdown content
- Unauthorized access to backup files or database

Issues outside scope (by design):
- No authentication (it's a local tool)
- No encryption at rest (files are plain markdown for CLI access)
- No HTTPS (intended for localhost or private networks)
- SMTP credentials in environment variables (standard Docker pattern)

## Supported Versions

Only the latest release on `main` is supported.
