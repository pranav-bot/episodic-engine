# Implementation Plan: graph-model

Canonical copy: [.agent-resources/plans/2026-10-27-graph-model.md](../.agent-resources/plans/2026-10-27-graph-model.md)

This file exists so the default plan path matches the task list in [todo.md](./todo.md). Edit the canonical plan first, then keep this summary in sync.

## Overview

Ship the hot graph contract and one in-memory adjacency graph at `demo-graph/test-graph/adjacency.py`. Types live in `src/episodic/model/`. No corpus ingest, no search, no Neo4j, no Pydantic.

## Architecture Decisions

- Frozen stdlib dataclasses for hot records
- SHA-256 fingerprint `v1` + type + source path + symbol or span
- Adjacency maps keyed by node id and edge type
- Payloads and merge conflicts in side maps, not on the hot node
- Load the hyphenated demo path with `importlib`

## Task List

### Phase 1: Contract

- [ ] Task 1: Fingerprint ids and locked edge types
- [ ] Task 2: Adjacency `neighbors`

### Checkpoint: Contract

- [ ] `python -m pytest tests/unit/test_graph_model.py -q` passes
- [ ] Review before merge behavior

### Phase 2: Payload and merge

- [ ] Task 3: Cold payload stays off `neighbors`
- [ ] Task 4: Merge union and label conflicts

### Checkpoint: Complete

- [ ] `python -m pytest` passes
- [ ] Spec success criteria covered by tests
- [ ] No edits to `src/episodic/graph.py` or `ingest-node`

## Risks and Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Second adjacency implementation | Contract drift | Only `demo-graph/test-graph/adjacency.py` |
| Full edge scan inside `neighbors` | Traversal rule broken | Test map iteration raises |
| Merge overwrites destination label | Conflict rule broken | Assert label and recorded conflict |

## Open Questions

None.
