# Implementation Plan: graph-model

**PRD:** [2026-10-27-graph-model.md](../prds/2026-10-27-graph-model.md)  
**Spec:** [SPEC-graph-model.md](../SPEC-graph-model.md)  
**Task list:** [tasks/todo.md](../../tasks/todo.md) (same tasks as below)

## Overview

Ship the hot graph contract and one in-memory adjacency graph at `demo-graph/test-graph/adjacency.py`. Types live in `src/episodic/model/`. Tests load the adjacency module by file path. This plan does not build corpus ingest or search.

## Architecture Decisions

- **Stdlib records.** `@dataclass(frozen=True)` for `Provenance`, `HotNode`, `Edge`, and `MergeConflict`. Pydantic stays out until someone asks.
- **Ids.** Node id is `sha256("v1\0{type}\0{source_path}\0{symbol_or_heading_or_span}")` as hex. Edge id is `sha256("v1\0{source}\0{target}\0{type}")` as hex. Document both in `src/episodic/model/identity.py`.
- **Adjacency.** `outgoing[node_id][edge_type]` and `incoming[node_id][edge_type]` map to tuples of neighbor ids. `neighbors` uses one map lookup. It does not walk a flat edge list.
- **Neighbor order.** Returned ids are sorted by id so tests are stable.
- **Cold and conflicts are side maps.** `payloads`, `extra_provenance`, and `conflicts` sit on the graph object. They are not fields of `HotNode`. `get_payload` and `get_conflicts` read them. `neighbors` must not call those functions.
- **Merge conflicts.** Destination `label` and `type` stay. Destination `provenance_ref` stays. The source provenance is appended in `extra_provenance`. A `MergeConflict` records the field name and both values. The source graph object is not mutated.
- **Package name.** New code goes in `src/episodic/model/`. The empty `src/episodic/models/` package is left untouched.
- **Loader.** Tests and the demo README load `demo-graph/test-graph/adjacency.py` with `importlib.util.spec_from_file_location`. The hyphenated directory is not a Python package.

## Dependency Order

```text
identity + hot types
        │
        ▼
adjacency neighbors
        │
        ├── cold payload isolation
        │
        └── merge
```

Cold payload and merge both need neighbors, and they do not need each other. Implement payload first so merge tests can show that merge does not pull bodies into the hot node.

## Task List

### Phase 1: Contract

- [ ] Task 1: Fingerprint ids and locked edge types
- [ ] Task 2: Adjacency `neighbors`

### Checkpoint: Contract

- [ ] `python -m pytest tests/unit/test_graph_model.py -q` passes
- [ ] Unknown edge type raises `ValueError`
- [ ] Review with human before merge behavior

### Phase 2: Payload and merge

- [ ] Task 3: Cold payload stays off `neighbors`
- [ ] Task 4: Merge union and label conflicts

### Checkpoint: Complete

- [ ] `python -m pytest tests/unit/test_graph_model.py -q` passes
- [ ] `python -m pytest` passes
- [ ] Spec success criteria are checked off in the PRD sense (tests cover them)
- [ ] No edits to `src/episodic/graph.py` or `ingest-node`

## Risks and Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| A second adjacency helper appears under `src/` or `tests/` | Two contracts drift | Only `demo-graph/test-graph/adjacency.py` implements the maps. Types have no neighbor logic. |
| `neighbors` scans `edges` for convenience | Breaks the traversal rule | Test installs a map whose iteration raises |
| Merge overwrites the destination label | Breaks the locked conflict rule | Test asserts the destination label and a recorded conflict |
| Hyphenated path is imported as a package | Import error | `importlib` from the file path, documented in the README |

## Open Questions

None. Conflict detail lives in side maps so the hot node stays four fields.

## Parallelization

Tasks 3 and 4 touch the same `adjacency.py`. Do them in order. Do not split them across sessions that both edit that file.

---

## Task 1: Fingerprint ids and locked edge types

**Description:** Add frozen hot-record types and the documented fingerprint function. Reject edge types outside the locked set at construction time. No adjacency yet.

**Acceptance criteria:**

