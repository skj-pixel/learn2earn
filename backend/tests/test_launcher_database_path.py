from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_launcher_pins_the_canonical_database_path():
    text = (REPO_ROOT / "scripts" / "start_local_demo_fast.ps1").read_text(encoding="utf-8-sig")
    assert "LEARN2EARN_DATABASE_PATH" in text
    assert "backend\\app\\learn2earn.db" in text
    assert 'EnvironmentVariables["LEARN2EARN_DATABASE_PATH"]' in text
    assert "-m uvicorn backend.app.main:app" in text
    assert "multiprocessing.set_executable" not in text
    assert "$protectedProcessVars = @('PATH', 'TEMP', 'TMP')" in text
    assert "DoNotExpandEnvironmentNames" not in text


def test_database_module_accepts_an_explicit_database_path():
    text = (REPO_ROOT / "backend" / "app" / "database.py").read_text(encoding="utf-8-sig")
    assert "LEARN2EARN_DATABASE_PATH" in text


def test_database_uses_a_bounded_thread_safe_sqlite_pool():
    text = (REPO_ROOT / "backend" / "app" / "database.py").read_text(encoding="utf-8-sig")
    assert "poolclass=QueuePool" in text
    assert "pool_size=3" in text
    assert "max_overflow=0" in text


def test_v1_launcher_guards_release_branch_and_delegates_to_standard_launcher():
    batch = (REPO_ROOT / "启动Learn2Earn-V1验收版.bat").read_text(encoding="utf-8")
    powershell = (REPO_ROOT / "Start-Learn2Earn-V1.ps1").read_text(encoding="utf-8-sig")
    assert "Start-Learn2Earn-V1.ps1" in batch
    assert "git branch --show-current" in powershell
    assert "'release/v1'" in powershell
    assert "scripts\\start_local_demo_fast.ps1" in powershell
