# Phase 1 — Hybrid-Local Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the Phase 1 Episodic Engine core loop — ingest graphify `graph.json` subgraphs, emit delta episodes, resolve entities (Tier 1), project to Neo4j, and query via CLI with basic time-travel — using the hybrid-local profile (SQLite + local blobs + Neo4j + graphify delegation).

**Architecture:** Pluggable StoragePorts with local drivers; cold blob snapshots; warm SQLite episode log; hot Neo4j supergraph projection + optional NetworkX subgraph cache; graphify subprocess for subgraph queries. See [09-hybrid-architecture.md](../09-hybrid-architecture.md).

**Tech Stack:** Python 3.11+, pydantic v2, typer (CLI), neo4j Python driver, networkx, sqlite3 (stdlib), pytest, graphify (`graphifyy` on PyPI)

**Design refs:** [02-temporal-schema-design.md](../02-temporal-schema-design.md), [03-entity-resolution.md](../03-entity-resolution.md), [08-graphify-integration.md](../08-graphify-integration.md)

---

## Target File Structure

```
episodic-engine/
├── pyproject.toml
├── docker-compose.yml              # Neo4j for dev
├── config.example.yaml
├── src/episodic/
│   ├── __init__.py
│   ├── config.py                   # Load hybrid-local config
│   ├── ports/
│   │   ├── __init__.py
│   │   ├── episode_store.py        # Protocol: EpisodeStorePort
│   │   ├── blob_store.py           # Protocol: BlobStorePort
│   │   ├── supergraph_store.py     # Protocol: SupergraphStorePort
│   │   └── subgraph_cache.py       # Protocol: SubgraphCachePort
│   ├── drivers/
│   │   ├── sqlite_episode_store.py
│   │   ├── local_blob_store.py
│   │   ├── neo4j_supergraph.py
│   │   └── networkx_subgraph_cache.py
│   ├── models/
│   │   ├── episode.py              # Episode, EpisodeStats
│   │   ├── operations.py           # OpType enum + op models
│   │   ├── canonical.py            # CanonicalNode, NodeAssertion
│   │   └── subgraph.py             # SubgraphRegistration, SnapshotMeta
│   ├── ingest/
│   │   ├── graphify_adapter.py     # Parse graph.json → internal nodes/edges
│   │   ├── fingerprint.py          # Tier 1 fingerprint computation
│   │   ├── differ.py               # Snapshot diff → operations
│   │   └── pipeline.py             # Orchestrate ingest end-to-end
│   ├── resolution/
│   │   └── tier1.py                # Fingerprint lookup + alias mapping
│   ├── projection/
│   │   └── applier.py              # Apply episode ops to Neo4j
│   ├── materializer.py             # Replay episodes → NetworkX view
│   ├── graphify_delegate.py        # Subprocess wrapper for graphify query
│   └── cli/
│       └── main.py                 # typer CLI entry point
└── tests/
    ├── conftest.py
    ├── fixtures/
    │   ├── graph_v1.json
    │   └── graph_v2.json
    ├── unit/
    │   ├── test_fingerprint.py
    │   ├── test_differ.py
    │   ├── test_tier1_resolution.py
    │   └── test_materializer.py
    ├── integration/
    │   ├── test_sqlite_episode_store.py
    │   ├── test_local_blob_store.py
    │   ├── test_ingest_pipeline.py
    │   └── test_neo4j_projection.py
    └── e2e/
        └── test_cli_smoke.py
```

---

## Prerequisites (Human Setup)

- [ ] Install graphify: `uv tool install graphifyy`
- [ ] Docker available for Neo4j
- [ ] Python 3.11+ with `uv` or `pip`

---

### Task 1: Project Scaffold

**Files:**
- Create: `pyproject.toml`
- Create: `src/episodic/__init__.py`
- Create: `docker-compose.yml`
- Create: `config.example.yaml`

- [ ] **Step 1: Create pyproject.toml**

