
# This stage installs build dependencies and compiles Python packages.
# It will be discarded in the final image, keeping only the compiled packages.
FROM python:3.13-slim-bookworm AS builder

# Install system packages required to build Python packages.
RUN apt-get update --yes --quiet && apt-get install --yes --quiet --no-install-recommends \
    build-essential \
    libpq-dev \
    libmariadb-dev \
    libjpeg62-turbo-dev \
    zlib1g-dev \
    libwebp-dev \
 && rm -rf /var/lib/apt/lists/* \
 && python -m venv /opt/venv

ENV PATH="/opt/venv/bin:$PATH"

# Install the project requirements.
COPY requirements.txt /
RUN pip install -r /requirements.txt

# RUNTIME STAGE
# Use an official Python runtime based on Debian 12 "bookworm" as a parent image.
FROM python:3.13-slim-bookworm AS runtime

# Install runtime system packages required by Wagtail and Django.
# These are the runtime libraries needed by the compiled Python packages.
RUN apt-get update --yes --quiet && apt-get install --yes --quiet --no-install-recommends \
    libpq5 \
    libmariadb3 \
    libjpeg62-turbo \
    libwebp7 \
 && rm -rf /var/lib/apt/lists/*

# Add user that will be used in the container.
RUN useradd wagtail

# Port used by this container to serve HTTP.
EXPOSE 8000

# Set environment variables.
# 1. Force Python stdout and stderr streams to be unbuffered.
# 2. Set PORT variable that is used by Gunicorn. This should match "EXPOSE"
#    command.
# 3. Add the virtual environment to PATH.
ENV PYTHONUNBUFFERED=1 \
    PORT=8000 \
    PATH="/opt/venv/bin:$PATH"



# Copy the virtual environment from the builder stage.
COPY --from=builder /opt/venv /opt/venv

# Use /app folder as a directory where the source code is stored.
WORKDIR /app

# Give the unprivileged application user access to its code and upload directory.
RUN mkdir -p /var/data/media \
 && chown wagtail:wagtail /app \
 && chown -R wagtail:wagtail /var/data

# Copy the source code of the project into the container.
COPY --chown=wagtail:wagtail . .

# Use user "wagtail" to run the build commands below and the server itself.
USER wagtail

# Build the production asset manifest without connecting to a real database.
# These values are build-only placeholders, never runtime credentials.
RUN DJANGO_SETTINGS_MODULE=lala_land.settings.production \
    DJANGO_SECRET_KEY=build-only-placeholder-not-a-production-secret \
    DJANGO_ALLOWED_HOSTS=build.invalid \
    WAGTAILADMIN_BASE_URL=https://build.invalid \
    DATABASE_URL=postgresql://build:build@localhost/build \
    EMAIL_HOST=build.invalid \
    python manage.py collectstatic --noinput --clear

# Database migrations run as a separate, explicit release step.
CMD ["sh", "-c", "gunicorn lala_land.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers 1 --threads 2"]
