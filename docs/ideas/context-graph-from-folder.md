# Context graph from a code folder

## Problem Statement

How might we let any agent harness turn one code folder into a named context graph, over stdio, so it sees how the code is structured and how calls move through it, without pasting the repo into the prompt?

## Recommended Direction

The harness launches one stdio MCP server. The server does not depend on which product launched it. The first tool is `create_context_graph(folder, name)`. The harness chooses `name`. Episodic registers the graph under that name, the same way `create-graph` already registers a name, and writes the hot graph to that graph’s `graph.json`.

The walk is structural and flow-aware:

- The folder is the root.
- Each directory is a hub. A hub `contains` its children, so names like “backend” and “frontend” show up when those directories exist.
- Each Python file is a `file` node. The `ast` module finds functions and classes. The file `contains` those symbols.
- `imports` edges come from import statements.
- `calls` edges come from call expressions. That is the code flow: who calls whom, including a call that reaches a function in another file when the import makes the target clear.
- Each Markdown file goes through the existing `ingest-node` path. Headings stay chunks. The link type stays whatever that command already allows.

The tool returns the hot map: ids, labels, types, and edges. File bodies stay in the payload store.

A control-flow graph, with an edge for every branch and loop, is a different structure. This slice uses the call graph. A frontend button gets an arrow to a database function only when the parsed code actually calls it.

Decision record: [ADR-001](../decisions/ADR-001-stdio-mcp-context-graph.md).

## Key Assumptions to Validate

- [ ] A harness can pass a folder path and a graph name into a stdio tool and use the returned map without opening every file.
- [ ] Directory hubs plus `contains`, `imports`, and `calls` match “how this folder fits together” on a Python repo.
- [ ] Call edges that cross files are reliable enough when the callee is an imported name. Calls through a variable or a string stay unresolved, and that is acceptable for this slice.

## MVP Scope

In: stdio MCP, one write tool, harness-supplied name, Python via `ast`, Markdown via `ingest-node`, hot map in the tool result, graph registered and saved.

Out of the tool result: file bytes. Out of the parser: PDFs, images, a model, and edges the AST did not see.

## Not Doing (and Why)

- A Claude Code-only config inside the server. Any harness that speaks stdio MCP can launch the same process.
- PDFs, images, and a model organizer. Those stay in [SPEC-corpus-ingestion.md](../../.agent-resources/SPEC-corpus-ingestion.md) for a later slice.
- A drawn graph. The tool returns structure.
- Invented cross-layer edges. A button-to-database arrow is in scope only when a call or import states it.
- Branch-level control flow. Call flow answers how a run moves. A graph of every `if` would bury that map.

## Open Questions

None that block a spec. Unresolved calls through variables stay missing until a later pass.