```toml
[project]
name = "episodic-engine"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "pydantic>=2.0",
    "typer>=0.12",
    "neo4j>=5.0",
    "networkx>=3.0",
    "pyyaml>=6.0",
]

[project.optional-dependencies]
dev = ["pytest>=8.0", "pytest-asyncio>=0.23"]

[project.scripts]
episodic = "episodic.cli.main:app"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/episodic"]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src"]
```

- [ ] **Step 2: Create docker-compose.yml for Neo4j**

```yaml
services:
  neo4j:
    image: neo4j:5-community
    ports:
      - "7474:7474"
      - "7687:7687"
    environment:
      NEO4J_AUTH: neo4j/episodic-dev
    volumes:
      - neo4j_data:/data

volumes:
  neo4j_data:
```

- [ ] **Step 3: Create config.example.yaml**

```yaml
deployment: hybrid-local

storage:
  episode_log:
    driver: sqlite
    path: ~/.episodic-engine/episodes.db
  snapshots:
    driver: local
    path: ~/.episodic-engine/snapshots/
  supergraph:
    driver: neo4j
    uri: bolt://localhost:7687
    user: neo4j
    password: episodic-dev
  subgraph_cache:
    enabled: true
    max_subgraphs: 5

graphify:
  binary: graphify
  delegate_subgraph_queries: true
```

- [ ] **Step 4: Install package in editable mode**

Run: `cd /home/padvani/dev/episodic-engine && pip install -e ".[dev]"`
Expected: Successful install

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml docker-compose.yml config.example.yaml src/episodic/__init__.py
git commit -m "chore: scaffold episodic-engine project"
```

---

### Task 2: Domain Models (Episode + Operations)

**Files:**
- Create: `src/episodic/models/operations.py`
- Create: `src/episodic/models/episode.py`
- Create: `src/episodic/models/subgraph.py`
- Create: `src/episodic/models/canonical.py`
- Test: `tests/unit/test_operations.py`

- [ ] **Step 1: Write failing test for operation serialization**

```python
# tests/unit/test_operations.py
from episodic.models.operations import AssertNodeOp, OpType
from episodic.models.episode import Episode


def test_assert_node_op_roundtrip():
    op = AssertNodeOp(
        op=OpType.ASSERT_NODE,
        global_id="gn_abc",
        local_ref={
            "subgraph_id": "myrepo-code",
            "local_id": "node_1",
            "fingerprint": "function:src/auth.py:authenticate_user",
        },
        properties={"label": "authenticate_user", "type": "function"},
        confidence=1.0,
    )
    episode = Episode(
        episode_id="ep_000001",
        sequence=1,
        recorded_at="2026-07-06T12:00:00Z",
        subgraph_id="myrepo-code",
        snapshot={"hash": "sha256:abc", "node_count": 1, "edge_count": 0},
        trigger={"type": "graphify_regen"},
        operations=[op],
    )
    data = episode.model_dump(mode="json")
    assert data["operations"][0]["op"] == "ASSERT_NODE"
    assert data["operations"][0]["local_ref"]["fingerprint"] == "function:src/auth.py:authenticate_user"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_operations.py -v`
Expected: FAIL — module not found

- [ ] **Step 3: Implement operations.py and episode.py**

`src/episodic/models/operations.py` — define `OpType` enum with all 8 op types from [02-temporal-schema-design.md](../02-temporal-schema-design.md): `ASSERT_NODE`, `UPDATE_NODE`, `RETRACT_NODE`, `ASSERT_EDGE`, `RETRACT_EDGE`, `MERGE_ENTITIES`, `SPLIT_ENTITY`, `RESOLVE_CROSS_LINK`. Use pydantic discriminated union on `op` field.

`src/episodic/models/episode.py` — `Episode`, `EpisodeStats`, `SnapshotMeta` pydantic models matching the JSON schema in doc 02.

`src/episodic/models/subgraph.py` — `SubgraphRegistration(subgraph_id, source_path, graphify_out_path, registered_at)`.

`src/episodic/models/canonical.py` — `CanonicalNode`, `LocalAlias`, `NodeAssertion` with `valid_from`, `valid_to`.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_operations.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/episodic/models/ tests/unit/test_operations.py
git commit -m "feat: add episode and operation domain models"
```

