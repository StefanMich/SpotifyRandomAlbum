#!/bin/bash
set -e

# Check if a package name was provided
if [ $# -eq 0 ]; then
  echo "Error: No package name provided"
  echo "Usage: ./add-dependency.sh PACKAGE_NAME [VERSION]"
  echo "Example: ./add-dependency.sh gunicorn \"~=23.0.0\""
  exit 1
fi

PACKAGE_NAME=$1
VERSION=$2

echo "🔍 Adding dependency: $PACKAGE_NAME $VERSION"

# Run in a Docker container
echo "Creating Docker container to update dependencies..."
docker run --rm -v $(pwd):/app -w /app python:3.11-slim bash -c "pip install pipenv && if [ -z \"$VERSION\" ]; then pipenv install $PACKAGE_NAME; else pipenv install $PACKAGE_NAME==$VERSION; fi"

echo "Dependency added successfully!"
echo "Remember to rebuild your Docker image with: docker-compose build"
echo "Then restart your containers with: docker-compose down && docker-compose up"
