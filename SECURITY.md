# Security

## Reporting a vulnerability

Open a [private security advisory](https://github.com/Excoriate/remarkable-templates/security/advisories/new).
Please do not open a public issue for anything exploitable.

## What the risk surface actually is

This repository builds image files. Most of it cannot hurt you. Two parts can,
and both are worth reading before you run them.

**`install/install.sh` runs commands on your tablet as root.** It prints
exactly what it will change and asks before doing any of it; `--dry-run` prints
and stops. Four things change:

1. **Files are written** under `/home/root/.local/share/remarkable/templates/`.
   Additive; nothing there is removed unless you pass `--purge` to the
   uninstaller.
2. **`/` is remounted read-write**, and back to read-only before the script
   finishes — including when it fails, via a trap. reMarkable mounts the system
   partition read-only by design and leaving it writable across a power loss
   risks corrupting it.
3. **A symlink is created** at `/usr/share/remarkable/templates/<set>`. If a
   symlink is already there it is replaced. If a *real directory* has that
   name, something else owns it: the script stops and changes nothing.
4. **`templates.json` is rewritten.** This is the step that could cost you your
   stock templates, so it is the most guarded. Before anything else changes,
   the file is copied to a timestamped backup on the device and — on the first
   run only — to a pristine `templates.json.orig`. The merge happens on your
   machine, and refuses to produce a file at all if the device's own entries
   are not carried through byte for byte. After upload the file is read back
   *from the device* and the count of entries belonging to the device is
   compared with what it was beforehand. Both of those guards have tests that
   break the merge on purpose and confirm they fire.

Enabling developer mode on a reMarkable is itself a decision with consequences,
including a factory reset on a Paper Pro. That is reMarkable's behaviour, not
this project's, but it is the prerequisite for the SSH route.

Enabling developer mode on a reMarkable is itself a decision with consequences,
including a factory reset on a Paper Pro. That is reMarkable's behaviour, not
this project's, but it is the prerequisite for the SSH route.

**`just ingest` reads image files you point it at.** It uses Pillow. If you
feed it untrusted images, you inherit Pillow's decoder risk.

**Everything runs from your checkout.** The families are discovered inside the
installed `rmtpl` package, not from a top-level directory on `sys.path`, so a
stray folder in your working directory cannot be picked up and executed by
`python -m rmtpl`.

## What this project does not do

- It does not phone home, collect telemetry, or make network requests at build
  time.
- It does not ship third-party binaries or artwork.
- Its GitHub Actions workflow runs with `contents: read`, checks out without
  persisting credentials, and needs no secrets.

## Supported versions

`main` only. This is a small project; fixes land there.