---

### Task 3: StoragePort Protocols

**Files:**
- Create: `src/episodic/ports/episode_store.py`
- Create: `src/episodic/ports/blob_store.py`
- Create: `src/episodic/ports/supergraph_store.py`
- Create: `src/episodic/ports/subgraph_cache.py`
- Create: `src/episodic/config.py`

- [ ] **Step 1: Define EpisodeStorePort protocol**

```python
# src/episodic/ports/episode_store.py
from typing import Protocol, Iterator
from episodic.models.episode import Episode
from episodic.models.subgraph import SubgraphRegistration


class EpisodeStorePort(Protocol):
    def register_subgraph(self, reg: SubgraphRegistration) -> None: ...
    def get_subgraph(self, subgraph_id: str) -> SubgraphRegistration | None: ...
    def list_subgraphs(self) -> list[SubgraphRegistration]: ...
    def append_episode(self, episode: Episode) -> None: ...
    def get_episode(self, episode_id: str) -> Episode | None: ...
    def latest_episode(self, subgraph_id: str) -> Episode | None: ...
    def episodes_range(
        self, subgraph_id: str | None, up_to_sequence: int | None
    ) -> Iterator[Episode]: ...
    def save_alias(self, subgraph_id: str, snapshot_hash: str, local_id: str, global_id: str) -> None: ...
    def resolve_alias(self, subgraph_id: str, snapshot_hash: str, local_id: str) -> str | None: ...
    def find_by_fingerprint(self, fingerprint: str) -> str | None: ...
    def save_fingerprint(self, global_id: str, fingerprint: str) -> None: ...
```

- [ ] **Step 2: Define BlobStorePort, SupergraphStorePort, SubgraphCachePort**

`BlobStorePort`: `put(hash, bytes) -> str`, `get(hash) -> bytes`, `exists(hash) -> bool`

`SupergraphStorePort`: `apply_episode(episode)`, `get_node(global_id)`, `find_by_fingerprint(fp)`, `shortest_path(src, tgt, as_of=None)`, `active_nodes(as_of=None)`

`SubgraphCachePort`: `load(subgraph_id, graph_json)`, `get(subgraph_id)`, `invalidate(subgraph_id)`

- [ ] **Step 3: Implement config.py**

Load `config.yaml` from `EPISODIC_CONFIG` env or `~/.episodic-engine/config.yaml`; pydantic settings model matching `config.example.yaml`.

- [ ] **Step 4: Commit**

```bash
git add src/episodic/ports/ src/episodic/config.py
git commit -m "feat: define StoragePort protocols and config loader"
```

---

### Task 4: SQLite Episode Store Driver

**Files:**
- Create: `src/episodic/drivers/sqlite_episode_store.py`
- Test: `tests/integration/test_sqlite_episode_store.py`

- [ ] **Step 1: Write failing integration test**

```python
# tests/integration/test_sqlite_episode_store.py
import tempfile
from episodic.drivers.sqlite_episode_store import SQLiteEpisodeStore
from episodic.models.episode import Episode
from episodic.models.subgraph import SubgraphRegistration


def test_append_and_retrieve_episode():
    with tempfile.TemporaryDirectory() as tmp:
        db_path = f"{tmp}/test.db"
        store = SQLiteEpisodeStore(db_path)
        store.register_subgraph(SubgraphRegistration(
            subgraph_id="test-repo",
            source_path="/tmp/repo",
            graphify_out_path="/tmp/repo/graphify-out",
            registered_at="2026-07-06T00:00:00Z",
        ))
        ep = Episode(
            episode_id="ep_000001",
            sequence=1,
            recorded_at="2026-07-06T12:00:00Z",
            subgraph_id="test-repo",
            snapshot={"hash": "sha256:abc", "node_count": 10, "edge_count": 20},
            trigger={"type": "graphify_regen"},
            operations=[],
        )
        store.append_episode(ep)
        loaded = store.get_episode("ep_000001")
        assert loaded is not None
        assert loaded.subgraph_id == "test-repo"
        assert store.latest_episode("test-repo").episode_id == "ep_000001"
```

