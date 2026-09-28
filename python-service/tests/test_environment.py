from app.settings import load_local_environment


def test_env_file_loads_without_overriding_terminal(tmp_path, monkeypatch):
    path = tmp_path / ".env"
    path.write_text("AI_PROVIDER=openai\nOPENAI_MODEL=model-from-file\n", encoding="utf-8")
    monkeypatch.setenv("AI_PROVIDER", "offline")
    monkeypatch.delenv("OPENAI_MODEL", raising=False)
    load_local_environment(path)
    import os
    assert os.environ["AI_PROVIDER"] == "offline"
    assert os.environ["OPENAI_MODEL"] == "model-from-file"


def test_missing_env_file_is_optional(tmp_path, monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "offline")
    load_local_environment(tmp_path / "missing.env")
    import os
    assert os.environ["AI_PROVIDER"] == "offline"
