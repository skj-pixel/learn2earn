from sqlalchemy.exc import OperationalError

from app.services import generation_task_service


def test_generation_does_not_replay_workflow_after_database_error(monkeypatch):
    attempts = []

    def flaky_run(task_id, user):
        attempts.append(task_id)
        raise OperationalError("INSERT products", {}, Exception("unable to open database file"))

    monkeypatch.setattr(generation_task_service, "_run_task_once", flaky_run)
    monkeypatch.setattr(generation_task_service, "_update", lambda *args, **kwargs: None)

    generation_task_service._run_task(17, {"id": "local:test@example.com"})

    assert attempts == [17]