- [ ] **Step 2: Run test — expect FAIL**

Run: `pytest tests/integration/test_sqlite_episode_store.py -v`

- [ ] **Step 3: Implement SQLiteEpisodeStore**

Schema tables (create on init):
- `subgraphs(subgraph_id, source_path, graphify_out_path, registered_at)`
- `episodes(episode_id, sequence, recorded_at, subgraph_id, snapshot_json, trigger_json, operations_json, parent_episode_id)`
- `fingerprints(fingerprint, global_id)` — unique on fingerprint
- `local_aliases(subgraph_id, snapshot_hash, local_id, global_id)` — composite PK

Use `json.dumps` for operations list. Auto-increment `sequence` per subgraph via `MAX(sequence)+1`.

- [ ] **Step 4: Run test — expect PASS**

- [ ] **Step 5: Commit**

```bash
git add src/episodic/drivers/sqlite_episode_store.py tests/integration/test_sqlite_episode_store.py
git commit -m "feat: add SQLite episode store driver"
```

---

### Task 5: Local Blob Store Driver

**Files:**
- Create: `src/episodic/drivers/local_blob_store.py`
- Test: `tests/integration/test_local_blob_store.py`

- [ ] **Step 1: Write failing test**

```python
def test_put_get_content_addressed():
    with tempfile.TemporaryDirectory() as tmp:
        store = LocalBlobStore(tmp)
        content = b'{"nodes": [], "links": []}'
        hash_key = store.put(content)
        assert hash_key.startswith("sha256:")
        assert store.get(hash_key) == content
        assert store.exists(hash_key)
```

- [ ] **Step 2–4: Implement, verify, commit**

`LocalBlobStore`: SHA-256 hash content; store at `{base}/{hash[7:9]}/{hash}.json` (sharded); return `sha256:{hex}`.

---

### Task 6: Graphify Adapter + Fingerprints

**Files:**
- Create: `src/episodic/ingest/graphify_adapter.py`
- Create: `src/episodic/ingest/fingerprint.py`
- Create: `tests/fixtures/graph_v1.json`
- Create: `tests/fixtures/graph_v2.json`
- Test: `tests/unit/test_fingerprint.py`

- [ ] **Step 1: Create minimal graph fixtures**

Two fixture files mimicking NetworkX `node_link_data` format with auth-related nodes. `graph_v2.json` = v1 with one function removed and one added.

- [ ] **Step 2: Write fingerprint test**

```python
def test_fingerprint_code_function():
    node = {"id": "n1", "label": "authenticate_user", "type": "function",
            "file": "src/auth.py", "qualified_name": "authenticate_user"}
    assert compute_fingerprint(node) == "function:src/auth.py:authenticate_user"
```

- [ ] **Step 3: Implement graphify_adapter.py**

Parse `graph.json` — handle both `links` and `edges` keys (NetworkX compat). Return `list[GraphNode]`, `list[GraphEdge]` dataclasses with normalized fields.

- [ ] **Step 4: Implement fingerprint.py**

Per [03-entity-resolution.md](../03-entity-resolution.md):
- Code: `{type}:{file_path}:{qualified_name}`
- Doc/concept: `{type}:{file_path}:{heading_slug}`
- Fallback: `{type}:{normalized_label}:{file_path or 'unknown'}`

- [ ] **Step 5: Run tests, commit**

---

### Task 7: Snapshot Differ

