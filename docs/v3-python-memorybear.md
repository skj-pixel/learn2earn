# V3 lightweight Python MemoryBear

V3 retains all V2 product behavior and changes only the MemoryBear implementation. The heavy upstream source and optional HTTP service are replaced by the vendored standard-library Python engine under `vendor/memory_bear_py`.

## Faithful translation boundary

The supplied engine already implements SQLite persistence, working-memory LRU, activation decay, pruning, reflection, a knowledge graph, and QUICK/DEEP routing. Learn2Earn adds the official five-category semantics at the adapter boundary:

| Official semantic category | Lightweight storage |
| --- | --- |
| perception | current generation query, not persisted |
| working | current note in working memory |
| episodic | historical notes in short-term storage |
| explicit | generated products in long-term storage |
| implicit | derived user preferences in long-term storage |

Stable IDs make repeated generation idempotent. Each user gets a separate hashed SQLite database under `storage/memory-bear-v3`, preventing memories from leaking between users. The current note is excluded from recalled historical context.

This is a faithful local translation of the mechanisms Learn2Earn uses, not a claim that the compact engine reproduces every upstream service, workflow, model, or infrastructure component.
