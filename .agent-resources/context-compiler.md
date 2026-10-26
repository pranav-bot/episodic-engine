# Episodic Context Compiler

## Problem Statement

How might we compile unstructured organizational data into a multi-resolution
context graph that can retrieve useful, well-supported context within a
1–10-second target while minimizing unnecessary model tokens?

## Recommended Direction

Build Episodic as a context compiler rather than only a graph store. Ingestion
should transform source data into linked representations with preserved
provenance: documents and source spans, normalized entities, claims,
relationships, and summaries.

Use multiple resolutions so retrieval can begin with inexpensive coarse
representations and descend into detailed claims and source evidence only when
needed. The first experiment should compare representations on a fixed corpus
of 10,000 nodes, using fixed queries and human scoring of the returned context.

The initial system should be deterministic enough to isolate representation
quality. Embeddings, model-guided traversal, merging, and learned indexes can
be evaluated after the representation baseline is established.

## Key Assumptions to Validate

- [ ] Multi-resolution representations improve usefulness over flat chunks or a
      single graph representation. Test identical source data and queries
      across each representation.
- [ ] Provenance can be preserved through normalization and summarization.
      Review whether human evaluators can trace each returned claim to source
      spans.
- [ ] Coarse-to-fine retrieval can meet the 1–10-second latency target at
      10,000 nodes. Record p50 and p95 latency for a fixed query set.
- [ ] Human scoring of fixed query results is repeatable enough to compare
      representations. Use a rubric for relevance, completeness, evidence
      quality, and unnecessary context.

## MVP Scope

- Ingest a bounded set of unstructured documents.
- Produce a versioned, multi-resolution graph with source provenance.
- Support deterministic retrieval over the compiled representation.
- Return a bounded context package containing relevant nodes, relationships,
  summaries, and source references.
- Benchmark at 10,000 nodes with a fixed set of representative queries.
- Record node count, ingestion time, storage size, p50/p95 retrieval latency,
  and human usefulness scores.

## Not Doing (and Why)

- **Graph merging** — adds conflict and lineage complexity before the base
  representation is understood.
- **Model-guided traversal** — can hide representation failures behind model
  behavior.
- **Embeddings as the first retrieval strategy** — evaluate them as a later
  baseline after deterministic representations are measurable.
- **Learned indexes** — premature optimization until query bottlenecks are
  observed.
- **Unbounded graph walks** — they threaten latency and produce excessive
  context.
- **A general organization ontology** — start with representation primitives
  that can be tested across data types.

## Open Questions

- Which resolution levels are actually useful: document, topic, entity, claim,
  event, source span, or another hierarchy?
- What exactly counts as a node, and when should a relationship become a
  first-class object?
- How should conflicting claims and stale sources be represented?
- What is the maximum context package size before answer quality declines?
- Which fixed query set best represents real organizational context use cases?