**Files:**
- Create: `src/episodic/ingest/differ.py`
- Test: `tests/unit/test_differ.py`

- [ ] **Step 1: Write failing diff test**

```python
def test_diff_detects_added_and_removed_nodes():
    old = load_fixture("graph_v1.json")
    new = load_fixture("graph_v2.json")
    ops = diff_snapshots(old, new, subgraph_id="test", recorded_at="2026-07-06T12:00:00Z")
    op_types = [op.op for op in ops]
    assert "ASSERT_NODE" in op_types
    assert "RETRACT_NODE" in op_types
```

- [ ] **Step 2: Implement differ.py**

Algorithm:
1. Index old nodes by fingerprint
2. Index new nodes by fingerprint
3. Fingerprints in new not in old → `ASSERT_NODE` (assign new `global_id` via uuid4)
4. Fingerprints in old not in new → `RETRACT_NODE`
5. Same fingerprint, changed properties → `UPDATE_NODE`
6. Same for edges keyed by `(src_fp, tgt_fp, edge_type)`
7. Return empty list if identical (idempotency)

- [ ] **Step 3: Verify idempotency test**

```python
def test_identical_snapshots_produce_no_ops():
    g = load_fixture("graph_v1.json")
    ops = diff_snapshots(g, g, subgraph_id="test", recorded_at="2026-07-06T12:00:00Z")
    assert ops == []
```

- [ ] **Step 4: Commit**

---

### Task 8: Tier 1 Entity Resolution

**Files:**
- Create: `src/episodic/resolution/tier1.py`
- Test: `tests/unit/test_tier1_resolution.py`

- [ ] **Step 1: Write failing test for fingerprint match**

```python
def test_tier1_reuses_existing_global_id(store):
    store.save_fingerprint("gn_existing", "module:src/auth.py")
    op = AssertNodeOp(..., local_ref={..., "fingerprint": "module:src/auth.py"})
    resolved = tier1_resolve_node(op, store)
    assert resolved.global_id == "gn_existing"
```

- [ ] **Step 2: Implement tier1.py**

For each `ASSERT_NODE` op:
1. Lookup fingerprint in episode store
2. If found → reuse `global_id`, emit alias mapping (no new canonical node)
3. If not found → keep assigned `global_id`, save fingerprint

Cross-link rules (Phase 1, rule-based only):
- Doc wikilink target matching file path → emit `RESOLVE_CROSS_LINK` with `DOCUMENTS`
- `test_*.py` → corresponding module path → `TESTS` edge

- [ ] **Step 3: Run tests, commit**

---

### Task 9: Neo4j Supergraph Driver

**Files:**
- Create: `src/episodic/drivers/neo4j_supergraph.py`
- Create: `src/episodic/projection/applier.py`
- Test: `tests/integration/test_neo4j_projection.py`

- [ ] **Step 1: Start Neo4j**

Run: `docker compose up -d`
Expected: Neo4j available at bolt://localhost:7687

- [ ] **Step 2: Write failing integration test (mark with `@pytest.mark.neo4j`)**

```python
@pytest.mark.neo4j
def test_apply_assert_node(neo4j_store):
    op = AssertNodeOp(
        op=OpType.ASSERT_NODE,
        global_id="gn_test",
        properties={"label": "auth", "type": "module"},
        confidence=1.0,
        local_ref={"subgraph_id": "t", "local_id": "n1", "fingerprint": "module:src/auth.py"},
    )
    episode = make_episode(operations=[op])
    neo4j_store.apply_episode(episode)
    node = neo4j_store.get_node("gn_test")
    assert node["canonical_label"] == "auth"
```

- [ ] **Step 3: Implement neo4j_supergraph.py**

Cypher on init (constraints):
```cypher
CREATE CONSTRAINT canonical_node_id IF NOT EXISTS FOR (n:CanonicalNode) REQUIRE n.global_id IS UNIQUE;
CREATE CONSTRAINT fingerprint IF NOT EXISTS FOR (n:CanonicalNode) REQUIRE n.primary_fingerprint IS UNIQUE;
```

