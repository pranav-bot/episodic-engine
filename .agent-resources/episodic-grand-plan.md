# Episodic Context Engine Grand Plan

## Problem Statement

How might we evolve Episodic beyond context version control into an
experiment-driven context engine that ingests unstructured data, builds and
merges large graphs, selects bounded subgraphs, searches them quickly, and
delivers evidence-grounded context to agent harnesses with fewer irrelevant
tokens?

## Product Thesis

Episodic is a **context compiler and retrieval engine**. It transforms
unstructured organizational data into a versioned, provenance-preserving,
multi-resolution graph. It then compiles user queries into a bounded context
package containing the smallest useful set of nodes, relationships, summaries,
and source evidence.

Agent harnesses consume that retrieval layer through a read-only MCP server.
A named graph or saved subgraph is an enforced context boundary, not a prompt
instruction. The harness can search and traverse only within the scope it was
given.

The project is research-led: representation, ingestion, merging, subgraph
selection, and retrieval strategies must be compared on the same corpus,
queries, scope, output contract, and context budget.

## Recommended Direction

Build one end-to-end vertical slice before building independent subsystems:

1. Ingest a small unstructured corpus.
2. Compile it into a multi-resolution graph with provenance.
3. Select a named graph or saved subgraph.
4. Search the bounded scope through one retrieval contract.
5. Expose that contract through MCP to an agent harness.
6. Compare deterministic, embedding, and model-guided retrieval on fixed tasks.

Compare all three retrieval strategies from day one, but keep deterministic
retrieval as the control. Every strategy must operate on the same compiled
representation and return the same evidence-first result format. This avoids
confusing search quality with differences in ingestion, corpus, or output
format.

The initial performance target is 1–10 seconds for retrieval. The first scale
milestone is 10,000 nodes, followed by larger controlled milestones based on
measured graph growth, edge density, ingestion time, storage size, and query
distribution. “Exponential-scale graphs” is a research ambition, not a useful
benchmark until these distributions are explicit.

## Grand Plan

### Phase 0 — Measurement Contract

Define before optimizing:

- Fixed representative organizational tasks and queries.
- Human usefulness rubric: relevance, completeness, evidence quality,
  answerability, and unnecessary context.
- Retrieval metrics: p50/p95 latency, token count, irrelevant-result count,
  source coverage, and failure rate.
- Ingestion metrics: throughput, extraction quality, graph growth, storage
  size, and provenance coverage.
- Scope and budget rules for named graphs and saved subgraphs.
- A common result schema for all retrieval strategies and MCP tools.

### Phase 1 — Representation and Ingestion

Compile unstructured sources into linked layers:

- source files and source spans
- documents and chunks
- entities
- claims and facts
- relationships and events
- summaries at multiple resolutions
- provenance and version references

Run representation experiments using the same source corpus. Compare flat
chunks, typed graphs, claim graphs, hierarchical summaries, and hybrid
representations. Preserve enough source evidence to audit every returned
claim.

### Phase 2 — Unified Retrieval Core

Create one retrieval interface with pluggable strategies:

- **Deterministic baseline:** lexical search, typed filters, and bounded graph
  traversal.
- **Embedding retrieval:** vector candidate generation followed by graph and
  provenance filtering.
- **Model-guided retrieval:** a model proposes or ranks traversal actions
  under explicit latency, token, and scope budgets.

All strategies must support:

- graph or subgraph scope
- bounded traversal
- result and token budgets
- evidence-first output
- relationship paths
- source references
- reproducible experiment records

### Phase 3 — Graph and Subgraph Management

Add graph operations in this order:

1. Named graph identity and registry.
2. Saved subgraph selection from node IDs, queries, types, or relationships.
3. Immutable subgraph snapshots for reproducible harness runs.
4. Partial graph export and import.
5. Graph merging with source lineage, conflict representation, and freshness.

Merging must never silently overwrite conflicting claims. Every merged result
needs provenance showing which source graphs contributed it.

### Phase 4 — Harness Integration

Expose the retrieval core through a read-only MCP-style server:

- `search_context`
- `get_node`
- `get_neighbors`

The server resolves a named graph or saved subgraph, enforces that scope for
every operation, applies the context budget, and returns:

- matching nodes
- relevant content
- provenance
- relationship paths
- scope identity
- budget usage
- retrieval strategy and experiment metadata

MCP is the shared adapter boundary for Claude Code, Copilot, OpenCode,
Antigravity, and other compatible harnesses. Avoid separate harness-specific
retrieval implementations.

