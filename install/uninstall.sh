#!/usr/bin/env bash
#
# Remove this repository's templates from a reMarkable tablet.
#
# Only entries filed under our own set directories are touched; everything else
# in templates.json is preserved. Notebook pages that already use one of these
# templates keep pointing at it, so if you reinstall later under the same
# filenames the pages come back looking the way they did.
#
# Usage:  install/uninstall.sh [--host HOST] [--only a,b] [--purge] [--yes]
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BUILD_ROOT="${REPO}/templates"
HOST="${RM_HOST:-10.11.99.1}"
SSH_OPTS=(-o ConnectTimeout=8 -o StrictHostKeyChecking=accept-new)
DEVICE_TEMPLATES=/usr/share/remarkable/templates
PERSIST_ROOT=/home/root/.local/share/remarkable/templates

ONLY=""
PURGE=0
ASSUME_YES=0

die() { printf '\nerror: %s\n' "$*" >&2; exit 1; }
say() { printf '%s\n' "$*"; }

while [[ $# -gt 0 ]]; do
  case "$1" in
    --host) HOST="$2"; shift 2 ;;
    --only) ONLY="$2"; shift 2 ;;
    --purge) PURGE=1; shift ;;
    --yes|-y) ASSUME_YES=1; shift ;;
    -h|--help) sed -n '2,10p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) die "unknown argument: $1" ;;
  esac
done

rsh() { ssh "${SSH_OPTS[@]}" "root@${HOST}" "$@"; }
wanted() {
  [[ -z "$ONLY" ]] && return 0
  [[ ",${ONLY}," == *",$1,"* ]]
}

NAMESPACES=()
MANIFESTS=()
for m in "${BUILD_ROOT}"/*/manifest.json; do
  [[ -f "$m" ]] || continue
  ns="$(basename "$(dirname "$m")")"
  wanted "$ns" || continue
  [[ "$ns" =~ ^[a-z0-9][a-z0-9-]*$ ]] \
    || die "set name ${ns} must be lower-case letters, digits and hyphens"
  NAMESPACES+=("$ns")
  MANIFESTS+=("$m")
done
[[ ${#NAMESPACES[@]} -gt 0 ]] || die "no built sets under ${BUILD_ROOT}.
This script identifies what to remove from the manifests in your checkout, so
there has to be a build to read. Run 'just build' (the artwork is regenerated
from source, nothing is downloaded) and run this again. --only filters that
list; it cannot name a set that was never built."

say "reMarkable template uninstall"
say "  device        root@${HOST}"
say "  removing      templates.json entries under: ${NAMESPACES[*]}"
say "  removing      ${DEVICE_TEMPLATES}/{${NAMESPACES[*]}} (symlinks only)"
say "  remounts      / read-write, and back to read-only before finishing"
if [[ $PURGE -eq 1 ]]; then
  say "  --purge       also deletes the artwork under ${PERSIST_ROOT}"
else
  say "  keeping       the artwork under ${PERSIST_ROOT} (use --purge to delete)"
fi
say ""
if [[ $ASSUME_YES -ne 1 ]]; then
  read -r -p "Proceed? [y/N] " reply
  [[ "$reply" =~ ^[Yy]$ ]] || { say "aborted"; exit 1; }
fi

rsh true >/dev/null 2>&1 || die "cannot reach root@${HOST} over SSH"

WORK="$(mktemp -d)"
REMOUNTED_RW=0
restore_ro() {
  [[ $REMOUNTED_RW -eq 1 ]] || return 0
  REMOUNTED_RW=0
  ssh "${SSH_OPTS[@]}" "root@${HOST}" "mount -o remount,ro / 2>/dev/null" || true
}
trap 'restore_ro; rm -rf "$WORK"' EXIT
STAMP="$(date +%Y%m%d-%H%M%S)"

rsh "mkdir -p ${PERSIST_ROOT}" || die "cannot write to ${PERSIST_ROOT}"
# A failed backup is a reason to stop, not a reason to carry on unprotected.
rsh "cp ${DEVICE_TEMPLATES}/templates.json ${PERSIST_ROOT}/templates.json.${STAMP}.bak" \
  || die "could not back up templates.json; nothing has been changed"
scp "${SSH_OPTS[@]}" -q "root@${HOST}:${DEVICE_TEMPLATES}/templates.json" "${WORK}/device.json" \
  || die "could not read templates.json from the device; nothing has been changed"
say "backed up templates.json to ${PERSIST_ROOT}/templates.json.${STAMP}.bak"

python3 "${REPO}/install/lib/merge_templates_json.py" \
  "${WORK}/device.json" "${MANIFESTS[@]}" --remove-only -o "${WORK}/clean.json"

rsh "mount -o remount,rw /" || die "could not remount / read-write"
REMOUNTED_RW=1
scp "${SSH_OPTS[@]}" -q "${WORK}/clean.json" "root@${HOST}:${DEVICE_TEMPLATES}/templates.json"
for ns in "${NAMESPACES[@]}"; do
  # Only ever removes the symlink. If something replaced it with a real
  # directory, that is not ours to delete.
  rsh "[ -L ${DEVICE_TEMPLATES}/${ns} ] && rm -f ${DEVICE_TEMPLATES}/${ns} || true"
  if [[ $PURGE -eq 1 ]]; then rsh "rm -rf ${PERSIST_ROOT}/${ns}"; fi
done

scp "${SSH_OPTS[@]}" -q "root@${HOST}:${DEVICE_TEMPLATES}/templates.json" "${WORK}/verify.json"
python3 "${REPO}/install/lib/verify_uninstall.py" "${WORK}/verify.json" "${NAMESPACES[@]}" || die "verification failed"

restore_ro
say "remounted / read-only"
rsh "systemctl restart xochitl"
say "done."
