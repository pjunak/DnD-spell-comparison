#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DB_PATH="$ROOT_DIR/database/spellBook.db"
DB_BACKUP="$ROOT_DIR/database/spellBook.db.prebuild"
PYINSTALLER_BIN="${PYINSTALLER:-pyinstaller}"
BUILD_DIR="$ROOT_DIR/build"
FINAL_DIR="$BUILD_DIR/SpellGraphix"
FINAL_BACKUP="$BUILD_DIR/SpellGraphix.prev"
TEMP_DIST="$BUILD_DIR/.pyi-dist"
TEMP_WORK="$BUILD_DIR/.pyi-work"

log() {
  echo "[build-linux] $*"
}

restore_database() {
  if [[ -f "$DB_BACKUP" ]]; then
    log "Restoring original database"
    mv -f "$DB_BACKUP" "$DB_PATH"
  fi
}

cleanup_artifacts() {
  log "Removing temporary build artifacts"
  rm -rf "$TEMP_DIST" "$TEMP_WORK" "$ROOT_DIR/dist"
  find "$ROOT_DIR" -path "$ROOT_DIR/.venv" -prune -o -name "__pycache__" -type d -print0 | xargs -0 rm -rf || true
}

cleanup() {
  local status=$?
  set +e
  if [[ $status -ne 0 && -e "$FINAL_BACKUP" ]]; then
    log "Build failed; restoring previous artifact"
    rm -rf "$FINAL_DIR"
    mv "$FINAL_BACKUP" "$FINAL_DIR"
  fi
  if [[ $status -eq 0 ]]; then
    rm -rf "$FINAL_BACKUP"
  fi
  restore_database
  cleanup_artifacts
  exit $status
}

trap cleanup EXIT

cd "$ROOT_DIR"

if ! command -v "$PYINSTALLER_BIN" >/dev/null 2>&1; then
  echo "pyinstaller is required but was not found in PATH" >&2
  exit 1
fi

mkdir -p "$BUILD_DIR"
rm -rf "$TEMP_DIST" "$TEMP_WORK"

if [[ -e "$FINAL_DIR" ]]; then
  log "Backing up previous build artifact"
  rm -rf "$FINAL_BACKUP"
  mv "$FINAL_DIR" "$FINAL_BACKUP"
fi

log "Preparing empty database"
if [[ -f "$DB_PATH" ]]; then
  cp "$DB_PATH" "$DB_BACKUP"
  rm -f "$DB_PATH"
fi

log "Running PyInstaller"
"$PYINSTALLER_BIN" \
  --clean --noconfirm \
  --distpath "$TEMP_DIST" \
  --workpath "$TEMP_WORK" \
  SpellGraphix.spec

ARTIFACT_SOURCE="$TEMP_DIST/SpellGraphix"
if [[ ! -e "$ARTIFACT_SOURCE" ]]; then
  echo "PyInstaller output not found at $ARTIFACT_SOURCE" >&2
  exit 1
fi

rm -rf "$FINAL_DIR"
if [[ -d "$ARTIFACT_SOURCE" ]]; then
  mv "$ARTIFACT_SOURCE" "$FINAL_DIR"
else
  mkdir -p "$FINAL_DIR"
  mv "$ARTIFACT_SOURCE" "$FINAL_DIR/"
fi
rm -rf "$FINAL_BACKUP"

log "Build completed. Artifact available in $FINAL_DIR"
