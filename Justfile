# remarkable-templates — build and install reMarkable paper templates.
#
#   just                 list the recipes
#   just setup           create .venv and install dependencies
#   just all             build everything and verify it
#   just install         copy the court templates onto a tablet over SSH
#
# Every recipe is a thin wrapper over `python -m rmtpl`, so nothing here is
# load-bearing: if you would rather not install `just`, read the recipe and run
# the command it shows.

set shell := ["bash", "-uc"]

venv    := justfile_directory() / ".venv"
python  := venv / "bin" / "python"
src     := justfile_directory() / "src"
out     := justfile_directory() / "templates"

# The device to build for: rmpp (Paper Pro), rm2, rmppm (Paper Pro Move).
device  := env_var_or_default("RM_DEVICE", "rmpp")

# Where `just install` looks for the tablet. 10.11.99.1 is the USB address.
host    := env_var_or_default("RM_HOST", "10.11.99.1")

export PYTHONPATH := src

_default:
    @just --list --unsorted

# Create the virtualenv and install dependencies.
setup:
    python3 -m venv {{venv}}
    {{python}} -m pip install --upgrade pip --quiet
    {{python}} -m pip install --quiet -e .[dev]
    @echo "ready. next: just all"

# Draw the court templates from the rule-book specs.
build:
    {{python}} -m rmtpl --device {{device}} --out {{out}} courts --clean

# Turn any folder of PNGs into templates: just ingest ~/art mine
ingest PNG_DIR NAMESPACE="imported" PREFIX="" STRIP="" FIT="fit":
    {{python}} -m rmtpl --device {{device}} --out {{out}} ingest "{{PNG_DIR}}" \
        --namespace "{{NAMESPACE}}" --prefix "{{PREFIX}}" --strip "{{STRIP}}" \
        --fit "{{FIT}}"

# The same pipeline over the original rM2-sized court PNGs (output git-ignored)
legacy PNG_DIR:
    {{python}} -m rmtpl --device {{device}} \
        --out {{justfile_directory()}}/templates-legacy ingest "{{PNG_DIR}}" \
        --namespace legacy --prefix "Legacy " --strip "rM-"

# Multi-page PDFs, for adding templates without developer mode.
bundle COPIES="1":
    {{python}} -m rmtpl --device {{device}} --out {{out}} bundle --copies {{COPIES}}

# Regenerate docs/court-geometry.md from the specs.
docs:
    {{python}} -m rmtpl docs

# Verify: rule-book cross-checks, file contract, geometry measured back out
check:
    {{python}} -m rmtpl --device {{device}} --out {{out}} doctor

# Validate the templates.json fragments on their own.
manifest:
    {{python}} -m rmtpl --out {{out}} manifest

# Run the test suite.
test:
    {{python}} -m pytest -q

# Lint Python and shell.
lint:
    {{python}} -m ruff check src tests tools install/lib
    shellcheck -S warning install/*.sh

# A contact sheet of every built template, for the README.
preview:
    {{python}} tools/contact_sheet.py {{out}}/png docs/images/contact-sheet.png

# Build, document and verify, in that order.
all: build docs check test
    @echo "built and verified."

# --- device ---------------------------------------------------------------- #

# Copy the court templates onto a tablet and register them.
install *ARGS:
    install/install.sh --host {{host}} {{ARGS}}

# The same, including the legacy set (run `just legacy` first).
install-legacy *ARGS:
    install/install.sh --host {{host}} --legacy {{ARGS}}

# Show what an install would change, without changing anything.
install-dry-run:
    install/install.sh --host {{host}} --dry-run

# After a firmware update: re-link and re-register without re-copying artwork.
relink:
    install/install.sh --host {{host}} --relink

# Remove the templates from a tablet (--purge also deletes the artwork).
uninstall *ARGS:
    install/uninstall.sh --host {{host}} {{ARGS}}

# Remove build output and caches.
clean:
    rm -rf {{out}}/png {{out}}/svg {{out}}/pdf {{out}}/templates.d
    find . -name __pycache__ -type d -prune -exec rm -rf {} +
