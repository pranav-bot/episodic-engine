"""Episodic Engine — versioned graphify subgraph memory.

This package provides an episodic memory layer for graphify knowledge graphs.
It treats each regeneration of a graph as a snapshot, diffs against the previous
snapshot to produce a list of operations, and stores them as versioned episodes
in a local SQLite store with full snapshots content-addressed in a blob store.

Think of it as "Git for a knowledge graph":
- Full snapshots = committed trees at points in time
- Episodes = commits containing only the diff (operations)
- SQLite = history/log
- Fingerprints = stable identity for nodes/edges across snapshots
"""

__version__ = "0.1.0"

