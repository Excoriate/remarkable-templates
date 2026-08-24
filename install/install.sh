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
# Usage:  install/install.sh [--host HOST] [--svg] [--legacy] [--relink]
#                            [--dry-run] [--yes]
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HOST="${RM_HOST:-10.11.99.1}"
SSH_OPTS=(-o ConnectTimeout=8 -o StrictHostKeyChecking=accept-new)

DEVICE_TEMPLATES=/usr/share/remarkable/templates
PERSIST_ROOT=/home/root/.local/share/remarkable/templates

# A build root and the namespace it owns, kept as parallel arrays so a set can
# be added without the script caring where it was built.
ROOTS=("${REPO}/templates")
NAMESPACES=(basketball)

WITH_SVG=0
RELINK_ONLY=0
DRY_RUN=0
ASSUME_YES=0

die() { printf '\nerror: %s\n' "$*" >&2; exit 1; }
say() { printf '%s\n' "$*"; }

while [[ $# -gt 0 ]]; do
  case "$1" in
    --host) HOST="$2"; shift 2 ;;
    --svg) WITH_SVG=1; shift ;;
    --legacy) ROOTS+=("${REPO}/templates-legacy"); NAMESPACES+=(legacy); shift ;;
    --relink) RELINK_ONLY=1; shift ;;
    --dry-run) DRY_RUN=1; shift ;;
    --yes|-y) ASSUME_YES=1; shift ;;
    -h|--help) sed -n '2,18p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) die "unknown argument: $1" ;;
  esac
done

rsh() { ssh "${SSH_OPTS[@]}" "root@${HOST}" "$@"; }

# --------------------------------------------------------------------------- #
# Work out exactly what will change, and say so before touching anything.
# --------------------------------------------------------------------------- #
FRAGMENTS=()
STEMS=()      # "<index> <namespace>/<stem>", index into ROOTS
for i in "${!NAMESPACES[@]}"; do
  ns="${NAMESPACES[$i]}"
  frag="${ROOTS[$i]}/templates.d/${ns}.json"
  [[ -f "$frag" ]] || die "missing manifest fragment: ${frag}
build it first:  just build          (court templates)
                 just legacy <folder-of-pngs>   (the legacy set)"
  FRAGMENTS+=("$frag")
  while IFS= read -r name; do
    STEMS+=("${i} ${name}")
  done < <(python3 -c '
import json, sys
from pathlib import Path
for t in json.loads(Path(sys.argv[1]).read_text())["templates"]:
    print(t["filename"])' "$frag")
done
[[ ${#STEMS[@]} -gt 0 ]] || die "the manifest fragments list no templates"

say "reMarkable template install"
say "  device            root@${HOST}"
say "  templates         ${#STEMS[@]} across namespaces: ${NAMESPACES[*]}"
say "  artwork goes to   ${PERSIST_ROOT}/<namespace>/   (survives firmware updates)"
say "  symlinked into    ${DEVICE_TEMPLATES}/<namespace>"
say "  modified in place ${DEVICE_TEMPLATES}/templates.json"
say "                    backed up on the device first; entries outside the"
say "                    namespaces above are preserved byte for byte"
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

# 1. artwork -> persistent storage
if [[ $RELINK_ONLY -ne 1 ]]; then
  for ns in "${NAMESPACES[@]}"; do rsh "mkdir -p ${PERSIST_ROOT}/${ns}"; done
  for row in "${STEMS[@]}"; do
    idx="${row%% *}"; name="${row#* }"
    ns="${name%%/*}"; stem="${name##*/}"
    src="${ROOTS[$idx]}/png/${stem}.png"
    [[ -f "$src" ]] || die "built template missing: ${src}"
    scp "${SSH_OPTS[@]}" -q "$src" "root@${HOST}:${PERSIST_ROOT}/${ns}/${stem}.png"
    if [[ $WITH_SVG -eq 1 && -f "${ROOTS[$idx]}/svg/${stem}.svg" ]]; then
      scp "${SSH_OPTS[@]}" -q "${ROOTS[$idx]}/svg/${stem}.svg" \
        "root@${HOST}:${PERSIST_ROOT}/${ns}/${stem}.svg"
    fi
  done
  say "copied ${#STEMS[@]} template file(s)"
fi

# 2. make the system partition writable and link the namespaces in
rsh "mount -o remount,rw /"
for ns in "${NAMESPACES[@]}"; do
  rsh "rm -rf ${DEVICE_TEMPLATES}/${ns} && ln -s ${PERSIST_ROOT}/${ns} ${DEVICE_TEMPLATES}/${ns}"
done
say "linked ${DEVICE_TEMPLATES}/{${NAMESPACES[*]}} -> ${PERSIST_ROOT}"

# 3. templates.json: back up, fetch, merge on the host, write back
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT
rsh "test -f ${PERSIST_ROOT}/templates.json.orig || cp ${DEVICE_TEMPLATES}/templates.json ${PERSIST_ROOT}/templates.json.orig"
rsh "cp ${DEVICE_TEMPLATES}/templates.json ${PERSIST_ROOT}/templates.json.${STAMP}.bak"
scp "${SSH_OPTS[@]}" -q "root@${HOST}:${DEVICE_TEMPLATES}/templates.json" "${WORK}/device.json"
BEFORE=$(python3 -c 'import json,sys;print(len(json.load(open(sys.argv[1]))["templates"]))' "${WORK}/device.json")

python3 "${REPO}/install/lib/merge_templates_json.py" \
  "${WORK}/device.json" "${FRAGMENTS[@]}" -o "${WORK}/merged.json"
scp "${SSH_OPTS[@]}" -q "${WORK}/merged.json" "root@${HOST}:${DEVICE_TEMPLATES}/templates.json"
say "backed up templates.json to ${PERSIST_ROOT}/templates.json.${STAMP}.bak"

# 4. verify against the device's own copy, not the file we just uploaded
scp "${SSH_OPTS[@]}" -q "root@${HOST}:${DEVICE_TEMPLATES}/templates.json" "${WORK}/verify.json"
python3 "${REPO}/install/lib/verify_install.py" "${WORK}/verify.json" "${BEFORE}" \
  "${FRAGMENTS[@]}" || die "verification failed. The device's previous
templates.json is at ${PERSIST_ROOT}/templates.json.${STAMP}.bak and the
pristine one at ${PERSIST_ROOT}/templates.json.orig"

# 5. every listed template must resolve to a file readable through the symlink
NAMES=$(printf '%s\n' "${STEMS[@]}" | cut -d' ' -f2- | tr '\n' ' ')
MISSING=$(rsh "cd ${DEVICE_TEMPLATES} && for f in ${NAMES}; do test -r \"\$f.png\" || test -r \"\$f.svg\" || echo \"\$f\"; done")
[[ -z "$MISSING" ]] || die "listed but not readable on the device:
${MISSING}"
say "verified: every listed template resolves to a readable file"

rsh "systemctl restart xochitl"
say ""
say "done. The tablet's UI restarts. Open a notebook, tap the page menu,"
say "choose a template, and look under the '${NAMESPACES[0]^}' tab."
