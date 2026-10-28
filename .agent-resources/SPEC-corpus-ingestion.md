# Spec: corpus-ingestion

**Module id:** `corpus-ingestion`  
**Status:** Draft for review (2026-10-27). The first build cut is narrower: Python and Markdown only, over a stdio MCP create tool. See [ADR-001](../docs/decisions/ADR-001-stdio-mcp-context-graph.md). PDFs, images, and the model organizer stay in this spec for a later slice.  
**Map:** [capability-map-initial-graph.md](./capability-map-initial-graph.md)  
**Depends on:** [SPEC-graph-model.md](./SPEC-graph-model.md)  
**Background:** [08-graphify-integration.md](./08-graphify-integration.md), [prds/2026-07-06-single-subgraph-save.md](./prds/2026-07-06-single-subgraph-save.md)

## Objective

Ingest one folder of mixed context and write a `graph-model` graph: code as structure, plus Markdown, PDFs, and images as document nodes tied back to the files they came from.

**User:** a developer (or a later harness) who points Episodic at a repository and expects a walkable context graph, not a second copy of the files dumped into prompts.

**Benchmark:** a small Python repository committed at `tests/fixtures/benchmark-repo`, plus one Markdown file, one PDF, and one image. The automated gate is that fixture. A larger external repo is a measurement, not the gate. Structural organizers must pass with no model installed. The model organizer is tested with a fake model, not a network call.

### PRD scope

**In scope**

- A directory ingest command that writes one named graph: `--name` selects the graph. Re-ingest of the same name updates that graph in place.
- `episodic merge-graphs --into <name> --from <name>` unions the source graph into the destination using the merge rule in [SPEC-graph-model.md](./SPEC-graph-model.md). The source graph is left as it is.
- Organizer methods. Every ingested file is assigned one method. The method either places context on the graph without a model, or calls a model when the bytes are not enough to organize.

| Method id | Data | Model |
|---|---|---|
| `python-ast` | `*.py` | no |
| `markdown-node` | `*.md` | no |
| `model-context` | `*.pdf`, images (`*.png`, `*.jpg`, `*.jpeg`, `*.webp`, `*.gif`), and any other kept file whose type has no structural method | yes |
| `file-provenance` | fallback when `model-context` cannot run | no |

- `python-ast` uses the stdlib `ast` module. It emits `file` and `symbol` nodes and `contains`, `imports`, and `calls` edges when the syntax states them.
- `markdown-node` builds on `parse_markdown_node` / `ingest_markdown_node` in `src/episodic/ingest/markdown_node.py`. Folder ingest does not reimplement Markdown parsing and does not prompt. It maps that parser’s node onto the `graph-model` hot record and stores the Markdown body as cold payload. Heading sections become `chunk` nodes the file `contains`. The `episodic ingest-node` command stays as the interactive single-file path.
- `model-context` sends the file to a model organizer and accepts only `graph-model` nodes and the five locked edge types back. Hot records still omit raw bytes. If no model is configured, the file is stored with `file-provenance` and `organizer_status: model_required`. The command does not fail the rest of the folder.
- Graphify is not a required dependency and is not imported. `model-context` has a seam for a later provider. These specs do not choose that provider. Tests call a fake organizer only.
- Idempotent re-ingest: identical source bytes for a file produce no new node ids and no duplicate edges.
- The benchmark fixture asserts at least one `contains` edge from a Python file to a symbol, plus a node each for the Markdown file, the PDF, and the image.

**Out of scope**

- Entity-resolution tiers, episodes as a user-facing feature, and silent overwrite of conflicting labels (merge records a conflict instead).
- Search latency (module `graph-search`).
- Office documents, audio, video, HTML sites, and archives, except as `file-provenance` when they are not skipped.
- Languages other than Python getting symbol nodes in this phase.
- Training a model. Calling a model is allowed only inside `model-context`.

### Acceptance stories

- As a developer, I run one command on a repo folder and get a graph whose code symbols are linked to the files that contain them.
- As a developer, a PDF or image is organized by `model-context` when a model is configured, and still kept as a provenance node with `model_required` when it is not.
- As a developer, `episodic ingest-node` still adds one Markdown node interactively after `ingest-corpus` exists.
- As a developer, running ingest twice on an unchanged repo does not duplicate symbols.
- As a developer, I merge two named graphs and the destination gains nodes that existed only on the source, without deleting the source graph.

## Tech Stack

- Python 3.11+ (`ast` for Python; existing Markdown parser for notes)
- Typer CLI (`episodic` script already declared in `pyproject.toml`)
- pytest
- The adjacency graph shipped at `demo-graph/test-graph/` ([SPEC-graph-model.md](./SPEC-graph-model.md))
- A model organizer interface with no live provider. Tests inject a fake organizer. Choosing the live model is a later spec. Graphify is not a dependency.

## Commands

```bash
pip install -e ".[dev]"
python -m pytest tests/unit/test_corpus_ingest.py tests/integration/test_corpus_ingest.py -q

episodic ingest-corpus --source ./path/to/repo --name "repo-context"
episodic ingest-corpus --source ./path/to/repo --name "repo-context" --code-only
episodic ingest-corpus --source ./path/to/repo --name "repo-context" --skip-assets
episodic merge-graphs --into "repo-context" --from "other-graph"
```

`--name` is the graph. One name is one graph. Running ingest again with the same name updates that graph.

`--code-only` runs `python-ast` only. `--skip-assets` skips PDF and image files and still runs `markdown-node`. The default command selects the organizer from the table above.

