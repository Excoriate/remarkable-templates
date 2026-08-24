#!/usr/bin/env bash
#
# Configure the GitHub repository and push main.
#
# Run this from a machine with an authenticated `gh` CLI. Every step prints what
# it is doing and is safe to re-run: the script sets state rather than toggling
# it, so a second run is a no-op that confirms the first.
#
# Usage:
#   scripts/setup-github.sh [--repo OWNER/NAME] [--remote URL]
#                           [--strict] [--no-push] [--dry-run]
#
#   --strict    branch protection also applies to admins and requires one
#               approving review. Correct for a team; it locks a solo
#               maintainer out of pushing to main, so it is not the default.
#   --no-push   configure only, do not push.
#   --dry-run   print every command instead of running it.
set -euo pipefail

REPO_SLUG="${GH_REPO:-Excoriate/remarkable-templates}"
REMOTE_URL=""
STRICT=0
DO_PUSH=1
DRY_RUN=0
BRANCH=main
CHECK_NAME=build      # the job name in .github/workflows/build.yml

die() { printf '\nerror: %s\n' "$*" >&2; exit 1; }
say() { printf '%s\n' "$*"; }
step() { printf '\n== %s\n' "$*"; }

run() {
  if [[ $DRY_RUN -eq 1 ]]; then
    printf '   would run: %s\n' "$*"
  else
    "$@"
  fi
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --repo) REPO_SLUG="$2"; shift 2 ;;
    --remote) REMOTE_URL="$2"; shift 2 ;;
    --strict) STRICT=1; shift ;;
    --no-push) DO_PUSH=0; shift ;;
    --dry-run) DRY_RUN=1; shift ;;
    -h|--help) sed -n '2,17p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) die "unknown argument: $1" ;;
  esac
done

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"
: "${REMOTE_URL:=git@github.com:${REPO_SLUG}.git}"

command -v gh >/dev/null || die "gh is not installed: https://cli.github.com"
gh auth status >/dev/null 2>&1 || die "gh is not authenticated. Run: gh auth login"

say "repository   ${REPO_SLUG}"
say "remote       ${REMOTE_URL}"
say "branch       ${BRANCH}"
say "protection   $([[ $STRICT -eq 1 ]] && echo 'strict (admins included, 1 review)' || echo 'solo maintainer (admins exempt, 0 reviews)')"
[[ $DRY_RUN -eq 1 ]] && say "MODE         dry run — nothing will be changed"

gh api "repos/${REPO_SLUG}" --silent 2>/dev/null \
  || die "cannot see ${REPO_SLUG} with this gh account. Check the slug and that you are logged in as its owner."

# --------------------------------------------------------------------------- #
step "remote and push"
if git remote get-url origin >/dev/null 2>&1; then
  current="$(git remote get-url origin)"
  [[ "$current" == "$REMOTE_URL" ]] || run git remote set-url origin "$REMOTE_URL"
else
  run git remote add origin "$REMOTE_URL"
fi
say "   origin -> ${REMOTE_URL}"

if [[ $DO_PUSH -eq 1 ]]; then
  [[ -z "$(git status --porcelain)" ]] || die "working tree is dirty; commit or stash first"
  run git push -u origin "$BRANCH"
  say "   pushed ${BRANCH}"
else
  say "   --no-push: skipped"
fi

# --------------------------------------------------------------------------- #
step "repository metadata"
run gh repo edit "$REPO_SLUG" \
  --description "A toolkit for building reMarkable paper templates, and the template families built with it" \
  --homepage "https://github.com/${REPO_SLUG}#readme" \
  --add-topic remarkable \
  --add-topic remarkable-tablet \
  --add-topic remarkable-paper-pro \
  --add-topic e-ink \
  --add-topic templates \
  --add-topic basketball \
  --add-topic coaching \
  --add-topic python \
  --enable-issues \
  --enable-wiki=false \
  --enable-projects=false \
  --delete-branch-on-merge \
  --allow-update-branch
