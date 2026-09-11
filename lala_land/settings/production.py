import os

from django.core.exceptions import ImproperlyConfigured

from .base import *  # noqa: F403

DEBUG = False

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY")
if not SECRET_KEY:
    raise ImproperlyConfigured("DJANGO_SECRET_KEY is required in production")

configured_hosts = [
    host.strip() for host in os.getenv("DJANGO_ALLOWED_HOSTS", "").split(",") if host.strip()
]
render_hostname = os.getenv("RENDER_EXTERNAL_HOSTNAME", "").strip()
ALLOWED_HOSTS = list(dict.fromkeys([host for host in [*configured_hosts, render_hostname] if host]))
if not ALLOWED_HOSTS:
    raise ImproperlyConfigured(
        "DJANGO_ALLOWED_HOSTS or RENDER_EXTERNAL_HOSTNAME is required in production"
    )

WAGTAILADMIN_BASE_URL = os.getenv("WAGTAILADMIN_BASE_URL", "").rstrip("/")
if not WAGTAILADMIN_BASE_URL and render_hostname:
    WAGTAILADMIN_BASE_URL = f"https://{render_hostname}"
if not WAGTAILADMIN_BASE_URL:
    raise ImproperlyConfigured(
        "WAGTAILADMIN_BASE_URL or RENDER_EXTERNAL_HOSTNAME is required in production"
    )

if not os.getenv("DATABASE_URL") and os.getenv("DATABASE_ENGINE") != "postgresql":
    raise ImproperlyConfigured("PostgreSQL is required in production")

MIDDLEWARE.insert(1, "whitenoise.middleware.WhiteNoiseMiddleware")  # noqa: F405

# ManifestStaticFilesStorage is recommended in production, to prevent
# outdated JavaScript / CSS assets being served from cache
# (e.g. after a Wagtail upgrade).
# See https://docs.djangoproject.com/en/6.0/ref/contrib/staticfiles/#manifeststaticfilesstorage
STORAGES["staticfiles"]["BACKEND"] = "whitenoise.storage.CompressedManifestStaticFilesStorage"

CSRF_COOKIE_SECURE = True
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_HSTS_SECONDS = int(os.getenv("SECURE_HSTS_SECONDS", "31536000"))
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = True
X_FRAME_OPTIONS = "DENY"

EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = os.getenv("EMAIL_HOST", "")
if not EMAIL_HOST:
    raise ImproperlyConfigured("EMAIL_HOST is required in production")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = os.getenv("EMAIL_USE_TLS", "true").lower() in {"1", "true", "yes"}
EMAIL_TIMEOUT = int(os.getenv("EMAIL_TIMEOUT", "10"))
