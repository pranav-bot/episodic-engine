# 06 — Time-Travel Queries

## Concept

Time-travel retrieves the **materialized graph state** as it was known at a specific point in time. This is not replaying raw graphify snapshots alone — it is applying the **assertion validity model** from [02-temporal-schema-design.md](./02-temporal-schema-design.md).

Two timestamps matter:

| Timestamp | Meaning |
|-----------|---------|
| `recorded_at` | When Episodic Engine ingested the episode (ordering) |
| `valid_from` / `valid_to` | When the assertion was considered true in the source world |

Default `as_of` queries filter on **`valid_from <= as_of AND (valid_to IS NULL OR valid_to > as_of)`**.

---

## Query Modes

| Mode                 | Parameter                      | Use Case                               |
| -------------------- | ------------------------------ | -------------------------------------- |
| **Point-in-time**    | `--as-of 2026-07-01T18:00:00Z` | "What did we know last Tuesday?"       |
| **Episode-boundary** | `--at-episode myrepo-code__ep_000042` | Exact reproducibility / debugging      |
| **Commit-boundary**  | `--at-commit abc123`           | Align with git history                 |
| **Range**            | `--from ... --to ...`          | "How did auth edges change this week?" |

---

## Example 1: Cypher — Active Nodes at a Point in Time

Assumes domain relationships carry temporal properties (`valid_from`, `valid_to`).

```cypher
// All canonical nodes with at least one active assertion at as_of
WITH datetime("2026-07-01T18:00:00+05:30") AS as_of

MATCH (n:CanonicalNode)-[a:HAS_ASSERTION]->(assertion:NodeAssertion)
WHERE assertion.valid_from <= as_of
  AND (assertion.valid_to IS NULL OR assertion.valid_to > as_of)

RETURN DISTINCT n.global_id, n.canonical_label, n.entity_type,
       assertion.properties AS props
ORDER BY n.canonical_label
```

---

## Example 2: Cypher — Active Edges (Auth Neighborhood) at as_of

```cypher
WITH datetime("2026-07-01T18:00:00+05:30") AS as_of

MATCH (src:CanonicalNode)
WHERE "module:src/auth.py:auth" IN src.fingerprints
MATCH (src)-[r:CALLS|IMPORTS|DOCUMENTS*1..3]-(tgt:CanonicalNode)
WHERE ALL(rel IN relationships(r) WHERE
  rel.valid_from <= as_of AND
  (rel.valid_to IS NULL OR rel.valid_to > as_of)
)
RETURN src, r, tgt
```

---

## Example 3: Cypher — Shortest Path as of Last Tuesday

Natural language: *"How were User Auth and authenticate_user connected last Tuesday?"*

```cypher
WITH datetime("2026-06-30T00:00:00+05:30") AS as_of

MATCH (a:CanonicalNode)
WHERE a.canonical_label CONTAINS "User Auth"
MATCH (b:CanonicalNode)
WHERE "function:src/auth.py:authenticate_user" IN b.fingerprints

CALL apoc.algo.dijkstra(a, b, 'CALLS>|IMPORTS>|DOCUMENTS>|IMPLEMENTS>', 'weight', as_of)
YIELD path, weight

// Filter path rels by validity (if not using apoc temporal extension)
RETURN path, weight
LIMIT 5
```

> **Note:** If APOC temporal helpers aren't available, pre-filter relationships in application layer or use the materializer (Example 5).

---

## Example 4: SQL — Episodes Between Two Dates

"What changed in the auth subgraph between June 1 and July 1?"

```sql
SELECT e.episode_id,
       e.recorded_at,
       e.subgraph_id,
       e.trigger_type,
       json_array_length(e.operations_json) AS op_count
FROM episodes e
WHERE e.subgraph_id = 'myrepo-code'
  AND e.recorded_at >= '2026-06-01T00:00:00Z'
  AND e.recorded_at <  '2026-07-01T00:00:00Z'
  AND EXISTS (
    SELECT 1 FROM json_each(e.operations_json) op
    WHERE json_extract(op.value, '$.local_ref.fingerprint') LIKE '%auth%'
       OR json_extract(op.value, '$.properties.label') LIKE '%auth%'
       OR json_extract(op.value, '$.fingerprint') LIKE '%auth%'
  )
ORDER BY e.recorded_at;
```

---

## Example 5: Python-Style Materializer (Planning Pseudocode)