### Phase 5 — Scale and Search Research

Scale the same benchmark across controlled graph sizes and densities:

- 10,000 nodes
- 100,000 nodes
- 1,000,000 nodes
- larger sizes only when the previous milestone is understood

Experiment with:

- indexing strategies
- graph partitioning
- multi-resolution routing
- approximate nearest-neighbor search
- embedding models
- traversal policies
- model-guided search
- caching and precomputed summaries
- query-specific context budgets

Report quality and cost together. A faster search that returns worse context
or consumes more tokens is not an improvement.

## Key Assumptions to Validate

- [ ] Multi-resolution representations improve usefulness over flat chunks or
      a single-resolution graph.
- [ ] Unstructured ingestion can produce useful entities, claims, and
      relationships without unacceptable provenance loss.
- [ ] The same compiled representation can support deterministic, embedding,
      and model-guided retrieval fairly.
- [ ] Bounded graph and subgraph scopes reduce irrelevant context without
      causing unacceptable missing context.
- [ ] Evidence-first results improve answer quality and auditability.
- [ ] A context budget reduces tokens without materially harming usefulness.
- [ ] Graph merging can preserve conflicting claims, lineage, and freshness.
- [ ] MCP configuration is reliable across target harnesses.
- [ ] Coarse-to-fine retrieval can meet the 1–10-second target at 10,000 nodes.
- [ ] Human reviewers can consistently score fixed retrieval tasks.

## MVP Scope

The first delivery is one vertical slice:

- Ingest a bounded set of unstructured documents.
- Compile a multi-resolution, provenance-preserving graph.
- Create or select a named graph and saved subgraph.
- Run deterministic, embedding, and model-guided retrieval behind one
  interface.
- Enforce graph/subgraph scope and a result or token budget.
- Expose read-only retrieval through the three MCP tools.
- Return bounded evidence-first context to a harness.
- Benchmark fixed tasks using human usefulness scores, token counts,
  irrelevant-result counts, and p50/p95 latency.
- Begin at 10,000 nodes.

## Not Doing Yet

- **Context version control as the product endpoint** — versioning is
  infrastructure for reproducibility, not the primary user value.
- **Unrestricted graph walks** — they undermine latency and context budgets.
- **Silent graph merge conflicts** — correctness and provenance come first.
- **MCP mutations** — keep the harness interface read-only initially.
- **Dynamic scope expansion** — validate bounded scopes before allowing agents
  to request more context.
- **Harness-specific search implementations** — use the shared MCP contract.
- **Autonomous agent loops** — Episodic supplies context; the harness reasons.
- **Optimizing only for latency** — quality, evidence, and token use are
  equally important.
- **Production-scale infrastructure before benchmarks** — prove the
  representation and retrieval behavior first.

## Risks and Guardrails

| Risk | Guardrail |
|---|---|
| Model-guided search hides weak representation quality | Keep deterministic control and compare identical inputs |
| Scope is too narrow and causes missing context | Measure recall and source coverage, not only noise |
| Scope is too broad and recreates token waste | Enforce budgets and report irrelevant-result counts |
| Merging destroys trust | Preserve source lineage and represent conflicts explicitly |
| MCP becomes a thin wrapper around poor search | Benchmark retrieval independently before harness evaluation |
| “Exponential graph” remains vague | Use explicit node, edge, density, and query-distribution milestones |
| Ingestion quality is anecdotal | Maintain fixed source corpora and human-reviewed extraction samples |

## Open Questions

- Which resolution levels produce the best quality-to-cost tradeoff?
- What should be a node, edge, claim, event, or first-class evidence object?
- How should stale, duplicated, and contradictory information be represented?
- How are saved subgraphs named, versioned, invalidated, and shared?
- Should subgraphs be immutable during a harness run?
- How should token budgets be estimated across model families?
- Which embedding and model-guided strategies are fair first baselines?
- What query distribution represents real organizational context use?
- What is the acceptable ingestion cost for each graph-scale milestone?

## Success Definition

The project is succeeding when, on fixed organizational tasks, Episodic can:

1. ingest and compile unstructured data with auditable provenance;
2. search a bounded graph or subgraph within 1–10 seconds;
3. return context that human reviewers judge useful and close to the query;
4. reduce irrelevant context and model tokens against a flat or unrestricted
   baseline; and
5. deliver the same controlled retrieval capability to agent harnesses through
   MCP.