`merge-graphs` requires both names to exist. It applies the `graph-model` merge rule. It does not call a model. Integration tests for `python-ast` and `markdown-node` must pass with no model configured. `model-context` tests use the fake organizer.

## Project Structure

```text
src/episodic/ingest/markdown_node.py → existing single-node parser; corpus calls it
src/episodic/ingest/organize.py      → method ids and selection by file type
src/episodic/ingest/corpus.py        → walk the folder and dispatch organizers
src/episodic/ingest/merge.py         → CLI-facing wrapper around graph-model merge
src/episodic/cli/main.py             → keep ingest-node; add ingest-corpus and merge-graphs
demo-graph/test-graph/               → graph the commands write through
tests/fixtures/benchmark-repo/       → tiny Python repo: code + one md + one pdf + one png
tests/unit/test_corpus_ingest.py
tests/integration/test_corpus_ingest.py
.agent-resources/SPEC-corpus-ingestion.md
```

Named graphs persist as files the `demo-graph/test-graph` loader can read. Tests must not import graphify or call a live model.

## Code Style

Same as the rest of `src/episodic`: small functions, explicit paths, raise `ValueError` / `FileNotFoundError` for bad input.

```python
def organize_file(path: Path, *, model: ModelOrganizer | None) -> OrganizerResult:
    """Pick python-ast, markdown-node, model-context, or file-provenance."""
    ...
```

Conventions:

- Source paths stored in provenance are relative to `source_root` when the file is inside it.
- Skip directories named `.git`, `node_modules`, `.venv`, `venv`, `__pycache__`, `dist`, `build`.
- Do not follow symlinks that leave `source_root`.
- A missing source directory fails the command. A PDF or image with no model configured still creates a provenance node and sets `organizer_status` to `model_required`.
- `ingest-corpus` does not delete or rewrite the `ingest-node` command. Markdown bytes go through `markdown_node.py`.
- `merge-graphs` on a missing name fails with a non-zero exit. A label conflict does not fail the command; it is reported and the destination label stays.

## Testing Strategy

- **Unit:** `tests/unit/test_corpus_ingest.py` covers `python-ast` and `markdown-node` with no model. A separate case feeds a one-node fake `model-context` result for a PDF and asserts those nodes land on the graph. Assert locked edge types, stable ids, and that hot nodes do not contain file text.
- **Integration:** `tests/integration/test_corpus_ingest.py` runs against `tests/fixtures/benchmark-repo` and a two-graph merge. With no model configured, the PDF and PNG exist as `file-provenance` nodes tagged `model_required`. With the fake model, those files use `model-context`. The test process must not import graphify and must not call a live model API. `episodic ingest-node --help` still exists.
- **Benchmark check (manual or opt-in):** ingest a larger real repository and record node count, edge count, and wall time. That run is a measurement. The committed fixture is the automated gate.

No coverage quota. Required behaviors are the success criteria.

## Boundaries

- **Always:** assign one organizer method per file; write `graph-model` records through `demo-graph/test-graph`; keep source bytes out of hot nodes; build Markdown ingest on `markdown_node.py`; leave `episodic ingest-node` in place; skip vendor and VCS directories; make a second ingest of unchanged inputs a no-op on ids; keep one graph per `--name`.
- **Ask first:** adding a model SDK or PDF library to `pyproject.toml`; choosing the live `model-context` provider; new organizer methods; changing which file types require a model; removing `--skip-assets`; changing merge so a conflict overwrites the destination label.
- **Never:** replace or remove `episodic ingest-node`; require a model for `.py` or `.md`; drop a PDF or image with no provenance node (unless `--skip-assets` or `--code-only`); call a live model from tests; duplicate node ids for the same fingerprint; commit API keys; treat the whole repository text as one node; delete the `--from` graph during merge.

## Success Criteria

On `tests/fixtures/benchmark-repo`:

- [ ] `episodic ingest-corpus --source tests/fixtures/benchmark-repo --name bench` exits 0 with no model configured and writes a graph loadable by `demo-graph/test-graph`.
- [ ] The graph contains at least one `file` node and one `symbol` node connected by `contains`, produced by `python-ast`.
- [ ] The Markdown file is produced by `markdown-node` using `markdown_node.py`, not a second parser.
- [ ] With no model, the PDF and the PNG each have a provenance node tagged `model_required`. With the fake model, those files are produced by `model-context` and still point at the source path.
- [ ] `episodic ingest-corpus --source tests/fixtures/benchmark-repo --name bench --skip-assets` writes the Markdown node and does not write the PDF or PNG nodes.
- [ ] `episodic ingest-node` remains a registered command.
- [ ] Hot nodes do not include the PDF bytes or the full Markdown body (assert key absence).
- [ ] A second ingest with no file changes adds zero nodes and zero edges.
- [ ] Changing one function’s name in the fixture changes that symbol’s id or label and does not create a second `file` node for the same path.
- [ ] `episodic merge-graphs --into bench --from extra` adds a node that exists only on `extra`, leaves `extra` unchanged, and on a label conflict keeps `bench`’s label and records the conflict.
- [ ] Unit tests pass with no network and no graphify import.

**Reframe of “turn a folder into a context graph”:** done means each file goes through an organizer method, structural files need no model, and unstructured files use a model when one is configured.

## Open Questions

None for this module. `--skip-assets` stays. The live `model-context` provider is explicitly deferred.
