#!/bin/zsh
# Commits the weekly ArcGIS snapshot. Called by launchd or manually via `make snapshot-commit`.
set -euo pipefail
cd "$(dirname "$0")/.."

DATE=$(date +%F)
DIR="data/raw/snapshots/$DATE"
LATEST="data/raw/snapshots/latest"

# Heavy layers stay out of history (tens of MB each, re-fetchable on demand);
# their .meta.json still gets committed so the timeline keeps checksums.
EXCLUDES=(
  ':(exclude)data/raw/snapshots/*/quadras.geojson'
  ':(exclude)data/raw/snapshots/*/logradouros.geojson'
  ':(exclude)data/raw/snapshots/*/zoneamento.geojson'
)

# data/raw is gitignored except snapshots — force-add them (excludes come last)
# shellcheck disable=SC2046
git add -f -- "$DIR" "$LATEST" "${EXCLUDES[@]}" 2>/dev/null || true

if git diff --cached --quiet; then
  echo "no changes since last snapshot — nothing to commit"
  exit 0
fi

git commit -m "snapshot: $DATE"
git push origin HEAD
