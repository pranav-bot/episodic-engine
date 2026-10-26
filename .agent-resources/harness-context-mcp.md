# Scoped Graph MCP Context

## Problem Statement

How might we let agent harnesses such as Claude Code, Copilot, OpenCode, and
Antigravity use a bounded graph or subgraph as their context world, retrieve
only relevant evidence, and improve answer quality while reducing irrelevant
context and token usage?

## Recommended Direction

Build a read-only MCP-style Episodic context server. A harness selects a named
graph or saved subgraph, and the server enforces that scope for every request.
The scope is an access boundary, not merely a prompt hint: agents cannot
traverse outside the graph or subgraph they were given.

Expose evidence-first retrieval rather than raw text search. Results should
include relevant nodes, source references, relationship paths, scope identity,
and budget usage. Support a bounded result or token budget so the harness
receives a small, explainable context package instead of an unbounded graph
walk.

The first experiment should compare scoped retrieval with unrestricted or flat
retrieval on fixed tasks. Evaluate human usefulness alongside token counts,
irrelevant-result counts, and p50/p95 retrieval latency.

## Key Assumptions to Validate

- [ ] MCP configuration works reliably across the first target harnesses.
- [ ] Named graphs and saved subgraphs form useful context boundaries for real
      agent tasks.
- [ ] Enforced scope prevents irrelevant retrieval without causing excessive
      missing context.
- [ ] Evidence-first results improve answer quality and make answers easier to
      verify.
- [ ] A result or token budget reduces context size without materially harming
      answer quality.
- [ ] Human reviewers can consistently score context usefulness for fixed tasks.

## MVP Scope

- Read-only MCP server.
- Resolve both named graphs and saved subgraphs.
- Enforce the selected scope on every operation.
- Provide three tools:
  - `search_context`
  - `get_node`
  - `get_neighbors`
- Return node content, provenance, relationship paths, scope identity, and
  budget usage.
- Support a maximum result or token budget.
- Compare scoped retrieval against a flat or unrestricted baseline.
- Record usefulness scores, token counts, irrelevant-result counts, and
  p50/p95 latency.

## Not Doing (and Why)

- **Graph mutations through MCP** — keep the first harness contract safe and
  read-only.
- **Dynamic scope expansion** — it weakens the bounded-context promise and can
  be added after the core is measured.
- **Unrestricted graph access** — it recreates the noise and token problems the
  feature is meant to solve.
- **Harness-specific integrations** — MCP should be the shared adapter boundary;
  separate adapters would multiply maintenance.
- **Autonomous agent behavior** — Episodic should provide context, not own the
  harness's reasoning loop.
- **Advanced embedding or learned traversal** — first establish whether scoped,
  evidence-first retrieval is useful at all.

## Open Questions

- How are saved subgraphs created, named, versioned, and invalidated?
- Should a subgraph be immutable while a harness is running?
- What exact fields and formats should the MCP tools return?
- How should token budgets be estimated across different models?
- What baseline best represents current harness behavior?
- Which fixed tasks and reviewer rubric make usefulness measurable?
