# Security

## Reporting a vulnerability

Open a [private security advisory](https://github.com/Excoriate/remarkable-templates/security/advisories/new).
Please do not open a public issue for anything exploitable.

## What the risk surface actually is

This repository builds image files. Most of it cannot hurt you. Two parts can,
and both are worth reading before you run them.

**`install/install.sh` runs commands on your tablet as root.** It remounts `/`
read-write, writes into `/usr/share/remarkable/templates`, edits
`templates.json` and restarts xochitl. It prints exactly what it will change and
asks before doing any of it; `--dry-run` prints and stops. The one destructive
step — rewriting `templates.json` — takes a backup on the device first, keeps a
pristine `templates.json.orig` from the first run, and re-reads the file from
the device afterwards to verify. Entries outside this project's own namespace
directories are never touched.

Enabling developer mode on a reMarkable is itself a decision with consequences,
including a factory reset on a Paper Pro. That is reMarkable's behaviour, not
this project's, but it is the prerequisite for the SSH route.

**`just ingest` reads image files you point it at.** It uses Pillow. If you
feed it untrusted images, you inherit Pillow's decoder risk.

## What this project does not do

- It does not phone home, collect telemetry, or make network requests at build
  time.
- It does not ship third-party binaries or artwork.
- Its GitHub Actions workflow runs with `contents: read`, checks out without
  persisting credentials, and needs no secrets.

## Supported versions

`main` only. This is a small project; fixes land there.