> Planning pseudocode — describes the replay algorithm, not production code.

```
function materialize_graph(as_of: datetime, scope: subgraph | supergraph, subgraph_id=None):

    # Start from empty or latest checkpoint before as_of
    checkpoint = episode_log.find_checkpoint_before(as_of)
    graph = load_checkpoint(checkpoint) if checkpoint else empty_graph()

    start_episode = checkpoint.next_episode if checkpoint else first_episode

    for episode in episode_log.range(start_episode, up_to=as_of):
        if scope == subgraph and episode.subgraph_id != subgraph_id:
            continue
        for op in episode.operations:
            apply_op(graph, op, clip_validity_at=as_of)

    # Clip any assertion still open but started after as_of
    graph.retain_assertions_where(
        valid_from <= as_of AND (valid_to IS NULL OR valid_to > as_of)
    )

    return graph
```

### Op Application Rules at as_of

| Operation | Effect on Materialized View |
|-----------|----------------------------|
| `ASSERT_NODE` | Add node if `valid_from <= as_of` |
| `RETRACT_NODE` | Exclude if `valid_to <= as_of` |
| `UPDATE_NODE` | Use assertion active at as_of |
| `MERGE_ENTITIES` | Apply if episode `recorded_at <= as_of` |
| `RESOLVE_CROSS_LINK` | Include edge if assertion active at as_of |

---

## Example 6: CLI — User-Facing Time Travel

```bash
# Natural language time reference (parsed by router)
episodic query "What did the docs say about auth last Tuesday?" \
  --scope subgraph --subgraph product-docs

# Explicit timestamp
episodic query "auth implementation" \
  --scope supergraph \
  --as-of "2026-07-01T18:00:00+05:30"

# At git commit (maps commit timestamp → nearest episode)
episodic query "show auth module" \
  --subgraph myrepo-code \
  --at-commit abc123def

# Diff two points in time
episodic diff \
  --subgraph myrepo-code \
  --from "2026-06-01" \
  --to "2026-07-01" \
  --focus "auth"
```

---

## Example 7: Temporal Diff Output

```json
{
  "from": "2026-06-01T00:00:00Z",
  "to": "2026-07-01T00:00:00Z",
  "subgraph_id": "myrepo-code",
  "nodes_added": [
    {"global_id": "gn_jwt_refresh", "label": "refresh_token", "type": "function"}
  ],
  "nodes_removed": [
    {"global_id": "gn_session_cookie", "label": "set_session_cookie", "type": "function"}
  ],
  "edges_changed": [
    {
      "type": "CALLS",
      "from": "authenticate_user",
      "to": "issue_jwt",
      "change": "added",
      "episode_id": "myrepo-code__ep_000038"
    }
  ],
  "resolution_changes": [
    {
      "merge": "gn_auth_spec → gn_auth",
      "status": "confirmed",
      "episode_id": "myrepo-code__ep_000031"
    }
  ]
}
```

---

## Performance: Avoid Full Replay Every Query

| Technique | Description |
|-----------|-------------|
| **Checkpoints** | Materialize Neo4j state every N episodes; replay only delta since checkpoint |
| **Temporal index** | Index `(valid_from, valid_to)` on assertion records |
| **Snapshot shortcut** | If `as_of` matches exact snapshot timestamp, serve raw subgraph blob |
| **Cached views** | LRU cache keyed by `(as_of_rounded, scope, subgraph_id)` |

For "last Tuesday" queries, round `as_of` to episode boundary (nearest prior episode `recorded_at`) — LLMs rarely need sub-episode precision.

---

## Semantic vs Record Time

| Question | Use |
|----------|-----|
| "What did we know when we shipped v1.2?" | `valid_from/valid_to` aligned to release tag |
| "What had been ingested by standup Tuesday?" | `recorded_at <= Tuesday standup` |
| "What did the code look like at commit X?" | Map commit timestamp → `valid_from` on code subgraph |

Expose both modes in API: `--as-of-semantic` vs `--as-of-recorded` (default: semantic).

---

## LLM Context Annotation

When serving time-traveled context, always include:

```json
{
  "temporal_context": {
    "as_of": "2026-07-01T18:00:00+05:30",
    "mode": "semantic",
    "latest_episode_included": "myrepo-code__ep_000041",
    "staleness_warning": null
  }
}
```

Prevents the LLM from presenting historical state as current.
