from sqlalchemy.exc import OperationalError

from app.cloud_db import LocalTable


class RetryQuery:
    def __init__(self, attempts):
        self.attempts = attempts

    def filter(self, *args):
        return self

    def order_by(self, *args):
        return self

    def all(self):
        self.attempts.append(1)
        if len(self.attempts) == 1:
            raise OperationalError("SELECT notes", {}, Exception("unable to open database file"))
        return []


class RetrySession:
    def __init__(self, attempts):
        self.attempts = attempts

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return None

    def query(self, model):
        return RetryQuery(self.attempts)


def test_local_table_retries_transient_database_open_error(monkeypatch):
    attempts = []
    monkeypatch.setattr("app.cloud_db.SessionLocal", lambda: RetrySession(attempts))

    assert LocalTable("notes", "local:test@example.com").list() == []
    assert len(attempts) == 2
