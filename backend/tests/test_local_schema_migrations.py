from sqlalchemy import create_engine, inspect, text

from app.database import _ensure_new_columns


def test_legacy_generation_tasks_get_product_strategies_column(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'legacy.db'}")
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE generation_tasks (id INTEGER PRIMARY KEY, status TEXT)"))

    _ensure_new_columns(engine)

    columns = {column["name"] for column in inspect(engine).get_columns("generation_tasks")}
    assert "product_strategies" in columns
