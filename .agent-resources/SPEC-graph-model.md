# Spec: graph-model

**Module id:** `graph-model`  
**Status:** Draft for review (2026-10-27)  
**Map:** [capability-map-initial-graph.md](./capability-map-initial-graph.md)  
**Background:** [02-temporal-schema-design.md](./02-temporal-schema-design.md), [08-graphify-integration.md](./08-graphify-integration.md)

## Objective

Define the graph Episodic stores so a caller can move from a node to its typed neighbors without scanning the corpus or loading source bytes.

**User:** ingestion and search inside Episodic, and later a harness that receives node ids. Not a person editing JSON by hand.

**Why:** a folder of code and documents becomes useful only if the graph can be walked by id, type, and edge type. Today’s prototype (`name` / `nodes` / `links` plus full Markdown `content` on the node) mixes display payload with structure. Traversal on a large graph needs the opposite split.

### PRD scope

**In scope**

- Canonical node and edge records aimed at adjacency queries.
- Stable node ids that survive a re-ingest of the same source identity.
- Typed edges. The set is `contains`, `imports`, `calls`, `references`, `describes`. That set is enough for this phase. A new type is a later spec change, not a runtime extension.
- A hot record (id, type, label, neighbor index keys) separate from cold payload (file text, PDF bytes, image bytes, long summaries).
- Provenance pointer on every node: source path plus a locator (line span, page, or byte span) when the extractor provides one.
- The shipped in-memory graph at `demo-graph/test-graph/`, used by the demo and by tests. Adjacency is a map from node id to outgoing and incoming edges. Neo4j is not required to satisfy this spec.
- Named-graph union rules used by `merge-graphs` (see Merge rule below). This is a union of two graphs, not cross-corpus entity resolution.

**Out of scope**

- Running extraction on a repository (module `corpus-ingestion`).
- Query latency benchmarks (module `graph-search`).
- Episodes, time-travel, embedding entity resolution, MCP.
- Migrating `episodic ingest-node` in this spec.
- Adding edge types beyond the five above.

### Acceptance stories

- As search, I can ask for the outgoing edges of type `calls` from one node id and receive only those targets.
- As ingestion, I can write a node whose body lives outside the hot record and still attach a provenance pointer.
- As a reviewer, I can tell a structural neighbor query from a payload fetch.

## Tech Stack

- Python 3.11+
- Pydantic v2 for the contract models when implemented (not a current runtime dependency; adding it is an “ask first”)
- pytest for contract tests
- Shipped in-memory adjacency graph at `demo-graph/test-graph/`. No NetworkX requirement. Neo4j is out of this spec; see [05-storage-and-database-decision.md](./05-storage-and-database-decision.md) for the later indexed backend.

## Commands

These commands verify the repo. This module does not add a user-facing CLI.

```bash
pip install -e ".[dev]"
python -m pytest tests/unit/test_graph_model.py -q
python -m pytest
```

There is no project linter configured. Do not add one inside this module without asking.

## Project Structure

When implemented, keep the contract in one place:

```text
demo-graph/test-graph/adjacency.py → shipped in-memory adjacency graph (demo and tests)
demo-graph/test-graph/README.md    → how to load the demo graph
src/episodic/model/                → node, edge, and merge types (new)
tests/unit/test_graph_model.py     → loads demo-graph/test-graph/adjacency.py
.agent-resources/SPEC-graph-model.md
```

`demo-graph/test-graph/` is the graph that ships. Tests do not keep a second adjacency implementation under `tests/`. Load `adjacency.py` by file path (`importlib`), because the directory name contains hyphens and is not a Python package.

Existing prototype stays where it is until a later migration: `src/episodic/graph.py`, `src/episodic/ingest/markdown_node.py`.

## Code Style

Match the current package: `from __future__ import annotations`, stdlib `pathlib`, small functions, no payload classes that hide the id.

```python
def neighbors(
    graph: Graph,
    node_id: NodeId,
    *,
    edge_type: EdgeType | None = None,
    direction: Direction = "out",
) -> tuple[NodeId, ...]:
    """Return adjacent node ids. Does not load cold payloads."""
    ...
```

Conventions:

- Types and functions use `snake_case`. Models use `PascalCase`.
- Ids are strings (`NodeId`), opaque to callers except for stability tests.
- Edge types are only `contains`, `imports`, `calls`, `references`, and `describes`. Any other type raises `ValueError` at write time.
- Hot node fields are only: `id`, `type`, `label`, `provenance_ref`. Everything else is cold and fetched by id.

