# Tasks: graph-model

Plan: [.agent-resources/plans/2026-10-27-graph-model.md](../.agent-resources/plans/2026-10-27-graph-model.md)  
PRD: [.agent-resources/prds/2026-10-27-graph-model.md](../.agent-resources/prds/2026-10-27-graph-model.md)

## Task 1: Fingerprint ids and locked edge types

**Description:** Add frozen hot-record types and the documented fingerprint function. Reject edge types outside the locked set at construction time. No adjacency yet.

**Acceptance criteria:**

- [ ] `node_id(type, source_path, symbol)` is stable across two calls and is 64 hex characters
- [ ] A different symbol produces a different id
- [ ] Constructing an edge with type `mentions` raises `ValueError`
- [ ] Each of the five locked types constructs

**Verification:**

- [ ] Tests pass: `python -m pytest tests/unit/test_graph_model.py -q`
- [ ] Build succeeds: `pip install -e ".[dev]"`
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

## Checkpoint: After Tasks 1-2

- [ ] `python -m pytest tests/unit/test_graph_model.py -q` passes
- [ ] Unknown edge type raises `ValueError`
- [ ] Review with human before merge behavior

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

## Checkpoint: Complete

- [ ] `python -m pytest` passes
- [ ] Spec success criteria are covered by tests
- [ ] No edits to `src/episodic/graph.py` or `ingest-node`
