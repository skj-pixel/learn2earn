from pathlib import Path

from app.services import memorybear_python_adapter as adapter


def test_python_memorybear_is_user_isolated(tmp_path, monkeypatch):
    monkeypatch.setattr(adapter, "REPO_ROOT", tmp_path)
    note = {"id": 1, "title": "Current", "content": "current query"}
    history = [note, {"id": 2, "title": "History", "content": "current query historical fact", "tags": ["python"]}]
    products = [{"id": 3, "title": "Product", "content": "current query verified output", "product_type": "ppt"}]

    context_a, meta_a = adapter.build_python_memory_context(note, {"name": "Subject"}, history, products, "user-a")
    adapter.build_python_memory_context(note, {"name": "Subject"}, history, products, "user-b")

    databases = list((tmp_path / "storage" / "memory-bear-v3").glob("*.db"))
    assert len(databases) == 2
    assert "historical fact" in context_a or "verified output" in context_a
    assert meta_a["provider"] == "memory-bear-python-v3"
    assert set(meta_a["layers"]) == {"perception", "working", "episodic", "explicit", "implicit"}


def test_python_memorybear_writes_are_idempotent(tmp_path, monkeypatch):
    monkeypatch.setattr(adapter, "REPO_ROOT", tmp_path)
    note = {"id": 7, "title": "Current", "content": "stable query"}
    args = (note, {"name": "Subject"}, [note], [], "same-user")
    adapter.build_python_memory_context(*args)
    _, second_meta = adapter.build_python_memory_context(*args)

    assert second_meta["engine_stats"]["total"] == 2  # working note + derived preferences
