# Local versioning and rollback

OpenWorker customizations live on `local/*` branches. Upstream's `main` branch remains the
clean reference point for future updates.

## Version format

- App version: standard semantic version in `surfaces/gui/src-tauri/tauri.conf.json`.
- Local checkpoint tag: `local-vX.Y.Z`.
- Portable backup: `openworker-local-vX.Y.Z.bundle`.

Each checkpoint must be tested, committed, tagged, and exported as a Git bundle. The bundle
contains the repository history and remains usable even if the working repository is damaged.

## Create a checkpoint

The working tree must be clean:

```sh
./scripts/create_local_checkpoint.sh 0.1.8 "Describe the stable change"
```

The script creates an annotated `local-v0.1.8` tag and a bundle in the sibling
`openworker-version-backups` directory. Keep that directory in a backed-up location.

## Safe rollback

Do not erase the current branch. Create a recovery branch from the desired checkpoint:

```sh
git switch -c restore/local-v0.1.7 local-v0.1.7
```

Build and test that branch. Return without losing later work:

```sh
git switch local/openworker-0.1.7
```

## Restore from a bundle

If the repository itself is unavailable:

```sh
git clone openworker-local-v0.1.7.bundle openworker-restored
cd openworker-restored
git switch -c restore/local-v0.1.7 local-v0.1.7
```

Never use `git reset --hard` for routine rollback. Recovery branches preserve both the old
checkpoint and all newer work.
