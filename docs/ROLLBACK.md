# Local versioning and rollback

OpenWorker customizations live on `local/*` branches. Upstream's `main` branch remains the
clean reference point for future updates.

## Version format

- App version: standard semantic version in `surfaces/gui/src-tauri/tauri.conf.json`.
- Local checkpoint tag: `local-v<base>.<sequence>`; the current line uses tags such
  as `local-v0.1.7.65`.
- Installed-app backup: `/private/tmp/OpenWorker.before-local-v<base>.<sequence>.app`.
- Optional portable repository backup: `openworker-local-v<base>.<sequence>.bundle`.

Each installed-app release must be tested, committed, tagged, backed up, and pushed.
Portable Git bundles are recommended periodic backups and remain usable even if the
working repository or GitHub remote is unavailable.

## Create a checkpoint

The working tree must be clean:

For a documentation-only checkpoint, commit and push the branch normally. For an
installed app release, follow `skills/openworker-release-integrity/SKILL.md`: run all
gates, build the complete package, back up the installed app, verify checksums,
smoke-test the installed build, then create and push the next monotonic tag.

`scripts/create_local_checkpoint.sh` can still create an annotated tag and portable
Git bundle, but it does not replace the installed-app release gates.

## GitHub remotes and access

- `origin`: the owner's private repository (`rfrossard/openworker`), used for synchronization.
- `upstream`: the original public project (`andrewyng/openworker`), used only to inspect or
  fetch upstream releases.

Do not give collaborators write/admin access unless explicitly intended. On the current
GitHub Free personal plan, GitHub does not offer branch-protection rules for private
repositories; privacy plus an empty collaborator list is therefore the available access
boundary. Never replace `origin` with `upstream`.

## Safe rollback

Do not erase the current branch. Create a recovery branch from the desired checkpoint:

```sh
git switch -c restore/local-v0.1.7.65 local-v0.1.7.65
```

Build and test that branch. Return without losing later work:

```sh
git switch local/openworker-0.1.7
```

## Restore from a bundle

To restore the previously installed application, stop only the current OpenWorker
process, preserve it under another recovery name, and copy the version-specific app
backup back to `/Applications/OpenWorker.app`. Verify its checksum and relaunch it.
Do not delete the backup until the restored application has passed a smoke test.

If the repository itself is unavailable:

```sh
git clone openworker-local-v0.1.7.65.bundle openworker-restored
cd openworker-restored
git switch -c restore/local-v0.1.7.65 local-v0.1.7.65
```

Never use `git reset --hard` for routine rollback. Recovery branches preserve both the old
checkpoint and all newer work.
