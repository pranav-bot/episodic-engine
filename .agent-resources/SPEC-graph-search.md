# Spec: graph-search

**Module id:** `graph-search`  
**Status:** Draft for review (2026-10-27)  
**Map:** [capability-map-initial-graph.md](./capability-map-initial-graph.md)  
**Depends on:** [SPEC-graph-model.md](./SPEC-graph-model.md)  
**Later consumer of:** [SPEC-corpus-ingestion.md](./SPEC-corpus-ingestion.md) (end-to-end check only)  
**Background:** [episodic-grand-plan.md](./episodic-grand-plan.md) Phase 2 and Phase 5, [04-query-routing-engine.md](./04-query-routing-engine.md)

## Objective

Look up nodes and walk a bounded neighborhood quickly as the graph grows, without loading source payloads and without scanning the whole edge set.

**User:** Episodic’s query path (CLI now, harness later). The caller has a node id, a label fragment, or a type filter and needs a small, repeatable set of nodes and edges.

**Why “exponential” is specified as milestones:** latency cannot be “superfast” at every size without a size, a density, and a query shape. This spec locks those. Growing from 10k to 100k to 1M nodes is the scale ladder. Unbounded walks are a failure, not a feature.

### PRD scope

**In scope**

- Lookup by node id.
- Filter by node type and exact label, plus a prefix match on label. Prefix and exact label compare with `str.casefold`, so `Auth` matches `auth`.
- One-hop `neighbors` (already required by `graph-model`) exposed as a search operation with the same semantics.
- Bounded traversal: breadth-first from a start id, max depth, max nodes returned, optional edge-type allow-list.
- Deterministic ordering: by `(depth, node_id)` so the same graph version returns the same list.
- A generator that builds a synthetic graph at a target node count and average out-degree, for benchmarks that do not wait on ingestion.
- Latency targets below, measured warm, single process, local machine, on the shipped in-memory adjacency graph (`demo-graph/test-graph`). The 10k and 100k milestones both use that driver. The 1M milestone is record-only in this phase (write down p50/p95; do not block the spec on meeting the 10k target at 1M).

**Out of scope**

- Embeddings, vector search, model-guided traversal, natural-language routing, token budgets, MCP tools.
- Time-travel (`as_of`) and cross-repo supergraph merge.
- All-pairs shortest paths, PageRank, and community detection.
- Returning file or PDF bodies in the search result. Results are hot records plus the edges walked.

### Acceptance stories

- As a caller, I start at a function node, follow only `calls` edges to depth 2, and get at most N nodes.
- As a caller, I repeat that query and get the same ids in the same order.
- As a reviewer, I can show the query did not read every edge in a 10k-node graph.

## Tech Stack

- Python 3.11+
- Python 3.11+
- The shipped adjacency graph at `demo-graph/test-graph/` for correctness tests and for the 10k and 100k latency gates
- pytest. Timing uses `time.perf_counter` around the query, after a warmup call. No new benchmark framework unless you ask.

The 100k gate may use that in-memory adjacency list. The run passes only when both are true: the report line includes `driver=in-memory-adjacency`, and every p95 in the table below is met. If a target is missed, the test fails. The driver name is not a waiver. Do not substitute a smaller graph or a looser number. Neo4j is not required for this gate.

## Commands

```bash
pip install -e ".[dev]"
python -m pytest tests/unit/test_graph_search.py -q
python -m pytest tests/benchmark/test_graph_search_scale.py -q --override-ini="addopts="
```

Benchmark tests are marked `pytest.mark.benchmark` and are excluded from the default `python -m pytest` run if they would make CI slow. Default CI runs the 10k correctness-and-budget test only if it stays under 5 seconds; otherwise it is marked `benchmark` too. Decision at implementation time: if 10k in-memory exceeds 5 seconds, mark it and do not silently drop the assertion.

CLI (thin wrapper, same function the tests call):

```bash
episodic search neighbors --graph <name> --node <id> --edge-type calls
episodic search walk --graph <name> --node <id> --depth 2 --limit 200 --edge-type calls
episodic search label --graph <name> --prefix auth --type symbol --limit 50
```

## Project Structure

```text
src/episodic/search/walk.py       → bounded BFS and label filter
src/episodic/search/scale.py      → synthetic graph builder for tests
src/episodic/cli/main.py          → search subcommands
demo-graph/test-graph/adjacency.py → graph the benchmarks run against
tests/unit/test_graph_search.py
tests/benchmark/test_graph_search_scale.py
.agent-resources/SPEC-graph-search.md
```

