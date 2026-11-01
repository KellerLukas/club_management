#!/usr/bin/env bash
set -euo pipefail

cd -- "$(dirname -- "$0")"
version=$(uv version --short)

uv lock
uv run pytest

git add .
git diff --cached --quiet || git commit -m "Release v$version"
git tag "v$version"
git push --atomic origin HEAD "v$version"
