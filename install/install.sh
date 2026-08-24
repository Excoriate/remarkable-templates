#!/usr/bin/env bash
#
# Install this repository's templates onto a reMarkable tablet over SSH.
#
# Two things make this safe to re-run and survivable across firmware updates:
#
#   1. The image files live under /home/root, which the updater leaves alone,
#      and /usr/share/remarkable/templates gets a symlink pointing at them. A
#      firmware update wipes the symlink, not the artwork; re-running with
#      --relink puts the link back without copying anything.
#
#   2. templates.json is never overwritten blind. It is copied to the host,
#      merged there, and written back, and the original is kept on the device
#      before anything changes.
#
# Every directory under templates/ that holds a manifest.json is one set, and
# every set is installed unless --only names a subset. What will be installed is
# printed before anything is touched.
#
# Usage:  install/install.sh [--host HOST] [--only a,b] [--svg] [--relink]
#                            [--dry-run] [--yes]
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BUILD_ROOT="${REPO}/templates"
HOST="${RM_HOST:-10.11.99.1}"
SSH_OPTS=(-o ConnectTimeout=8 -o StrictHostKeyChecking=accept-new)

DEVICE_TEMPLATES=/usr/share/remarkable/templates
PERSIST_ROOT=/home/root/.local/share/remarkable/templates

ONLY=""
WITH_SVG=0
RELINK_ONLY=0
DRY_RUN=0
ASSUME_YES=0

die() { printf '\nerror: %s\n' "$*" >&2; exit 1; }
say() { printf '%s\n' "$*"; }

while [[ $# -gt 0 ]]; do
  case "$1" in
    --host) HOST="$2"; shift 2 ;;
    --only) ONLY="$2"; shift 2 ;;
    --svg) WITH_SVG=1; shift ;;
    --relink) RELINK_ONLY=1; shift ;;
    --dry-run) DRY_RUN=1; shift ;;
    --yes|-y) ASSUME_YES=1; shift ;;
    -h|--help) sed -n '2,21p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) die "unknown argument: $1" ;;
  esac
done

rsh() { ssh "${SSH_OPTS[@]}" "root@${HOST}" "$@"; }
wanted() {
  [[ -z "$ONLY" ]] && return 0
  [[ ",${ONLY}," == *",$1,"* ]]
}