`apply_episode`: for each op type, run appropriate Cypher:
- `ASSERT_NODE`: `MERGE (n:CanonicalNode {global_id: $gid}) SET ...` + create assertion properties with `valid_from`, `valid_to: null`
- `RETRACT_NODE/EDGE`: `SET valid_to = $timestamp` on active relationships
- `ASSERT_EDGE`: `MATCH (a), (b) MERGE (a)-[r:REL {type: $type}]->(b) SET r.valid_from = ...`
- `RESOLVE_CROSS_LINK`: `MERGE (a)-[r:DOCUMENTS|IMPLEMENTS|TESTS]->(b) SET r.origin = 'entity_resolution'`

- [ ] **Step 4: Run integration test, commit**

---

### Task 10: Ingest Pipeline

**Files:**
- Create: `src/episodic/ingest/pipeline.py`
- Test: `tests/integration/test_ingest_pipeline.py`

- [ ] **Step 1: Write failing end-to-end ingest test**

```python
def test_ingest_two_snapshots_creates_two_episodes(tmp_paths, stores):
    # Register subgraph, ingest v1, ingest v2
    pipeline.ingest("test-repo", graph_json_path=v1_path)
    pipeline.ingest("test-repo", graph_json_path=v2_path)
    ep1 = store.latest_episode("test-repo")  # after v1
    # ... verify sequence increments, v2 has ops, v1 unchanged
    identical = pipeline.ingest("test-repo", graph_json_path=v2_path)  # re-ingest same
    assert identical.skipped  # zero ops, no new episode
```

- [ ] **Step 2: Implement pipeline.py**

`IngestPipeline.ingest(subgraph_id, graph_json_path)`:
1. Read graph.json bytes → blob store.put → hash
2. If hash == latest snapshot hash → return early (idempotent)
3. Parse via graphify_adapter
4. Load prior snapshot from blob store (if exists)
5. diff_snapshots → ops
6. tier1_resolve each op
7. Build Episode, append to episode store
8. Apply to Neo4j via supergraph store
9. Save local aliases
10. Invalidate subgraph cache

- [ ] **Step 3: Run test, commit**

---

### Task 11: Temporal Materializer

**Files:**
- Create: `src/episodic/materializer.py`
- Test: `tests/unit/test_materializer.py`

- [ ] **Step 1: Write failing time-travel test**

```python
def test_materialize_excludes_retracted_nodes(episodes):
    view = materialize(subgraph_id="test", as_of="2026-07-06T18:00:00Z", episodes=episodes)
    assert "removed_function" not in [n.label for n in view.nodes]
    assert "authenticate_user" in [n.label for n in view.nodes]
```

- [ ] **Step 2: Implement materializer.py**

Returns `networkx.DiGraph`:
1. Iterate episodes where `recorded_at <= as_of` (and matching subgraph_id if scoped)
2. Apply ops in sequence order
3. Filter to assertions where `valid_from <= as_of < valid_to`

- [ ] **Step 3: Run test, commit**

---

### Task 12: Graphify Delegate

**Files:**
- Create: `src/episodic/graphify_delegate.py`
- Test: `tests/integration/test_graphify_delegate.py` (skip if graphify not installed)

- [ ] **Step 1: Implement subprocess wrapper**

```python
def graphify_query(question: str, graph_path: Path, binary: str = "graphify") -> str:
    result = subprocess.run(
        [binary, "query", question, "--graph", str(graph_path)],
        capture_output=True, text=True, check=True,
    )
    return result.stdout
```

Also: `graphify_path`, `graphify_explain` wrappers.

- [ ] **Step 2: Test with fixture graph (or skip)**

- [ ] **Step 3: Commit**

---

### Task 13: CLI

