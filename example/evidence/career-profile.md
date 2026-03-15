# Career Profile

## Jordan Chen — Research Engineering Fellow candidate, Acme Corp

---

## Summary

Jordan Chen is a full-stack software engineer with six years of professional experience, the last three focused on data infrastructure and ML systems. They have built two open-source projects with meaningful adoption (DataForge, Sentinel), contributed substantively to scikit-learn, and spent the past year closing the gap between their engineering background and the mathematical and research foundations required to do original work in ML. They are applying to the Acme Corp Research Engineering Fellowship to make that transition formal and deliberate.

---

## Career Arc

**2020 — Initech (Junior Software Developer)**
Joined Initech straight out of UC Berkeley. Built and maintained internal reporting dashboards and ETL pipelines for the operations team. Introduced type annotations and pytest coverage to a previously untested codebase, taking coverage from 0% to 74% in four months. First exposure to the pattern that would define the rest of the career: data infrastructure determines the velocity of everyone downstream of it. Left after a year with a strong foundation in production Python and a clear sense that the data layer was where interesting problems lived.

**2021 — Nexus Analytics (Data Engineer)**
Moved to Nexus Analytics to own end-to-end data pipeline infrastructure serving 12 customer-facing analytics products. This was the first time Jordan worked directly alongside data scientists and ML engineers, and it crystallized a pattern: the research team's velocity was almost entirely determined by the quality of the infrastructure underneath them. Reduced median pipeline failure recovery time from 3.2 hours to 22 minutes by rebuilding the alerting and runbook system. Migrated 40TB of historical data to a modern storage layer, reducing query costs by 60%. Began contributing to scikit-learn during this period — 4 merged PRs that went through rigorous maintainer review.

**2023 — Meridian Labs (Senior Software Engineer, ML Infrastructure)**
Joined Meridian Labs, a Series B data observability startup, to lead data platform engineering for three research teams. Built DataForge (32K LOC, Python/Rust) as the production pipeline framework — now processing ~2M records/day. Built Sentinel (18K LOC, Python/Go) for real-time anomaly detection after a silent data corruption issue went undetected for six weeks. Also took on mentoring two junior engineers and running weekly data infrastructure office hours. Began taking the fast.ai practical deep learning course in parallel with work, and audited MIT 6.S191 (Introduction to Deep Learning). This is the current role.

---

## Narrative Arc

The application to the Acme Corp Research Engineering Fellowship comes out of a specific realization, not a general desire to pivot.

At Tempus and Meridian, Jordan spent years being the person who made researchers go faster. That work was satisfying and taught them a great deal about what makes ML systems fail in production. But it also created a persistent frustration: the infrastructure engineer can see the experiment design clearly enough to notice when it is wrong, but has no standing to say so. The role is defined as execution, not inquiry.

The scikit-learn contributions were the first time that changed. Opening PR #26841 required understanding the statistical assumptions behind `GridSearchCV`'s parallel evaluation logic — not just the code, but the reason the code was written the way it was. The maintainers' review pushed Jordan to read the original Bergstra & Bengio random search paper and three follow-up benchmarks before the thread was resolved. That was the first time engineering work required the same kind of engagement as research, and it felt qualitatively different.

DataForge and Sentinel were both built to solve real problems, but they were also platforms for learning: every performance investigation led to a paper, every algorithm implementation required understanding a literature. Jordan has spent the last 18 months doing this systematically — reading, implementing, benchmarking, writing up results on the blog. The fellowship would provide structure, mentorship, and collaborators to make that work rigorous rather than self-directed.

The target is applied ML research at the infrastructure/systems layer — the kind of work that produces both papers and artifacts that other researchers can use. Acme Corp's published research on training efficiency and evaluation methodology is exactly the domain.

---

## Education & Credentials

- BS Computer Science, UC Berkeley, 2020 — GPA 3.7, concentration in Systems; senior thesis on consistent hashing variants for distributed key-value stores
- fast.ai Practical Deep Learning for Coders (Part 1 + Part 2), 2024–2025 — completed with implementation projects
- MIT 6.S191 Introduction to Deep Learning (audit), Spring 2025
- Stanford CS229 Machine Learning (audit via OpenCourseWare), 2024
- Stripe engineering onboarding program (distributed systems track), 2020
- AWS Certified Solutions Architect — Associate, 2022

---

## Key Differentiators

- **Systems depth at ML scale.** DataForge's Rust/Python hybrid and Sentinel's ingest service are not toy projects — they handle real production load and were designed with the same rigor Jordan applied at Stripe. Most ML-adjacent engineers have one or the other; not both.

- **Contributor, not just user, of foundational libraries.** Seven merged scikit-learn PRs means understanding the codebase at the level of someone who could extend it. That is a different kind of credibility than "used scikit-learn in a project."

- **Writing as a forcing function.** The technical blog is not a portfolio artifact — it is how Jordan thinks. Every major decision in DataForge and Sentinel has a corresponding post that explains the trade-off space. That habit of making reasoning legible is the same habit that makes research engineering productive.

- **Knows where the gap is.** Jordan is not applying to the fellowship because the engineering career stalled. It is going well. The application is specific: there is a class of problems at the intersection of systems and ML research that require formal training to engage with, and the fellowship is the most direct path to acquiring it.
