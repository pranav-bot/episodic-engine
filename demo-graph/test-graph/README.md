# test-graph

In-memory adjacency graph used by demos and tests. This folder is not a Python package. Load the file by path:

```python
import importlib.util
from pathlib import Path

path = Path("demo-graph/test-graph/adjacency.py")
spec = importlib.util.spec_from_file_location("test_graph_adjacency", path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
graph = module.MemoryGraph()
```