Search calls `demo-graph/test-graph`. It does not import graphify or the corpus walker.

## Code Style

```python
def walk(
    graph: Graph,
    start: NodeId,
    *,
    depth: int,
    limit: int,
    edge_types: frozenset[EdgeType] | None = None,
) -> tuple[NodeId, ...]:
    """Bounded BFS. depth and limit are required and must be >= 1."""
    if depth < 1 or limit < 1:
        raise ValueError("depth and limit must be >= 1")
    ...
```

Conventions:

- `depth` and `limit` are required. There is no default that means “whole graph.”
- Maximum accepted `depth` for this phase is 5. Maximum accepted `limit` is 2_000. Larger values raise `ValueError`.
- Results are hot ids (and edge ids if the caller asks). Payload fetch is a different function and is not called from `walk`.
- Compare node ids as strings. Do not sort by label when returning a walk; order is `(depth, node_id)`.
- Label prefix and exact label match are case-insensitive via `str.casefold`. Node ids stay case-sensitive.

## Testing Strategy

- **Unit:** tiny hand-built graphs. Assert depth cutoff, limit cutoff, edge-type filter, deterministic order, missing start id, and rejection of `depth=0` or `limit=0`.
- **Scale:** synthetic graphs.

| Milestone | Nodes | Mean out-degree | What this phase requires |
|---|---|---|---|
| S | 10_000 | 4 | Report p95 against the iteration-1 table |
| M | 100_000 | 4 | Same report, `driver=in-memory-adjacency` |
| L | 1_000_000 | 4 | Record p50/p95 only; not a pass/fail gate yet |

Query shapes (fixed, same at every milestone):

1. One-hop neighbors of a node whose degree is the median degree.
2. Walk depth 3, `limit=200`, all edge types.
3. Label prefix that matches 20 nodes (builder plants those labels).

**Latency targets (warm, p95 of 20 runs after 3 warmup runs):**

| Query | 10k | 100k |
|---|---|---|
| One-hop neighbors | < 5 ms | < 20 ms |
| Walk depth 3, limit 200 | < 50 ms | < 150 ms |
| Label prefix, limit 50 | < 20 ms | < 50 ms |

These are the **iteration-1** targets for this structural slice. They replace a vague “superfast” bar. The grand plan’s 1–10 second budget still applies later, when retrieval includes ranking and evidence packaging.

The numbers are allowed to move between iterations. An iteration records p50 and p95 for the three queries. If a target is missed, write the observed times next to the iteration. The next iteration either meets the table or this table is edited with the observed result and the reason. Do not change the assertion in code and leave this table stale. A miss on iteration 1 is an experiment result, not a silent pass.

**Work bound:** for the depth-3 walk, the number of adjacency lookups is at most `limit * mean_degree` order, and the test graph’s edge count is not passed into the query function as a loop bound. A test with a counting wrapper fails if `neighbors` is called once per edge in the full graph.

A walk of a graph produced by `ingest-corpus` is out of this spec. Add that check only after `corpus-ingestion` exists.

## Boundaries

- **Always:** require depth and limit; keep walks deterministic; measure the three query shapes on synthetic graphs; keep payloads out of results; record 1M numbers without pretending they are a gate.
- **Ask first:** adding a database or ANN library; raising depth/limit caps; editing the iteration target table; turning benchmark tests on in default CI if they need Docker or Neo4j.
- **Never:** offer an unbounded walk flag; scan all nodes to answer a one-hop query; hide a missed latency target by reducing the synthetic graph size; call an LLM on the search path.

## Success Criteria

- [ ] `walk` and label search reject missing caps and caps above the maxima.
- [ ] Unit tests show depth, limit, edge type, stable order, and that prefix `Auth` matches a node labeled `auth`.
- [ ] On the 10k and 100k synthetic graphs, the run reports p50 and p95 for all three query shapes against the current table, with `driver=in-memory-adjacency` on the 100k line.
- [ ] Iteration 1 uses the table in this spec. A miss is recorded with the observed times. A later target change is an edit to that table, not a test-only change.
- [ ] A counting test shows one-hop and bounded walk do not call `neighbors` once per edge in the full graph.
- [ ] The 1M run, if executed, writes p50/p95 next to the test output and does not fail the suite for being slower than the 10k target.
- [ ] Search results contain no cold payload fields.

## Open Questions

None for this module. Label match is case-insensitive. 100k may run on the in-memory adjacency list when the report says `driver=in-memory-adjacency`. The p95 table is iteration 1 and may be revised after each recorded experiment. The ingest-repo walk waits until `corpus-ingestion` exists.
