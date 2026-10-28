# Episodic Engine — Planning Resources

Planning documents for **Episodic**: a **context compiler and retrieval engine** for agent harnesses. It sits on [graphify](https://github.com/safishamsi/graphify), turns static `graph.json` outputs into **versioned, mergeable memory**, and (on the roadmap) compiles bounded, evidence-first context packs for MCP tool loops.

**Status:** Active planning (updated 2026-10-27)  
**North star:** [Episodic Grand Plan](./episodic-grand-plan.md) — research-led vertical slice, harness MCP, measurement contract  
**Current implementation slice:** [Single Subgraph Save PRD](./prds/2026-07-06-single-subgraph-save.md) (`episodic init` / `save` / `status`, cold + warm storage)

---

## How the docs fit together

| Layer | What it answers | Start here |
|-------|-----------------|------------|
| **Grand Plan** | Why, product thesis, phases 0–5, MVP vertical slice, benchmarks | [episodic-grand-plan.md](./episodic-grand-plan.md) |
| **Architecture (00–09)** | How — supergraph, episodes, resolution, routing, storage, graphify bridge | [00](./00-system-overview.md) → [09](./09-hybrid-architecture.md) |
| **Implementation track** | What to build in order — hybrid-local Phase 1–3, feature backlog | [07](./07-feature-backlog-and-phasing.md), [phase1 plan](./plans/2026-07-06-phase1-hybrid-local.md) |
| **Initial graph specs** | Graph contract, corpus ingest, bounded search | [capability map](./capability-map-initial-graph.md) |
| **PRDs** | Thin slices | [graph model](./prds/2026-10-27-graph-model.md), [single subgraph save](./prds/2026-07-06-single-subgraph-save.md) |

The **Grand Plan** and the **July 2026 architecture set** describe the same system at different altitudes. The grand plan emphasizes experiment-driven retrieval, harness MCP, and token budgets; docs 00–09 specify supergraph synthesis, temporal episodes, and hybrid storage. Neither replaces the other — [07](./07-feature-backlog-and-phasing.md) maps grand-plan phases onto concrete features and build order.

---

## Document Index

| # | Document | Purpose |
|---|----------|---------|
| — | **[Grand Plan](./episodic-grand-plan.md)** | **North star** — context compiler, retrieval strategies, MCP harness boundary, scale research |
| 00 | [System Overview](./00-system-overview.md) | Executive summary, glossary, design principles |
| 01 | [Architecture Overview](./01-architecture-overview.md) | Components, data flow, graphify bridge |
| 02 | [Temporal Schema Design](./02-temporal-schema-design.md) | Episodic versioning without graph bloat |
| 03 | [Entity Resolution](./03-entity-resolution.md) | Cross-subgraph deduplication and merge logic |
| 04 | [Query Routing Engine](./04-query-routing-engine.md) | NL query → scope; evolves into unified retrieval core |
| 05 | [Storage & Database Decision](./05-storage-and-database-decision.md) | Neo4j vs alternatives, recommended stack |
| 06 | [Time-Travel Queries](./06-time-travel-queries.md) | Point-in-time graph retrieval examples |
| 07 | [Feature Backlog & Phasing](./07-feature-backlog-and-phasing.md) | **Implementation track** mapped to Grand Plan phases |
| 08 | [Graphify Integration](./08-graphify-integration.md) | Leveraging existing graphify capabilities |
| 09 | [Hybrid Architecture](./09-hybrid-architecture.md) | **Approved profile** — hot/warm/cold tiers, pluggable backends |
| — | [Graph model PRD](./prds/2026-10-27-graph-model.md) | **Next build** — hot graph contract only |
| — | [Graph model plan](./plans/2026-10-27-graph-model.md) | Tasks 1–4 for `SPEC-graph-model` |
| — | [Single Subgraph Save PRD](./prds/2026-07-06-single-subgraph-save.md) | Earlier slice — init + save, cold+warm only |
| — | [Initial graph capability map](./capability-map-initial-graph.md) | Draft modules: `graph-model`, `corpus-ingestion`, `graph-search` |
| — | [SPEC-graph-model](./SPEC-graph-model.md) | Traversal-oriented node and edge contract |
| — | [SPEC-corpus-ingestion](./SPEC-corpus-ingestion.md) | Folder → graph; coding repo benchmark |
| — | [SPEC-graph-search](./SPEC-graph-search.md) | Bounded search with 10k / 100k / 1M milestones |
| — | [ADR-001](../docs/decisions/ADR-001-stdio-mcp-context-graph.md) | **Accepted** — stdio MCP creates a Python + Markdown context graph |
| — | [Context graph idea](../docs/ideas/context-graph-from-folder.md) | One-pager for that first harness slice |

---

## Recommended Reading Order

1. **[Grand Plan](./episodic-grand-plan.md)** + **00** — product direction and supergraph mental model  
2. **09** + **01** + **05** — approved hybrid deployment and storage  
3. **02** + **03** — versioning and merging (Grand Plan Phase 3 foundations)  
4. **04** + **06** — query scope, time-travel, context packaging (Grand Plan Phase 2)  
5. **07** + **08** + **phase1 plan** — what to build next and what graphify already provides  

---

## Key Recommendation (TL;DR)

| Decision | Recommendation |
|----------|----------------|
| **Product direction** | **Context compiler + retrieval** for harnesses ([Grand Plan](./episodic-grand-plan.md)); versioning is infrastructure, not the endpoint |
| **Deployment profile** | **Hybrid** — local-first, pluggable backends ([09](./09-hybrid-architecture.md)) |
| Supergraph store | **Neo4j** (with NetworkX fallback for lite/offline) |
| Episode / audit log | **SQLite locally → PostgreSQL for team** (same interface) |
| Subgraph snapshots | **Immutable blobs** — filesystem locally, S3 for team |
| Subgraph queries | **Delegate to graphify**; Neo4j for supergraph/temporal only |
| Versioning model | **Git-like deltas**, not full graph copies per episode |
| Entity resolution | **Deterministic keys first**, embeddings second, LLM adjudication last |
| graphify relationship | **Wrap, don't fork** — ingest via CLI output + episodic overlay |
| Harness boundary | **Read-only MCP** — `search_context`, `get_node`, `get_neighbors`; enforced graph/subgraph scope + token budget |
| Retrieval research | **Three strategies on one representation** — deterministic control, embedding, model-guided ([Grand Plan](./episodic-grand-plan.md) Phase 2) |

---

## Next Step

**In repo today:** single-subgraph save (PRD). **Next engineering milestone:** hybrid-local Phase 1 core loop.

→ **[plans/2026-07-06-phase1-hybrid-local.md](./plans/2026-07-06-phase1-hybrid-local.md)**  
→ Phase mapping and backlog: **[07-feature-backlog-and-phasing.md](./07-feature-backlog-and-phasing.md)**
