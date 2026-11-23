#!/bin/bash
set -euo pipefail

if [ $# -eq 0 ]; then
  echo "Error: No package name provided"
  echo "Usage: ./add-dependency.sh PACKAGE_NAME [VERSION]"
  echo "Example: ./add-dependency.sh gunicorn \"~=23.0.0\""
  exit 1
fi

package_name=$1
version=${2:-}

if [ -n "$version" ]; then
  case "$version" in
    =*|~*|<*|>*|!*) spec="${package_name}${version}" ;;
    *) spec="${package_name}==${version}" ;;
  esac
else
  spec="$package_name"
fi

echo "Adding dependency: $spec"

docker run --rm \
  -v "$(pwd)":/app \
  -w /app \
  -e UV_PROJECT_ENVIRONMENT=/tmp/venv \
  ghcr.io/astral-sh/uv:0.13.9-python3.15-trixie-slim \
  uv add --no-sync "$spec"

echo "Dependency added successfully!"
echo "Remember to rebuild your Docker image with: docker compose build"
echo "Then restart your containers with: docker compose down && docker compose up"
