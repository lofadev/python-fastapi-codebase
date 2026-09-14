import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_secret_key_is_required(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SECRET_KEY", raising=False)

    with pytest.raises(ValidationError, match="SECRET_KEY"):
        Settings(_env_file=None)


def test_secret_key_must_have_at_least_32_characters(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SECRET_KEY", "x" * 31)

    with pytest.raises(ValidationError, match="SECRET_KEY"):
        Settings(_env_file=None)


def test_cors_origins_default_to_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SECRET_KEY", "x" * 32)
    monkeypatch.delenv("CORS_ORIGINS", raising=False)

    assert Settings(_env_file=None).CORS_ORIGINS == []
