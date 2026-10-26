# Capability Map: Initial Graph Core

**Status:** Draft for review (2026-10-27). Review decisions are folded in. No open questions remain on the three module specs.  
**Location:** specs live in `.agent-resources/` (this repo’s planning system, not a second spec format)  
**North star:** [episodic-grand-plan.md](./episodic-grand-plan.md) — these modules are the first build focus (representation, ingestion, fast structural search). Harness MCP, embeddings, and model-guided retrieval stay later.

| Module id | Responsibility | Depends on | Spec |
|---|---|---|---|
| `graph-model` | Traversal-oriented node, edge, and adjacency contract. Stable ids, typed links, hot properties separated from source bytes. | — | [SPEC-graph-model.md](./SPEC-graph-model.md) |
| `corpus-ingestion` | Turn a folder of structured and unstructured context (code, Markdown, PDFs, images) into a graph that satisfies `graph-model`. Coding repository is the benchmark corpus. | `graph-model` | [SPEC-corpus-ingestion.md](./SPEC-corpus-ingestion.md) |
| `graph-search` | Id lookup, typed filters, and bounded traversal that stay fast as the graph grows through explicit size milestones. | `graph-model` | [SPEC-graph-search.md](./SPEC-graph-search.md) |

**Build order:** `graph-model` → `corpus-ingestion` and `graph-search` (parallel once the graph contract is approved).

An end-to-end check — search a graph produced by ingesting a coding repo — waits until both dependents exist. That check is recorded on `graph-search`; it does not create a dependency cycle. `graph-search` can be proven on a synthetic graph that already matches `graph-model`.

**Interfaces:** `graph-model` owns the contract both other modules use. Ingestion writes that shape. Search reads it. Neither module redefines node or edge fields.

## Decisions

1. Edge types for now are `contains`, `imports`, `calls`, `references`, and `describes`. Adding a type later means editing [SPEC-graph-model.md](./SPEC-graph-model.md) first.
2. The in-memory adjacency graph ships at `demo-graph/test-graph/`. Demos and tests load that graph. It is not a tests-only copy.
3. Corpus ingest selects an organizer per file. Python and Markdown organizers do not call a model. PDFs, images, and other unstructured files use a model organizer when structure is not enough to place context on the graph. `ingest-corpus` builds on `episodic ingest-node` and does not replace that command. One graph per `--name`. `episodic merge-graphs --into <name> --from <name>` unions two named graphs.
4. An in-memory adjacency list is acceptable at 100k nodes when the report says `driver=in-memory-adjacency`. The p95 table in [SPEC-graph-search.md](./SPEC-graph-search.md) is the iteration-1 target. A later iteration may change those numbers only by editing that table after the experiment is recorded. The driver name alone does not waive a recorded miss.
5. A walk over a graph produced by ingest is specified after `corpus-ingestion` exists. It is not part of [SPEC-graph-search.md](./SPEC-graph-search.md).
6. `--skip-assets` stays: it skips PDF and image files and still runs `markdown-node`.
7. The live model behind `model-context` is not chosen in these specs. Tests use a fake organizer. Naming a provider is a later spec.
8. Label prefix search is case-insensitive (`str.casefold`).

## Assumptions

1. The benchmark gate is a small in-repo coding fixture (Python, one Markdown file, one PDF, one image), not an unbounded organization dump.
2. “Exponential graph” means controlled growth milestones (10k, then 100k, then 1M nodes) at mean out-degree 4. It does not mean unbounded walks.
3. This phase’s search is structural and lexical (id, type, label, bounded traversal). Embedding and model-guided strategies stay in the grand plan.
4. The file-based Markdown graph in `src/episodic/graph.py` is a prototype. These specs do not require migrating that CLI inside `graph-model`.
5. Runtime is Python 3.11+, tests are pytest, CLI is Typer. Neo4j is not required to pass these three specs.

Correct the map or the assumptions before implementation. Planning and code start only after you approve these specs.
