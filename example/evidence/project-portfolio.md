# Project Portfolio

## Jordan Chen — Key projects with evidence for fellowship applications

---

## DataForge

**What it is:** A high-performance data pipeline framework that lets data engineers define extract-transform-load workflows in Python with optional Rust extensions for throughput-critical steps. Designed to replace ad-hoc ETL scripts with a testable, composable, production-ready abstraction. Ships with a CLI, a web UI for pipeline inspection, and connectors for 27 sources and sinks (Postgres, S3, Kafka, BigQuery, Snowflake, and more).

**Tech stack:** Python 3.11 core, PyO3 Rust extensions, Click CLI, FastAPI monitoring UI, PostgreSQL state store, Redis task queue, Docker, GitHub Actions CI

**Scale:** 32,400 LOC; 1,847 tests; 91% coverage; 12,600 PyPI downloads in the last 30 days; 2,140 GitHub stars; 38 known production deployments; peak throughput of 4.2 GB/min in benchmarks

**Key achievement:** The Rust extension layer delivers an 11x throughput gain over pure-Python equivalents on columnar transformation workloads, measured in the project's open benchmark suite. This required deep profiling, careful FFI boundary design via PyO3, and a zero-copy memory model for passing NumPy arrays across the language boundary.

**Relevance:** Research engineering at Acme Corp requires building the infrastructure that experiments run on — reliable, fast, observable data pipelines are table stakes. DataForge demonstrates I can design systems at that layer, not just consume them. The Rust/Python hybrid architecture is the same pattern used in production ML frameworks (Polars, PyArrow), so this reflects current industry standards rather than hobby-scale work.

**Code samples:** github.com/jordanchen/dataforge (public) — start with `dataforge/core/pipeline.py` and `dataforge/ext/transforms.rs`

**Demo/live URL:** dataforge.dev (docs + live playground)

---

## Sentinel

**What it is:** A streaming anomaly detection system for application and infrastructure metrics. Engineers instrument their services with a lightweight SDK, and Sentinel applies a configurable ensemble of statistical and ML-based detectors (Z-score, LSTM autoencoder, Isolation Forest, and others) to flag anomalies in near-real-time. Alerts route to PagerDuty, Slack, or a built-in dashboard.

**Tech stack:** Python (detection engine, SDK), TypeScript/React (dashboard), Go (high-throughput ingest service), PostgreSQL (alert history), Redis Streams (event bus), Kubernetes (production deployment), Prometheus + Grafana (self-monitoring)

**Scale:** 18,200 LOC; 84% test coverage; processes 2.1 million events/day at peak; p99 detection latency of 38 ms; 0.8% false-positive rate in production baseline; 140 daily active dashboard users; 99.6% uptime over the last 90 days

**Key achievement:** Reducing the false-positive rate from 4.1% (single-algorithm baseline) to 0.8% by building a weighted ensemble that dynamically adjusts detector weights based on recent precision/recall. The weighting logic is documented in `sentinel/ensemble/adaptive_weights.py` and covered by a replay-based evaluation harness that runs against 60 days of labeled production data.

**Relevance:** Anomaly detection is a microcosm of applied ML research — you have to translate a statistical idea into a system that works on messy real-world data, stays calibrated over time, and fails gracefully. Building and operating Sentinel gave me direct experience with model drift, threshold calibration, and the gap between benchmark performance and production performance. That gap is exactly what research engineers at AI labs navigate every day.

**Code samples:** github.com/jordanchen/sentinel (public) — `sentinel/detectors/` for algorithm implementations, `sentinel/ensemble/` for the weighting layer

**Demo/live URL:** sentinel-demo.jordanchen.dev (read-only dashboard with synthetic data)

---

## scikit-learn Contributions

**What it is:** Ongoing contributions to scikit-learn, the foundational Python ML library. Work spans bug fixes, performance improvements, and new estimator features. All contributions go through scikit-learn's rigorous review process (SLEP governance, two core-maintainer approvals, full test suite, documentation).

**Tech stack:** Python, Cython, NumPy, SciPy, pytest, Sphinx

**Scale:** 7 merged PRs; ~2,800 lines changed (additions + deletions); 11 issues resolved; most significant PR (#26841) reduced `GridSearchCV` memory usage by 34% on large parameter grids by switching to a generator-based candidate iterator

**Key achievement:** PR #26841 — profiled a memory regression in `GridSearchCV` reported by a user running 10,000-combination searches, traced it to a list materialization in `ParameterGrid.__iter__`, and replaced it with a lazy generator. The fix reduced peak RSS by 34% on the reporter's workload and was merged without changes after the first review round. Write-up: jordanchen.dev/blog/sklearn-memory-fix

**Relevance:** Contributing to scikit-learn requires understanding the codebase at the level of someone who could have written it — not just using the API. The review process is adversarial in a healthy way: maintainers push back hard on anything that introduces complexity without clear benefit. That discipline — make it correct, make it fast, justify every trade-off — is the same standard research engineering requires.

**Code samples:** github.com/scikit-learn/scikit-learn/pulls?q=author%3Ajordanchen

**Demo/live URL:** N/A (library)

---

## forge-cli

**What it is:** A personal command-line toolkit that wraps common developer workflows — project scaffolding, git branch hygiene, Docker Compose templating, and local environment setup. Distributed as a single static binary compiled with PyInstaller (Python core) and a small Rust helper for filesystem-heavy operations.

**Tech stack:** Python, Rust, Click, Typer, PyInstaller, Homebrew tap

**Scale:** 4,100 LOC; 22 commands; available via a personal Homebrew tap; ~60 installs based on tap analytics

**Key achievement:** Bootstrapping a new project from scratch (git init, virtualenv, pre-commit hooks, Docker Compose scaffold, CI template) takes 90 seconds instead of 15–20 minutes of copy-paste. Several colleagues at Meridian Labs adopted it and contributed two commands via PR.

**Relevance:** A secondary signal: developers who build tools for their own workflows tend to have strong opinions about DX, which translates into better internal tooling on research engineering teams.

**Code samples:** github.com/jordanchen/forge-cli

**Demo/live URL:** N/A (CLI tool)

---

## jordanchen.dev

**What it is:** Personal site and technical blog. Publishes deep-dive posts on systems programming, ML infrastructure, and open-source contribution process. Built with Astro (static site generation) and deployed on Cloudflare Pages.

**Tech stack:** Astro, TypeScript, MDX, Cloudflare Pages, Plausible analytics

**Scale:** 14 published posts; ~2,800 monthly unique visitors (Plausible); top post ("Why your ETL is slow and how to fix it") has 18,000 cumulative views and was linked from the Python Weekly newsletter

**Key achievement:** The blog functions as a public audit trail for technical decisions — most posts are post-mortems or deep dives into a specific problem encountered while building DataForge or Sentinel. Several scikit-learn contributors found the repo via the blog.

**Relevance:** Writing clearly about technical work is a core research engineering skill. Grant proposals, design docs, and RFC-style discussions all require the same translation layer: take something complex, make it legible to a technically sophisticated reader who doesn't share your exact context.

**Code samples:** github.com/jordanchen/jordanchen.dev

**Demo/live URL:** jordanchen.dev