**Files:**
- Create: `src/episodic/cli/main.py`
- Test: `tests/e2e/test_cli_smoke.py`

- [ ] **Step 1: Implement typer commands**

```python
app = typer.Typer()

@app.command()
def register(subgraph_id: str, source: Path, graphify_out: Path): ...

@app.command()
def ingest(subgraph_id: str, graph: Path | None = None): ...

@app.command()
def status(): ...

@app.command()
def query(
    question: str,
    scope: str = "subgraph",
    subgraph_id: str | None = None,
    as_of: str | None = None,
): ...
```

`query` behavior:
- `--scope subgraph` → resolve latest graph.json path from registry → graphify_delegate
- `--scope supergraph` → Neo4j traverser (simple keyword match for Phase 1, not LLM router)
- `--as-of` → materializer path for subgraph; Neo4j temporal filter for supergraph

- [ ] **Step 2: Write CLI smoke test using typer CliRunner**

- [ ] **Step 3: Commit**

---

### Task 14: Bootstrap Import (graphify global-graph)

**Files:**
- Modify: `src/episodic/ingest/pipeline.py`
- Create: `src/episodic/ingest/bootstrap.py`

- [ ] **Step 1: Implement bootstrap import**

`episodic bootstrap --from-global ~/.graphify/global-graph.json`:
- Create synthetic `ep_000000` with `trigger.type: bootstrap_import`
- All nodes → `ASSERT_NODE`, all edges → `ASSERT_EDGE`
- All assertions get `valid_from = import_time`

- [ ] **Step 2: Add CLI command, test with minimal fixture, commit**

---

### Task 15: Phase 1 Exit Verification

- [ ] **Step 1: Run full test suite**

Run: `pytest tests/ -v --ignore=tests/integration/test_neo4j_projection.py`
Run: `pytest tests/integration/test_neo4j_projection.py -v -m neo4j` (with Docker up)

- [ ] **Step 2: Manual smoke test**

```bash
docker compose up -d
cp config.example.yaml ~/.episodic-engine/config.yaml
episodic register myrepo-code --source ./examples/repo --graphify-out ./examples/repo/graphify-out
episodic ingest myrepo-code
episodic status
episodic query "auth flow" --scope subgraph --subgraph myrepo-code
episodic query "auth" --scope supergraph
episodic query "auth" --scope subgraph --subgraph myrepo-code --as-of "2026-07-01T00:00:00Z"
```

- [ ] **Step 3: Verify exit criteria from doc 07**

- [ ] Two subgraphs ingested with Tier 1 cross-link
- [ ] Re-ingest unchanged → zero ops
- [ ] `--as-of` returns different state before/after known change
- [ ] Supergraph path crosses subgraph boundary

- [ ] **Step 4: Final commit**

```bash
git commit -m "chore: phase 1 hybrid-local complete"
```

---

## Phase 2 Preview (Not In This Plan)

- Rule + LLM hybrid query router ([04-query-routing-engine.md](../04-query-routing-engine.md))
- Tier 3 embedding resolution + local vector store
- Hybrid query merge (Neo4j anchors + graphify expansion)
- MCP server extensions
- `episodic diff` command

---

## Plan Self-Review

| Spec Requirement | Task |
|------------------|------|
| Subgraph registry | Task 4, 10, 13 |
| Snapshot ingestion (immutable blobs) | Task 5, 10 |
| Snapshot differ | Task 7 |
| Episode log (append-only) | Task 4 |
| StoragePort interfaces | Task 3 |
| Tier 1 entity resolution | Task 8 |
| Neo4j projection | Task 9 |
| Basic CLI + query | Task 13 |
| Time-travel `--as-of` | Task 11, 13 |
| graphify bootstrap | Task 14 |
| graphify delegation | Task 12 |
| Hybrid-local profile | Task 1, 3, throughout |

No placeholder tasks. All op types from doc 02 covered in Task 2. StoragePort swap path preserved for Phase 3 team drivers.
