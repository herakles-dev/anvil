# Talking Points — Acme Corp Research Engineering Fellow

## Why This Company

- **Reliability as a first-class research problem.** Most AI labs treat data quality and infrastructure as engineering afterthoughts. Acme Corp's published work on evaluation frameworks and dataset curation treats these as core research questions — that's the intellectual environment I want to work in.
- **The scale of the evaluation problem they're tackling.** Acme's model evaluation infrastructure handles dozens of benchmarks across multiple model families simultaneously. That's exactly the kind of cross-cutting infrastructure challenge I've been gravitating toward — DataForge exists because I got tired of evaluation pipelines breaking in non-obvious ways.
- **Fellowship structure that actually embeds engineers with researchers.** A lot of "research engineer" roles end up being glorified DevOps. The Acme fellowship rotates fellows through active research projects and expects engineering contributions to appear in papers. That's a different contract, and it's the one I want.

## Why This Role

- **My infrastructure work is already research-adjacent.** DataForge's schema validation and lineage tracking aren't just engineering niceties — they're answers to the question "how do we know a model was trained on what we think it was trained on?" That question is squarely in the fellowship's scope.
- **I've debugged the failure modes this role exists to prevent.** Sentinel caught a silent data corruption issue at Meridian Labs that had been subtly skewing a production model for six weeks before anyone noticed. I know what those failure modes look like from the inside, which makes me a more useful collaborator for researchers thinking about them abstractly.
- **Open-source track record means I can write code that survives contact with other engineers.** My scikit-learn contributions went through rigorous review from maintainers who care deeply about API stability and correctness. That discipline carries over to research code that needs to be reproducible and extensible.

## Key Numbers to Reference

| Claim | Number | Source |
|-------|--------|--------|
| DataForge codebase size | 32,000 LOC (Python + Rust) | GitHub repo, line count |
| DataForge daily throughput | ~2M records/day | Meridian Labs production metrics |
| DataForge p99 pipeline latency | <50ms | Internal benchmarks |
| Sentinel codebase size | 18,000 LOC (Python + Go) | GitHub repo |
| Years of production engineering | 6 (2020–2026) | Resume |
| scikit-learn contributions | 4 merged PRs, 2 open issues resolved | GitHub contribution history |

## Potential Interview Questions

- "Tell me about a time you had to make a tradeoff between engineering rigor and shipping speed."
  My answer: When DataForge was first adopted by a second team at Meridian Labs, they wanted to disable the schema validation layer because it was adding ~8ms per batch. I pushed back and instead profiled the validator — found that 90% of the overhead came from a single regex compiled inside a hot loop. Fixed it, brought overhead down to under 1ms, and kept the validation. The right answer wasn't to cut the safety check; it was to make the safety check cheap enough that there was no argument for cutting it.

- "How do you approach designing infrastructure that researchers can actually use?"
  My answer: I've learned to build the unhappy path first. Researchers will always find a way to feed unexpected data into a pipeline. With DataForge I wrote the error messages before I wrote the happy-path logic — that forced me to think through what information a researcher actually needs when something breaks at 2am before a deadline. The result is that adoption at Meridian was almost entirely self-service; I don't get paged about DataForge issues.

- "What's your experience with ML model evaluation?"
  My answer: At Meridian Labs I built the evaluation harness that runs nightly regression tests on our production models. It compares outputs across a fixed evaluation set and flags statistical deviations above a configurable threshold. That work made me deeply skeptical of single-number metrics — a model can hold its aggregate score steady while quietly degrading on a specific input slice. Sentinel's anomaly detection applies the same instinct to streaming data.

- "Where do you think data quality tooling is still immature?"
  My answer: Lineage. Most tools tell you whether data is clean at a point in time, but almost nothing tracks *why* a dataset looks the way it does — which upstream transformation introduced a particular distribution shift, or which cleaning decision three months ago is now causing a model to underperform on a new input type. DataForge has a basic lineage graph, but it's nowhere near good enough. I'd love to work on that problem seriously.

- "How do you handle disagreement with a researcher about technical approach?"
  My answer: I try to make the disagreement concrete as fast as possible. Abstract debates about architecture go nowhere. At Meridian I had a long back-and-forth with a research lead about whether to use a streaming or batch paradigm for Sentinel's inference layer. I spent a day building a minimal prototype of both approaches against our actual data volume and latency requirements. The prototype ended the debate in about fifteen minutes. Usually when engineers and researchers disagree it's because they're imagining different constraints — making the constraints visible tends to collapse the disagreement.

## Questions to Ask Interviewers

1. How does the fellowship structure balance time between research contributions and infrastructure support? Is there a typical breakdown, or does it vary by project?
2. What does it look like when a fellow's engineering work ends up shaping a research direction rather than just enabling it — has that happened in past cohorts?
3. What's the current biggest pain point in the data pipeline or evaluation infrastructure that the team wishes it had more bandwidth to address?
