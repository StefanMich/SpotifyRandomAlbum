FROM python:3.11-slim AS base

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

# Install pipenv and compilation dependencies
RUN pip install pipenv
RUN apt-get update && apt-get install -y --no-install-recommends gcc

# Install python dependencies in /.venv
COPY Pipfile .
COPY Pipfile.lock .
RUN PIPENV_VENV_IN_PROJECT=1 pipenv install --deploy


FROM base AS runtime

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

# Create a non-root user and give ownership of /app
RUN useradd --create-home appuser
RUN chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Expose the port
EXPOSE 8000

# Use shell form of ENTRYPOINT with full path
ENTRYPOINT ["/bin/bash", "-c", "if [ \"$ENV\" = \"prod\" ]; then exec ./entrypoint.prod.sh; else exec ./entrypoint.sh; fi"]
