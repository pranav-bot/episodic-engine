# Episodic Engine — Planning Resources

Planning documents for a **Context Management System** that sits on top of [graphify](https://github.com/safishamsi/graphify) and turns static `graph.json` subgraphs into a **dynamic, version-controlled Supergraph** suitable for LLM memory.

**Status:** Draft for review (2026-07-06)  
**Scope:** Architecture, schema, entity resolution, query routing, time-travel — no implementation code.

---

## Document Index

| # | Document | Purpose |
|---|----------|---------|
| 00 | [System Overview](./00-system-overview.md) | Executive summary, glossary, design principles |
| 01 | [Architecture Overview](./01-architecture-overview.md) | Components, data flow, graphify bridge |
| 02 | [Temporal Schema Design](./02-temporal-schema-design.md) | Episodic versioning without graph bloat |
| 03 | [Entity Resolution](./03-entity-resolution.md) | Cross-subgraph deduplication and merge logic |
| 04 | [Query Routing Engine](./04-query-routing-engine.md) | NL query → subgraph vs supergraph routing |
| 05 | [Storage & Database Decision](./05-storage-and-database-decision.md) | Neo4j vs alternatives, recommended stack |
| 06 | [Time-Travel Queries](./06-time-travel-queries.md) | Point-in-time graph retrieval examples |
| 07 | [Feature Backlog & Phasing](./07-feature-backlog-and-phasing.md) | MVP scope, phased rollout, open decisions |
| 08 | [Graphify Integration](./08-graphify-integration.md) | Leveraging existing graphify capabilities |
| 09 | [Hybrid Architecture](./09-hybrid-architecture.md) | **Approved profile** — hot/warm/cold tiers, pluggable backends |
| — | [Single Subgraph Save PRD](./prds/2026-07-06-single-subgraph-save.md) | **Current slice** — init + save, cold+warm only |

---

## Recommended Reading Order

1. **00** + **09** — orient yourself; hybrid is the chosen profile  
2. **01** + **05** — architecture and storage choice  
3. **02** + **03** — the hard problems (time + merging)  
4. **04** + **06** — how LLMs will query the system  
5. **07** + **08** — what to build first and what graphify already gives you

---

## Key Recommendation (TL;DR)

| Decision | Recommendation |
|----------|----------------|
| **Deployment profile** | **Hybrid** — local-first, pluggable backends ([09](./09-hybrid-architecture.md)) |
| Supergraph store | **Neo4j** (with NetworkX fallback for lite/offline) |
| Episode / audit log | **SQLite locally → PostgreSQL for team** (same interface) |
| Subgraph snapshots | **Immutable blobs** — filesystem locally, S3 for team |
| Subgraph queries | **Delegate to graphify**; Neo4j for supergraph/temporal only |
| Versioning model | **Git-like deltas**, not full graph copies per episode |
| Entity resolution | **Deterministic keys first**, embeddings second, LLM adjudication last |
| graphify integration | **Wrap, don't fork** — ingest via CLI output + extend with episodic overlay |

---

## Next Step

Design **approved** (hybrid profile). Implementation plan:

→ **[plans/2026-07-06-phase1-hybrid-local.md](./plans/2026-07-06-phase1-hybrid-local.md)**
