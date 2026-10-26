# PRD — Graph Model

**Status:** Ready to build (2026-10-27)  
**Module id:** `graph-model`  
**Slice:** In-memory hot graph only. No ingest, no search, no Neo4j.  
**Parents:** [SPEC-graph-model.md](../SPEC-graph-model.md), [capability-map-initial-graph.md](../capability-map-initial-graph.md)  
**Plan:** [2026-10-27-graph-model.md](../plans/2026-10-27-graph-model.md)

---

## Problem

Callers need to walk a context graph by node id and edge type without loading file bytes and without scanning every edge. The prototype graph stores Markdown bodies on the node. This slice freezes the hot contract and ships one in-memory adjacency graph that meets it.

---

## Locked Decisions

| # | Topic | Decision |
|---|---|---|
| 1 | Edge types | `contains`, `imports`, `calls`, `references`, `describes`. Anything else raises `ValueError`. |
| 2 | Where the graph ships | `demo-graph/test-graph/adjacency.py`. Tests load that file. No second adjacency implementation. |
| 3 | Identity | SHA-256 of `v1`, node type, source path, and symbol or heading or span. Graphify fields are not inputs. |
| 4 | Hot vs cold | Hot node is `id`, `type`, `label`, `provenance_ref`. Bodies and merge conflict detail are side maps. `neighbors` does not read them. |
| 5 | Merge | Union by fingerprint and by `(source, target, type)`. Same fingerprint with a different label or type keeps the destination hot fields, keeps both provenance refs, and records a conflict. Source graph is unchanged. |
| 6 | Dependencies | Python 3.11 stdlib only. No Pydantic, Neo4j, or NetworkX. |
| 7 | Prototype CLI | `src/episodic/graph.py` and `episodic ingest-node` stay as they are. |

---

## Goals

1. A caller can insert a hot node and a typed edge and read only the neighbor ids for that edge type.
2. The same fingerprint always yields the same node id.
3. A cold payload change does not change neighbor results, and neighbor lookup does not read payloads.
4. Merge copies source-only nodes and edges, and a label clash does not overwrite the destination label.

---

## Non-Goals

- Folder ingest, organizers, and `merge-graphs` CLI (`corpus-ingestion`)
- Bounded search and latency benchmarks (`graph-search`)
- Episodes, time-travel, entity resolution, MCP
- Migrating the Markdown prototype CLI
- A sixth edge type

---

## User Stories

| As a… | I want to… | So that… |
|---|---|---|
| Search | ask for outgoing `calls` from one id | I receive only those target ids |
| Ingestion | store a body off the hot node and still set provenance | traversal stays small |
| Reviewer | see that `neighbors` never reads payloads | structural queries stay separate from file bytes |

---

## Success Criteria

The checklist in [SPEC-graph-model.md](../SPEC-graph-model.md) under Success Criteria, verified by:

```bash
pip install -e ".[dev]"
python -m pytest tests/unit/test_graph_model.py -q
```

No new CLI command.
