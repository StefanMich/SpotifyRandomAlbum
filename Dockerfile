FROM python:3.15-slim AS base

# Setup env
ENV LANG=C.UTF-8
ENV LC_ALL=C.UTF-8
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONFAULTHANDLER=1
ENV PYTHONUNBUFFERED=1

# Build argument to determine environment
ARG ENV=dev
ENV ENV=${ENV}

FROM base AS python-deps

COPY --from=ghcr.io/astral-sh/uv:0.13.9 /uv /uvx /bin/

ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy
ENV UV_PROJECT_ENVIRONMENT=/.venv
ENV UV_PYTHON_DOWNLOADS=never

WORKDIR /app

# Install dependencies from the lockfile before copying the app
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-dev --no-install-project

FROM base AS runtime

LABEL org.opencontainers.image.source="https://github.com/StefanMich/SpotifyRandomAlbum"

# Copy virtual env from python-deps stage
COPY --from=python-deps /.venv /.venv
ENV PATH="/.venv/bin:$PATH"

# Create app directory
RUN mkdir -p /app
WORKDIR /app

# Copy entrypoint scripts first and make them executable
COPY entrypoint.sh entrypoint.prod.sh ./
RUN chmod +x entrypoint.sh entrypoint.prod.sh

# Copy the rest of the application code
COPY . .

# Create a non-root user and give ownership of /app and /data
RUN groupadd --gid 1000 appuser \
    && useradd --create-home --uid 1000 --gid 1000 appuser \
    && mkdir -p /data \
    && chown -R appuser:appuser /app /data

VOLUME /data

# Switch to non-root user
USER appuser

# Expose the port
EXPOSE 8000

# Use shell form of ENTRYPOINT with full path
ENTRYPOINT ["/bin/bash", "-c", "if [ \"$ENV\" = \"prod\" ]; then exec ./entrypoint.prod.sh; else exec ./entrypoint.sh; fi"]