### Contract (normative)

**Node (hot)**

| Field | Required | Notes |
|---|---|---|
| `id` | yes | Stable for the same fingerprint across re-ingests |
| `type` | yes | Examples: `file`, `symbol`, `chunk`, `document`, `image` |
| `label` | yes | Short display string, not the source body |
| `provenance_ref` | yes | `{source_path, locator}` locator may be null if unknown |

**Edge**

| Field | Required | Notes |
|---|---|---|
| `id` | yes | Stable for the same `(source, target, type)` |
| `type` | yes | See closed set below |
| `source` | yes | Node id |
| `target` | yes | Node id |

**Edge types (locked):** `contains`, `imports`, `calls`, `references`, `describes`. An unknown label is rejected at write time. Do not collapse it into `references`. Adding a sixth type means editing this spec first.

**Merge rule:** `merge(into, source)` unions `source` into `into` by fingerprint for nodes and by `(source, target, type)` for edges.

- Identical hot records are a no-op.
- The same fingerprint with a different `label` or `type` does not overwrite `into`. Keep `into`’s hot fields, keep both provenance refs, and record a conflict on the node.
- Nodes and edges that exist only on `source` are copied onto `into`.
- `source` is not modified.

**Adjacency rule:** `neighbors` is answered from an index (adjacency lists or store indexes on `source`/`target` + `type`). A correct implementation never scans every edge in the graph to answer a one-node query.

**Cold payload rule:** file text, PDF bytes, image bytes, and long summaries are not fields on the hot node. A separate `get_payload(node_id)` reads them. `neighbors` must not call it.

**Identity rule:** fingerprint inputs are `(type, source_path, symbol_or_heading_or_span)`. Identity does not read graphify fields such as `qualified_name`. Document the hash function next to the code when implemented.

This is the boundary `corpus-ingestion` writes and `graph-search` reads. Temporal assertions in doc 02 wrap these records later; they do not replace these fields.

## Testing Strategy

- Framework: pytest. Tests live in `tests/unit/test_graph_model.py`.
- No coverage percentage gate in this repo. This module’s tests must cover the contract behaviors below, not a line quota.
- Level: unit tests against `demo-graph/test-graph/adjacency.py`. No Neo4j, no filesystem corpus, no graphify.

Required cases:

- Insert nodes and a typed edge; `neighbors` returns the target for that type and nothing else.
- Changing a cold payload does not change `neighbors` results.
- Re-adding the same fingerprint yields the same node id.
- A second edge type between the same pair is a different edge.
- `neighbors` on a missing id raises `KeyError`.
- Merge copies a node that exists only on the source graph, and a label mismatch records a conflict without changing the destination label.
- Depth is not this module’s job; do not implement search here.

## Boundaries

- **Always:** keep hot records free of source bodies; answer `neighbors` from the adjacency map in `demo-graph/test-graph/`; reject edge types outside the locked set; point ingestion and search at this spec instead of inventing a third JSON shape.
- **Ask first:** adding Pydantic or Neo4j to `pyproject.toml`; adding an edge type; changing fingerprint inputs; deleting or rewriting `src/episodic/graph.py`.
- **Never:** store PDF or image bytes on the hot node; scan all edges inside `neighbors`; commit secrets; weaken a failing contract test to make ingestion pass.

## Success Criteria

- [ ] The hot node and edge tables in this spec are the only structural fields ingestion is allowed to require.
- [ ] An in-memory graph answers typed `neighbors` for one node without reading cold payloads (asserted by a test that fails if payload I/O runs).
- [ ] The same fingerprint produces the same node id across two inserts in one process.
- [ ] A one-node neighbor query’s implementation does not iterate every edge (tested with a counter or by using an adjacency map only).
- [ ] Provenance is present on every node created by the test builder.
- [ ] `demo-graph/test-graph/adjacency.py` is the in-memory implementation imported by tests. There is no second copy under `tests/` or `src/episodic/model/`.
- [ ] Writing an edge whose type is not one of the five locked types raises `ValueError`.
- [ ] Merge of a conflicting label keeps the destination label and records a conflict.

## Open Questions

None for this module. Edge types, fingerprint inputs, the shipped path `demo-graph/test-graph/`, and “Neo4j is not required here” are decided.