say "   description, homepage, topics, merge hygiene"

# --------------------------------------------------------------------------- #
step "security"
# Public repositories get secret scanning and push protection at no cost.
# Dependabot alerts need the vulnerability-alerts endpoint, which has no
# equivalent field on the repo object.
run gh api -X PATCH "repos/${REPO_SLUG}" \
  -f 'security_and_analysis[secret_scanning][status]=enabled' \
  -f 'security_and_analysis[secret_scanning][push_protection][status]=enabled' \
  --silent
say "   secret scanning + push protection"

run gh api -X PUT "repos/${REPO_SLUG}/vulnerability-alerts" --silent
say "   Dependabot vulnerability alerts"

run gh api -X PUT "repos/${REPO_SLUG}/automated-security-fixes" --silent
say "   Dependabot security updates"

# Workflows in this repository declare `permissions: contents: read` and check
# out without persisting credentials, so the default token can stay read-only.
run gh api -X PUT "repos/${REPO_SLUG}/actions/permissions/workflow" \
  -f default_workflow_permissions=read \
  -F can_approve_pull_request_reviews=false \
  --silent
say "   GITHUB_TOKEN defaults to read-only"

# --------------------------------------------------------------------------- #
step "branch protection on ${BRANCH}"
REVIEWS=0
ADMINS=false
if [[ $STRICT -eq 1 ]]; then REVIEWS=1; ADMINS=true; fi

PROTECTION=$(cat <<JSON
{
  "required_status_checks": {
    "strict": true,
    "contexts": ["${CHECK_NAME}"]
  },
  "enforce_admins": ${ADMINS},
  "required_pull_request_reviews": {
    "dismiss_stale_reviews": true,
    "require_code_owner_reviews": false,
    "required_approving_review_count": ${REVIEWS}
  },
  "restrictions": null,
  "required_linear_history": true,
  "allow_force_pushes": false,
  "allow_deletions": false,
  "block_creations": false,
  "required_conversation_resolution": true
}
JSON
)

if [[ $DRY_RUN -eq 1 ]]; then
  printf '   would PUT repos/%s/branches/%s/protection:\n%s\n' \
    "$REPO_SLUG" "$BRANCH" "$PROTECTION"
else
  printf '%s' "$PROTECTION" | gh api -X PUT \
    "repos/${REPO_SLUG}/branches/${BRANCH}/protection" \
    -H "Accept: application/vnd.github+json" --input - --silent
fi
say "   pull request required, '${CHECK_NAME}' must pass and be up to date"
say "   linear history, no force pushes, no branch deletion"
say "   conversations must be resolved"
say "   admins exempt: $([[ $ADMINS == true ]] && echo no || echo yes)"

# --------------------------------------------------------------------------- #
step "verify, by reading the settings back"
if [[ $DRY_RUN -eq 1 ]]; then
  say "   dry run: nothing to verify"
  exit 0
fi
gh api "repos/${REPO_SLUG}" --jq '
  "   visibility            \(.visibility)",
  "   default branch        \(.default_branch)",
  "   secret scanning       \(.security_and_analysis.secret_scanning.status)",
  "   push protection       \(.security_and_analysis.secret_scanning_push_protection.status)",
  "   delete branch on merge \(.delete_branch_on_merge)"'
gh api "repos/${REPO_SLUG}/branches/${BRANCH}/protection" --jq '
  "   required checks       \(.required_status_checks.contexts | join(", "))",
  "   strict checks         \(.required_status_checks.strict)",
  "   linear history        \(.required_linear_history.enabled)",
  "   force pushes          \(.allow_force_pushes.enabled)",
  "   deletions             \(.allow_deletions.enabled)",
  "   enforce admins        \(.enforce_admins.enabled)"'

say ""
say "done. https://github.com/${REPO_SLUG}"