- [ ] `node_id(type, source_path, symbol)` is stable across two calls and is 64 hex characters
- [ ] A different symbol produces a different id
- [ ] Constructing an edge with type `mentions` raises `ValueError`
- [ ] Each of the five locked types constructs

**Verification:**

- [ ] Tests pass: `python -m pytest tests/unit/test_graph_model.py -q`
- [ ] Build succeeds: `pip install -e ".[dev]"` (types import without new dependencies)
- [ ] Manual check: `identity.py` docstring shows the `v1` byte layout

**Dependencies:** None

**Files likely touched:**

- `src/episodic/model/__init__.py`
- `src/episodic/model/types.py`
- `src/episodic/model/identity.py`
- `tests/unit/test_graph_model.py`

**Estimated scope:** Medium: 4 files

## Task 2: Adjacency neighbors

**Description:** Implement `MemoryGraph` in the shipped adjacency module. `add_node`, `add_edge`, and `neighbors` answer from the outgoing and incoming maps. Missing node id raises `KeyError`.

**Acceptance criteria:**

- [ ] An outgoing `calls` edge is returned for that type and omitted for `imports`
- [ ] A second edge type between the same pair is a different edge id
- [ ] Re-adding the same fingerprint returns the same node id and does not duplicate the node
- [ ] `neighbors` on an unknown id raises `KeyError`
- [ ] Tests load `demo-graph/test-graph/adjacency.py` by file path
- [ ] During `neighbors`, iterating the adjacency map raises if attempted (lookup by key only)

**Verification:**

- [ ] Tests pass: `python -m pytest tests/unit/test_graph_model.py -q`
- [ ] Build succeeds: `python -c "import episodic.model"`
- [ ] Manual check: `demo-graph/test-graph/README.md` shows the `importlib` load snippet

**Dependencies:** Task 1

**Files likely touched:**

- `demo-graph/test-graph/adjacency.py`
- `demo-graph/test-graph/README.md`
- `tests/unit/test_graph_model.py`

**Estimated scope:** Medium: 3 files

## Task 3: Cold payload stays off neighbors

**Description:** Store bodies in a side map. `get_payload` reads them. `neighbors` does not call `get_payload`. Changing a payload does not change neighbor ids.

**Acceptance criteria:**

- [ ] After `put_payload`, `neighbors` results are unchanged
- [ ] Hot node objects have no body field
- [ ] A test double fails if `neighbors` calls `get_payload`
- [ ] Provenance is present on every node the test builder inserts

**Verification:**

- [ ] Tests pass: `python -m pytest tests/unit/test_graph_model.py -q`
- [ ] Build succeeds: `python -m pytest tests/unit/test_graph_model.py -q`
- [ ] Manual check: `HotNode` fields are only `id`, `type`, `label`, `provenance_ref`

**Dependencies:** Task 2

**Files likely touched:**

- `demo-graph/test-graph/adjacency.py`
- `tests/unit/test_graph_model.py`

**Estimated scope:** Small: 2 files

## Task 4: Merge union and label conflicts

**Description:** `merge(into, source)` unions nodes by fingerprint and edges by endpoints plus type. Identical hot records are a no-op. A label or type mismatch keeps the destination hot fields, appends source provenance, and records a conflict. `source` is unchanged.

**Acceptance criteria:**

- [ ] A node that exists only on `source` appears on `into`
- [ ] An edge that exists only on `source` appears on `into`
- [ ] A label mismatch leaves `into`'s label in place and `get_conflicts` returns that clash
- [ ] Both provenance refs are readable after the clash
- [ ] `source` node count and labels are unchanged after merge

**Verification:**

- [ ] Tests pass: `python -m pytest tests/unit/test_graph_model.py -q`
- [ ] Build succeeds: `python -m pytest`
- [ ] Manual check: `src/episodic/graph.py` has no diff from this work

**Dependencies:** Task 3

**Files likely touched:**

- `demo-graph/test-graph/adjacency.py`
- `src/episodic/model/types.py`
- `tests/unit/test_graph_model.py`

**Estimated scope:** Medium: 3 files