# --------------------------------------------------------------------------- #
# Work out exactly what will change, and say so before touching anything.
# --------------------------------------------------------------------------- #
NAMESPACES=()
MANIFESTS=()
for m in "${BUILD_ROOT}"/*/manifest.json; do
  [[ -f "$m" ]] || continue
  ns="$(basename "$(dirname "$m")")"
  wanted "$ns" || continue
  # A namespace becomes a directory name on the tablet and a bare word inside a
  # command run over SSH. Anything outside this set is refused rather than
  # quoted around, because quoting a name that should never have existed just
  # moves the problem.
  [[ "$ns" =~ ^[a-z0-9][a-z0-9-]*$ ]] \
    || die "set name ${ns} must be lower-case letters, digits and hyphens"
  NAMESPACES+=("$ns")
  MANIFESTS+=("$m")
done
[[ ${#NAMESPACES[@]} -gt 0 ]] || die "nothing to install under ${BUILD_ROOT}.
build first:  just build                       (every family)
              just ingest <folder> <namespace> (your own PNGs)"

STEMS=()   # "<namespace>/<stem>", exactly as the manifest writes it
for m in "${MANIFESTS[@]}"; do
  while IFS= read -r name; do
    [[ "$name" =~ ^[a-z0-9][a-z0-9-]*/[a-z0-9][a-z0-9-]*$ ]] \
      || die "manifest ${m} lists an unusable template name: ${name}"
    STEMS+=("$name")
  done < <(python3 -c '
import json, sys
from pathlib import Path
for t in json.loads(Path(sys.argv[1]).read_text())["templates"]:
    print(t["filename"])' "$m")
done
[[ ${#STEMS[@]} -gt 0 ]] || die "the manifests list no templates"

say "reMarkable template install"
say "  device            root@${HOST}"
say "  sets              ${NAMESPACES[*]}"
say "  templates         ${#STEMS[@]}"
say "  artwork goes to   ${PERSIST_ROOT}/<set>/   (survives firmware updates)"
say "  symlinked into    ${DEVICE_TEMPLATES}/<set>   (an existing symlink there"
say "                    is replaced; a real directory of that name is not"
say "                    touched and the install stops instead)"
say "  modified in place ${DEVICE_TEMPLATES}/templates.json"
say "                    backed up on the device before anything else changes;"
say "                    entries outside the sets above are preserved byte for"
say "                    byte"
say "  remounts          / read-write for the duration, and back to read-only"
say "                    before finishing"
say "  then              systemctl restart xochitl"
[[ $RELINK_ONLY -eq 1 ]] && say "  --relink          skipping the copy: re-link and re-register only"
say ""

if [[ $DRY_RUN -eq 1 ]]; then
  say "dry run: nothing was changed."
  exit 0
fi
if [[ $ASSUME_YES -ne 1 ]]; then
  read -r -p "Proceed? [y/N] " reply
  [[ "$reply" =~ ^[Yy]$ ]] || { say "aborted"; exit 1; }
fi

rsh true >/dev/null 2>&1 || die "cannot reach root@${HOST} over SSH.
Connect the tablet by USB (host 10.11.99.1), or set RM_HOST to its WiFi address.
The root password is in Settings > General > Help > Copyrights and licenses."

say "connected. device build: $(rsh 'cat /etc/version 2>/dev/null || echo unknown')"
rsh "mkdir -p ${PERSIST_ROOT}"
STAMP="$(date +%Y%m%d-%H%M%S)"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

# The system partition is mounted read-only by design. Put it back that way on
# every exit path, including a failure, so a later power loss cannot catch it
# writable.
REMOUNTED_RW=0
restore_ro() {
  [[ $REMOUNTED_RW -eq 1 ]] || return 0
  REMOUNTED_RW=0
  ssh "${SSH_OPTS[@]}" "root@${HOST}" "mount -o remount,ro / 2>/dev/null" || true
}
trap 'restore_ro; rm -rf "$WORK"' EXIT

# 0. back up templates.json BEFORE anything is changed. A backup taken after
#    the first destructive step is not a rollback.
rsh "test -f ${PERSIST_ROOT}/templates.json.orig || cp ${DEVICE_TEMPLATES}/templates.json ${PERSIST_ROOT}/templates.json.orig" \
  || die "could not create the pristine backup; nothing has been changed"
rsh "cp ${DEVICE_TEMPLATES}/templates.json ${PERSIST_ROOT}/templates.json.${STAMP}.bak" \
  || die "could not back up templates.json; nothing has been changed"
scp "${SSH_OPTS[@]}" -q "root@${HOST}:${DEVICE_TEMPLATES}/templates.json" "${WORK}/device.json" \
  || die "could not read templates.json from the device; nothing has been changed"
# How many entries the device owns, i.e. everything not under one of our set
# names. This, not the total, is what verification compares against afterwards.
BEFORE_FOREIGN=$(python3 -c '
import json, sys
from pathlib import Path
entries = json.loads(Path(sys.argv[1]).read_text())["templates"]
ours = set(sys.argv[2:])
print(sum(1 for t in entries if str(t.get("filename", "")).split("/")[0] not in ours))
' "${WORK}/device.json" "${NAMESPACES[@]}")
BEFORE=$(python3 -c 'import json,sys;print(len(json.load(open(sys.argv[1]))["templates"]))' "${WORK}/device.json")
say "backed up templates.json (${BEFORE} entries, ${BEFORE_FOREIGN} the device\047s own) to ${PERSIST_ROOT}/templates.json.${STAMP}.bak"

# 1. artwork -> persistent storage
if [[ $RELINK_ONLY -ne 1 ]]; then
  for ns in "${NAMESPACES[@]}"; do rsh "mkdir -p ${PERSIST_ROOT}/${ns}"; done
  for row in "${STEMS[@]}"; do
    ns="${row%% *}"; stem="${row#* }"
    src="${BUILD_ROOT}/${ns}/png/${stem}.png"
    [[ -f "$src" ]] || die "built template missing: ${src}"
    scp "${SSH_OPTS[@]}" -q "$src" "root@${HOST}:${PERSIST_ROOT}/${ns}/${stem}.png"
    if [[ $WITH_SVG -eq 1 && -f "${BUILD_ROOT}/${ns}/svg/${stem}.svg" ]]; then
      scp "${SSH_OPTS[@]}" -q "${BUILD_ROOT}/${ns}/svg/${stem}.svg" \
        "root@${HOST}:${PERSIST_ROOT}/${ns}/${stem}.svg"
    fi
  done
  say "copied ${#STEMS[@]} template file(s)"
fi

# 2. link the sets in. An existing symlink is ours to replace; a real
#    directory belongs to something else and is left alone.
for ns in "${NAMESPACES[@]}"; do
  kind=$(rsh "if [ -L ${DEVICE_TEMPLATES}/${ns} ]; then echo symlink; elif [ -e ${DEVICE_TEMPLATES}/${ns} ]; then echo other; else echo absent; fi")
  [[ "$kind" != "other" ]] || die "${DEVICE_TEMPLATES}/${ns} exists on the tablet
and is not a symlink this tool created. Something else owns that name. Move it
aside yourself, or build this set under a different name. Nothing has been
changed."
done

rsh "mount -o remount,rw /" || die "could not remount / read-write"
REMOUNTED_RW=1
for ns in "${NAMESPACES[@]}"; do
  rsh "rm -f ${DEVICE_TEMPLATES}/${ns} && ln -s ${PERSIST_ROOT}/${ns} ${DEVICE_TEMPLATES}/${ns}"
done
say "linked ${DEVICE_TEMPLATES}/{${NAMESPACES[*]}} -> ${PERSIST_ROOT}"

# 3. templates.json: merge on the host, write back
python3 "${REPO}/install/lib/merge_templates_json.py" \
  "${WORK}/device.json" "${MANIFESTS[@]}" -o "${WORK}/merged.json"
scp "${SSH_OPTS[@]}" -q "${WORK}/merged.json" "root@${HOST}:${DEVICE_TEMPLATES}/templates.json"

# 4. verify against the device's own copy, not the file we just uploaded
scp "${SSH_OPTS[@]}" -q "root@${HOST}:${DEVICE_TEMPLATES}/templates.json" "${WORK}/verify.json"
python3 "${REPO}/install/lib/verify_install.py" "${WORK}/verify.json" "${BEFORE_FOREIGN}" \
  "${MANIFESTS[@]}" || die "verification failed. The device's previous
templates.json is at ${PERSIST_ROOT}/templates.json.${STAMP}.bak and the
pristine one at ${PERSIST_ROOT}/templates.json.orig"

# 5. every listed template must resolve to a file readable through the symlink
NAMES="${STEMS[*]}"
MISSING=$(rsh "cd ${DEVICE_TEMPLATES} && for f in ${NAMES}; do test -r \"\$f.png\" || test -r \"\$f.svg\" || echo \"\$f\"; done")
[[ -z "$MISSING" ]] || die "listed but not readable on the device:
${MISSING}"
say "verified: every listed template resolves to a readable file"

restore_ro
say "remounted / read-only"
rsh "systemctl restart xochitl"
say ""
say "done. The tablet's UI restarts. Open a notebook, tap the page menu,"
say "choose a template, and look for the new tab."
