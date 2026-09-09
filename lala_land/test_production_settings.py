import importlib
import sys


def test_production_security_cannot_be_overridden_by_local_settings(monkeypatch):
    monkeypatch.setenv("DJANGO_SECRET_KEY", "production-test-secret")
    monkeypatch.setenv("DJANGO_ALLOWED_HOSTS", "example.test")
    monkeypatch.setenv("DATABASE_ENGINE", "postgresql")
    monkeypatch.setenv("POSTGRES_DB", "lala_land")
    monkeypatch.setenv("POSTGRES_USER", "lala_land")
    monkeypatch.setenv("POSTGRES_PASSWORD", "not-used-by-this-test")
    monkeypatch.setenv("EMAIL_HOST", "smtp.example.test")

    sys.modules.pop("lala_land.settings.production", None)
    production = importlib.import_module("lala_land.settings.production")

    assert production.DEBUG is False
    assert production.ALLOWED_HOSTS == ["example.test"]
    assert production.CSRF_COOKIE_SECURE is True
    assert production.SESSION_COOKIE_SECURE is True
    assert production.SECURE_SSL_REDIRECT is True
    assert production.EMAIL_HOST == "smtp.example.test"
    assert production.EMAIL_TIMEOUT == 10
    assert production.STORAGES["staticfiles"]["BACKEND"].endswith("ManifestStaticFilesStorage")
