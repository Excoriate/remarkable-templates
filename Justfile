# remarkable-templates — build and install reMarkable paper templates.
#
#   just                 list the recipes
#   just setup           create .venv and install dependencies
#   just all             build everything and verify it
#   just install         copy the templates onto a tablet over SSH
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
    python3 -m venv "{{venv}}"
    "{{python}}" -m pip install --upgrade pip --quiet
    "{{python}}" -m pip install --quiet -e ".[dev]"
    @echo "ready. next: just all"

# Show the families, devices and template sets this checkout knows about.
list:
    "{{python}}" -m rmtpl --device "{{device}}" --out "{{out}}" list

# Render every template family (or one: just build basketball).
build FAMILIES="":
    "{{python}}" -m rmtpl --device "{{device}}" --out "{{out}}" build "{{FAMILIES}}" --clean

# Turn a folder of PNGs into a template set: just ingest ~/art mine
ingest PNG_DIR NAMESPACE="imported" PREFIX="" STRIP="" FIT="fit":
    "{{python}}" -m rmtpl --device "{{device}}" --out "{{out}}" ingest "{{PNG_DIR}}" \
        --namespace "{{NAMESPACE}}" --prefix "{{PREFIX}}" --strip "{{STRIP}}" \
        --fit "{{FIT}}"

# Multi-page PDFs per set, for adding templates without developer mode.
bundle COPIES="1":
    "{{python}}" -m rmtpl --device "{{device}}" --out "{{out}}" bundle --copies "{{COPIES}}"

# Regenerate the generated reference docs from each family's specs.
docs:
    "{{python}}" -m rmtpl docs

# Verify: rule-book cross-checks, file contract, geometry measured back out.
check:
    "{{python}}" -m rmtpl --device "{{device}}" --out "{{out}}" doctor

# Run the test suite.
test:
    "{{python}}" -m pytest -q

# Lint Python and shell.
lint:
    "{{python}}" -m ruff check src tests tools install/lib
    shellcheck -S warning install/*.sh scripts/*.sh

# A contact sheet per set, for the README.
preview:
    "{{python}}" tools/contact_sheet.py "{{out}}" docs/images

# Build, document, preview and verify, in that order.
all: build docs bundle preview check test
    @echo "built and verified."

# --- device ---------------------------------------------------------------- #

# Copy the built templates onto a tablet and register them.
install *ARGS:
    install/install.sh --host "{{host}}" {{ARGS}}

# Show what an install would change, without changing anything.
install-dry-run *ARGS:
    install/install.sh --host "{{host}}" --dry-run {{ARGS}}

# After a firmware update: re-link and re-register without re-copying artwork.
relink:
    install/install.sh --host "{{host}}" --relink

# Remove the templates from a tablet (--purge also deletes the artwork).
uninstall *ARGS:
    install/uninstall.sh --host "{{host}}" {{ARGS}}

# Remove build output and caches.
#
# The deletion is done by the toolkit rather than by a shell glob: `just`
# interpolates unquoted, so `rm -rf {{{{out}}}}/*/png` on a path containing a
# space becomes two arguments and deletes the wrong thing. Only this recipe is
# destructive, so only this recipe gets to be paranoid.
clean:
    "{{python}}" -m rmtpl --out "{{out}}" clean
    find . -name __pycache__ -type d -prune -exec rm -rf {} +
