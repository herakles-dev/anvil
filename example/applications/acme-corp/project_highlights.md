# Project Highlights — Jordan Chen for Research Engineering Fellow

## Project 1: DataForge

**What it is:** A production data pipeline framework built for ML workloads — handles ingestion, validation, transformation, and lineage tracking across heterogeneous data sources. Started as an internal tool at Meridian Labs, now used by three research teams processing live production data.

**Tech stack:** Python (core API, validation engine, lineage graph), Rust (high-throughput batch processing layer, compiled via PyO3 bindings), PostgreSQL (lineage metadata store), Redis (pipeline state cache), Docker + Kubernetes (deployment)

**Key metrics:**
- 32,000 lines of code across Python and Rust
- Processes approximately 2 million records per day in production
- Sub-50ms p99 end-to-end pipeline latency on standard validation workloads
- Schema validation catches malformed records before they reach model training
- Adopted by 3 research teams within 6 months of internal release, zero ops support required post-launch

**Why it matters for this role:** The fellowship's stated focus on data quality and ML infrastructure is exactly the problem DataForge was built to solve. The work required understanding both the engineering constraints (throughput, latency, reliability) and the research needs (reproducibility, lineage, schema enforcement) — the same dual fluency the Research Engineering Fellow role demands. The Rust performance layer in particular reflects a deliberate decision to make correctness cheap enough that researchers never have an incentive to skip validation.

---

## Project 2: Sentinel

**What it is:** A real-time anomaly detection system for monitoring ML model behavior in production. Runs continuous inference on streaming input/output data and flags statistical deviations from baseline distributions. Built after a silent data corruption issue at Meridian Labs went undetected for six weeks.

**Tech stack:** Python (detection algorithms, statistical modeling, alerting), Go (high-throughput streaming ingestion daemon), PyTorch (baseline distribution modeling), Redis Streams (event queue), Grafana + custom webhooks (alerting)

**Key metrics:**
- 18,000 lines of code across Python and Go
- Monitors streaming data at up to 50,000 events per second without dropping events
- Detected a production data corruption issue that dashboard-level monitoring missed for 6 weeks
- Configurable detection thresholds per metric and per input slice (not just aggregate scores)
- Mean time to alert on anomalies: under 90 seconds from event ingestion

**Why it matters for this role:** Model evaluation is only useful if it runs continuously, not just at deployment time. Sentinel embodies a conviction that matters directly for Acme's work: aggregate metrics can stay stable while a model degrades on specific input slices. The system was built specifically to catch that failure mode. For a fellowship focused on evaluation infrastructure, Sentinel is proof that I've thought seriously about what "reliable AI behavior" means in a production context — and built tooling to enforce it.

---

## Project 3: scikit-learn (OSS Contributions)

**What it is:** Contributed patches and documentation improvements to scikit-learn, the widely-used Python ML library maintained by a distributed team of researchers and engineers across academia and industry.

**Tech stack:** Python, NumPy, SciPy, pytest; development process involves rigorous code review, CI pipelines, and compatibility guarantees across Python and NumPy version matrices

**Key metrics:**
- 4 merged pull requests: 2 bug fixes in preprocessing utilities, 1 performance improvement to KMeans initialization, 1 documentation expansion for Pipeline API edge cases
- 2 issue investigations that led to upstream fixes by maintainers
- All contributions went through full review cycle with core maintainers (typically 2–4 review rounds)
- Patches required backward compatibility with multiple scikit-learn and NumPy versions simultaneously

**Why it matters for this role:** Research engineering at Acme means writing code that survives contact with a large, diverse user base — code that has to be correct, maintainable, and trustworthy across versions. The scikit-learn review process is one of the most rigorous in open-source ML: maintainers push back hard on anything that could silently break existing behavior. Going through that process four times built habits around defensive API design, thorough testing, and writing code that makes its assumptions explicit. Those habits are directly transferable to building evaluation and infrastructure tooling that research teams can rely on.
