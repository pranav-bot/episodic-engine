# ADR-001: Stdio MCP creates a context graph from a code folder

## Status

Accepted

## Date

2026-10-28

## Context

Episodic can store a hot graph (`graph.json`: nodes, typed edges, payloads) and can ingest one Markdown file with `ingest-node`. It cannot yet turn a code folder into that graph, and no harness can ask it to.

The corpus spec describes a later folder ingest that also covers PDFs, images, and a model organizer. The grand plan describes a read-only MCP surface (`search_context`, `get_node`, `get_neighbors`). The first harness slice is narrower and writes:

- The harness chooses the graph name and passes a folder path.
- The graph is the context of that folder: directory hubs, Python files and symbols, import edges, call edges, and Markdown heading chunks.
- The same server must launch under any harness that speaks stdio MCP. It is not a Claude Code plugin.

Call flow matters. A tree of files is not enough. The map has to show who calls whom when the syntax says so.

## Decision

Ship one stdio MCP server whose first tool is `create_context_graph(folder, name)`.

- Register `name` with the existing graph registry and write that graph’s `graph.json`.
- Walk the folder. Each directory is a hub that `contains` its children.
- Parse Python with the stdlib `ast` module. A file `contains` its functions and classes. `imports` come from import statements. `calls` come from call expressions, including a call whose target is clear from an import. That call graph is the code flow for this slice.
- Pass each Markdown file through `ingest_markdown_node`. Do not add a second Markdown parser.
- Return ids, labels, types, and edges. Do not return file bytes.
- Leave calls through a variable, attribute that is not an imported name, or string unresolved.
- Do not emit an edge for every branch or loop.

## Alternatives Considered

### Read-only MCP, creation only on the CLI

- Pros: Matches the grand plan’s read-only harness boundary.
- Cons: The harness cannot ask for the graph to be created.
- Rejected: The harness must be able to create, and later to link and merge. This slice only requires the create tool.

### Return only node and edge counts

- Pros: Smallest tool result.
- Cons: The harness never sees the hubs or the call edges, so it still has to open the repo.
- Rejected: The tool result is the hot map.

### Claude Code-specific server

- Pros: One config file and a faster demo.
- Cons: The server would encode one product’s paths and tool names.
- Rejected: The process is plain stdio MCP. A sample config for a product can be added later. It is not part of the server.

### Control-flow graph (every branch and loop)

- Pros: Closer to “how this function runs” inside one body.
- Cons: Edge count explodes, and it does not answer which component calls which.
- Rejected: Flow means the call graph.

### Invent button-to-database edges when the syntax does not state them

- Pros: Looks like an architecture sketch of a Todo app.
- Cons: The harness would treat a guess as a fact.
- Rejected: An arrow exists only when an import or a call states it.

### PDFs, images, and a model organizer in this slice

- Pros: Matches the full corpus spec.
- Cons: Blocks the code map on a model choice that is explicitly deferred.
- Rejected: Python and Markdown only. The rest of the corpus spec stays later.

## Consequences

- The grand plan’s “MCP is read-only” line is superseded for this slice by a create tool. Search tools from that plan are not in this slice.
- [SPEC-corpus-ingestion.md](../../.agent-resources/SPEC-corpus-ingestion.md) remains the full folder spec. This ADR is the first build cut: no PDFs, no images, no model.
- Unresolved calls are missing on purpose. A later pass can fill them. This slice must not invent them.
- Any harness that can launch a stdio MCP process can use the server. Product-specific install docs are separate from the server.
- Idea notes: [context-graph-from-folder.md](../ideas/context-graph-from-folder.md).
