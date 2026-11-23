#!/usr/bin/env bash
#
# Update the Impeccable design skill from upstream.
#
# What it does:
#   1. Clones the latest pbakaus/impeccable (sparse, .opencode/ only)
#   2. Replaces reference/, scripts/ wholesale
#   3. Replaces SKILL.md, then re-appends the workspace-integration fragment
#   4. Rewrites all .opencode/skills/impeccable/ paths → .agents/skills/impeccable/
#   5. Patches pin.mjs to discover impeccable inside category subdirectories
#
# Usage:
#   .opencode/scripts/update-impeccable.sh [--dry-run]
#
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
SKILL_DIR="$REPO_ROOT/packs/design/skills/impeccable"
WORKSPACE_FRAGMENT="$SKILL_DIR/.workspace-integration.md"
UPSTREAM_REPO="https://github.com/pbakaus/impeccable.git"
UPSTREAM_PATH=".opencode/skills/impeccable"

DRY_RUN=false
if [[ "${1:-}" == "--dry-run" ]]; then
  DRY_RUN=true
fi

log() { echo "==> $*"; }
die() { echo "ERROR: $*" >&2; exit 1; }

# --- Preflight checks ---

[[ -d "$SKILL_DIR" ]] || die "Skill directory not found: $SKILL_DIR"
[[ -f "$WORKSPACE_FRAGMENT" ]] || die "Workspace fragment not found: $WORKSPACE_FRAGMENT"

# --- Clone upstream into temp directory ---

TMPDIR="$(mktemp -d)"
trap 'rm -rf "$TMPDIR"' EXIT

log "Cloning latest upstream..."
git clone --depth 1 --filter=blob:none --sparse "$UPSTREAM_REPO" "$TMPDIR/impeccable" 2>&1 | tail -1
cd "$TMPDIR/impeccable"
git sparse-checkout set .opencode 2>/dev/null

UPSTREAM_DIR="$TMPDIR/impeccable/$UPSTREAM_PATH"
[[ -d "$UPSTREAM_DIR" ]] || die "Upstream path not found after clone: $UPSTREAM_PATH"

# Grab upstream version from frontmatter
UPSTREAM_VERSION=$(grep -m1 '^version:' "$UPSTREAM_DIR/SKILL.md" | sed 's/version: *//' || echo "unknown")
log "Upstream version: $UPSTREAM_VERSION"

if $DRY_RUN; then
  # Show what would change
  CURRENT_VERSION=$(grep -m1 '^version:' "$SKILL_DIR/SKILL.md" | sed 's/version: *//' || echo "unknown")
  log "Current version: $CURRENT_VERSION"
  log "[dry-run] Would replace reference/ ($(find "$UPSTREAM_DIR/reference" -type f | wc -l | tr -d ' ') files)"
  log "[dry-run] Would replace scripts/ ($(find "$UPSTREAM_DIR/scripts" -type f | wc -l | tr -d ' ') files)"
  log "[dry-run] Would replace SKILL.md + append workspace fragment"
  log "[dry-run] Would fix paths and patch pin.mjs"
  exit 0
fi

# --- Replace files ---

log "Replacing reference/..."
rm -rf "$SKILL_DIR/reference"
cp -R "$UPSTREAM_DIR/reference" "$SKILL_DIR/reference"

log "Replacing scripts/..."
rm -rf "$SKILL_DIR/scripts"
cp -R "$UPSTREAM_DIR/scripts" "$SKILL_DIR/scripts"

log "Replacing SKILL.md and appending workspace fragment..."
cp "$UPSTREAM_DIR/SKILL.md" "$SKILL_DIR/SKILL.md"
cat "$WORKSPACE_FRAGMENT" >> "$SKILL_DIR/SKILL.md"

# --- Fix paths for the flat skills layout ---

log "Fixing paths (.opencode/skills/impeccable/ → .agents/skills/impeccable/)..."
find "$SKILL_DIR" -name "*.md" -exec \
  sed -i '' 's|\.opencode/skills/impeccable/|.agents/skills/impeccable/|g' {} +

# --- Patch pin.mjs for category-aware discovery ---

PIN_SCRIPT="$SKILL_DIR/scripts/pin.mjs"
PIN_PATCH="$SKILL_DIR/.pin-patch.js"
if [[ -f "$PIN_SCRIPT" ]] && [[ -f "$PIN_PATCH" ]]; then
  if ! grep -q "category nesting" "$PIN_SCRIPT"; then
    log "Patching pin.mjs for category-aware harness discovery..."
    # Find the line range of the original findHarnessDirs function and replace it
    # with the patched version from .pin-patch.js
    START=$(grep -n 'function findHarnessDirs' "$PIN_SCRIPT" | head -1 | cut -d: -f1)
    if [[ -n "$START" ]]; then
      # Find the closing brace: first line after START that is exactly "}"
      END=$(tail -n +"$START" "$PIN_SCRIPT" | grep -n '^}$' | head -1 | cut -d: -f1)
      END=$((START + END - 1))
      # Build new file: lines before function + patch + lines after function
      {
        head -n $((START - 1)) "$PIN_SCRIPT"
        cat "$PIN_PATCH"
        tail -n +$((END + 1)) "$PIN_SCRIPT"
      } > "$PIN_SCRIPT.tmp"
      mv "$PIN_SCRIPT.tmp" "$PIN_SCRIPT"
      log "pin.mjs patched (replaced lines ${START}-${END})."
    else
      log "WARNING: Could not find findHarnessDirs in pin.mjs — skipping patch."
    fi
  else
    log "pin.mjs already patched, skipping."
  fi
fi

# --- Summary ---

FINAL_VERSION=$(grep -m1 '^version:' "$SKILL_DIR/SKILL.md" | sed 's/version: *//' || echo "unknown")
FILE_COUNT=$(find "$SKILL_DIR" -type f | wc -l | tr -d ' ')

log "Done. Impeccable updated to v${FINAL_VERSION} (${FILE_COUNT} files)."
log ""
log "Next steps:"
log "  git diff --stat packs/design/skills/impeccable/"
log "  git add packs/design/skills/impeccable/ && git commit -m 'Update Impeccable to v${FINAL_VERSION}'"
