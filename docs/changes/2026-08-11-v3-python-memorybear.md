# V3 Python MemoryBear replacement

- Added a dedicated V3 launcher and explicit V2/V3 feature notes.
- Replaced the 91 MB upstream MemoryBear tree and HTTP adapter with `memory_bear_py.zip` source.
- Extended the lightweight engine with stable IDs and explicit storage layers.
- Added five-category semantic mapping, idempotent persistence, and per-user SQLite isolation.
- Kept V2 Skill labels 0-13. Compatibility is now modeled as two hidden rule groups: algorithms and Skills share one generation-stage group, while quality techniques use a separate post-generation group. Users only see a warning naming the conflicting pairs they actually selected.
- Added adapter regression tests for isolation, five-layer metadata, retrieval, and idempotency.
