#!/bin/sh
set -eu

VERSION="${1:-}"
MESSAGE="${2:-}"

if [ -z "$VERSION" ] || [ -z "$MESSAGE" ]; then
  echo "Usage: $0 X.Y.Z \"checkpoint description\"" >&2
  exit 2
fi

case "$VERSION" in
  *[!0-9.]* | .* | *.) echo "Version must use X.Y.Z numeric form." >&2; exit 2 ;;
esac

TAG="local-v$VERSION"
if ! git diff --quiet || ! git diff --cached --quiet || [ -n "$(git status --porcelain --untracked-files=normal)" ]; then
  echo "The working tree must be clean before creating a checkpoint." >&2
  exit 1
fi
if git rev-parse -q --verify "refs/tags/$TAG" >/dev/null; then
  echo "Tag $TAG already exists." >&2
  exit 1
fi

REPO_ROOT="$(git rev-parse --show-toplevel)"
BACKUP_DIR="$(dirname "$REPO_ROOT")/openworker-version-backups"
mkdir -p "$BACKUP_DIR"

git tag -a "$TAG" -m "$MESSAGE"
git bundle create "$BACKUP_DIR/openworker-$TAG.bundle" --all

if git remote get-url origin >/dev/null 2>&1; then
  BRANCH="$(git branch --show-current)"
  git push -u origin "$BRANCH"
  git push origin "$TAG"
  echo "GitHub: synchronized $BRANCH and $TAG"
else
  echo "Warning: no origin remote; checkpoint was not synchronized to GitHub." >&2
fi

echo "Created $TAG"
echo "Bundle: $BACKUP_DIR/openworker-$TAG.bundle"
