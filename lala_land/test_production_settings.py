import importlib
import sys


def test_production_security_cannot_be_overridden_by_local_settings(monkeypatch):
    monkeypatch.setenv("DJANGO_SECRET_KEY", "production-test-secret")
    monkeypatch.setenv("DJANGO_ALLOWED_HOSTS", "example.test")
    monkeypatch.setenv("WAGTAILADMIN_BASE_URL", "https://cms.example.test/")
    monkeypatch.setenv("DATABASE_ENGINE", "postgresql")
    monkeypatch.setenv("POSTGRES_DB", "lala_land")
    monkeypatch.setenv("POSTGRES_USER", "lala_land")
    monkeypatch.setenv("POSTGRES_PASSWORD", "not-used-by-this-test")
    monkeypatch.setenv("EMAIL_HOST", "smtp.example.test")

    sys.modules.pop("lala_land.settings.production", None)
    production = importlib.import_module("lala_land.settings.production")

    assert production.DEBUG is False
    assert production.ALLOWED_HOSTS == ["example.test"]
    assert production.WAGTAILADMIN_BASE_URL == "https://cms.example.test"
    assert production.CSRF_COOKIE_SECURE is True
    assert production.SESSION_COOKIE_SECURE is True
    assert production.SECURE_SSL_REDIRECT is True
    assert production.EMAIL_HOST == "smtp.example.test"
    assert production.EMAIL_TIMEOUT == 10
    assert production.MIDDLEWARE[1] == "whitenoise.middleware.WhiteNoiseMiddleware"
    assert production.STORAGES["staticfiles"]["BACKEND"] == (
        "whitenoise.storage.CompressedManifestStaticFilesStorage"
    )


def test_render_environment_supplies_host_admin_url_and_database(monkeypatch):
    base = importlib.import_module("lala_land.settings.base")
    with monkeypatch.context() as environment:
        environment.setenv("DJANGO_SECRET_KEY", "production-test-secret")
        environment.delenv("DJANGO_ALLOWED_HOSTS", raising=False)
        environment.delenv("WAGTAILADMIN_BASE_URL", raising=False)
        environment.setenv("RENDER_EXTERNAL_HOSTNAME", "lala-land-properties.onrender.com")
        environment.setenv("DATABASE_URL", "postgresql://lala:secret@db.example.test:5432/lala")
        environment.setenv("EMAIL_HOST", "smtp.example.test")
        environment.setenv("MEDIA_ROOT", "/var/data/media")

        importlib.reload(base)
        sys.modules.pop("lala_land.settings.production", None)
        production = importlib.import_module("lala_land.settings.production")

        assert production.ALLOWED_HOSTS == ["lala-land-properties.onrender.com"]
        assert production.WAGTAILADMIN_BASE_URL == "https://lala-land-properties.onrender.com"
        assert production.DATABASES["default"]["ENGINE"] == "django.db.backends.postgresql"
        assert production.DATABASES["default"]["CONN_MAX_AGE"] == 60
        assert production.DATABASES["default"]["CONN_HEALTH_CHECKS"] is True
        assert production.MEDIA_ROOT.as_posix() == "/var/data/media"

    sys.modules.pop("lala_land.settings.production", None)
    importlib.reload(base)
