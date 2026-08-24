"""The promise the installer makes about a device's own templates.

`templates.json` is a single flat list that xochitl owns. Merging into it is the
one step in this project that can destroy something the user cares about, and
"we merge carefully" is worth nothing without a check that fires when the merge
goes wrong. These tests exercise the guards themselves — including by breaking
the merge on purpose and confirming the guard refuses to write.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

from rmtpl import manifest

REPO = Path(__file__).resolve().parents[1]
MERGE = REPO / "install" / "lib" / "merge_templates_json.py"
VERIFY = REPO / "install" / "lib" / "verify_install.py"
VERIFY_UNINSTALL = REPO / "install" / "lib" / "verify_uninstall.py"


def _device(n: int = 5) -> dict:
    return {"templates": [
        {"name": f"Stock {i}", "filename": f"Stock{i}", "iconCode": "",
         "categories": ["Creative"]} for i in range(n)]}


def _our_manifest(tmp_path: Path, stems=("a", "b")) -> Path:
    entries = [manifest.TemplateEntry(f"Ours {s}", f"demo/{s}", "",
                                      categories=["Demo"]) for s in stems]
    path = tmp_path / "manifest.json"
    manifest.write(path, entries)
    return path


def _run(script: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(script), *map(str, args)],
                          capture_output=True, text=True)


def test_merge_keeps_every_device_entry(tmp_path):
    dev = tmp_path / "device.json"
    dev.write_text(json.dumps(_device()))
    out = tmp_path / "merged.json"
    r = _run(MERGE, dev, _our_manifest(tmp_path), "-o", out)
    assert r.returncode == 0, r.stderr
    merged = json.loads(out.read_text())["templates"]
    assert [t for t in merged if not t["filename"].startswith("demo/")] == \
        _device()["templates"]
    assert len(merged) == 7


def test_merge_refuses_to_write_when_a_device_entry_would_be_lost(tmp_path,
                                                                 monkeypatch):
    """Break the merge itself; the guard must catch it and write nothing."""
    dev = tmp_path / "device.json"
    dev.write_text(json.dumps(_device()))
    out = tmp_path / "merged.json"

    spec = importlib.util.spec_from_file_location("merge_mod", MERGE)
    module = importlib.util.module_from_spec(spec)
    original = manifest.merge

    def losing(device, ours, *, namespace):
        merged, removed, added = original(device, ours, namespace=namespace)
        merged = dict(merged)
        merged["templates"] = merged["templates"][1:]      # drop a stock entry
        return merged, removed, added

    monkeypatch.setattr(manifest, "merge", losing)
    monkeypatch.setattr(sys, "argv",
                        ["merge", str(dev), str(_our_manifest(tmp_path)),
                         "-o", str(out)])
    spec.loader.exec_module(module)
    assert module.main() == 1
    assert not out.exists(), "a failed merge must not leave a file to upload"


def test_verify_detects_a_wholesale_replacement(tmp_path):
    """The catastrophe: templates.json replaced with only our entries."""
    ours = _our_manifest(tmp_path)
    replaced = tmp_path / "replaced.json"
    replaced.write_text(json.dumps({"templates": [
        {"name": "Ours a", "filename": "demo/a", "iconCode": "",
         "categories": ["Demo"]},
        {"name": "Ours b", "filename": "demo/b", "iconCode": "",
         "categories": ["Demo"]}]}))
    r = _run(VERIFY, replaced, "5", ours)
    assert r.returncode == 1
    assert "did not survive" in r.stderr


def test_verify_passes_on_a_correct_install(tmp_path):
    dev = tmp_path / "device.json"
    dev.write_text(json.dumps(_device()))
    out = tmp_path / "merged.json"
    ours = _our_manifest(tmp_path)
    assert _run(MERGE, dev, ours, "-o", out).returncode == 0
    r = _run(VERIFY, out, "5", ours)
    assert r.returncode == 0, r.stderr
    assert "unchanged" in r.stdout


def test_uninstall_restores_the_device_file_exactly(tmp_path):
    dev = tmp_path / "device.json"
    dev.write_text(json.dumps(_device()))
    ours = _our_manifest(tmp_path)
    merged, clean = tmp_path / "merged.json", tmp_path / "clean.json"
    assert _run(MERGE, dev, ours, "-o", merged).returncode == 0
    assert _run(MERGE, merged, ours, "--remove-only", "-o", clean).returncode == 0
    assert json.loads(clean.read_text())["templates"] == _device()["templates"]
    assert _run(VERIFY_UNINSTALL, clean, "demo").returncode == 0


def test_merge_refuses_an_invalid_manifest(tmp_path):
    dev = tmp_path / "device.json"
    dev.write_text(json.dumps(_device()))
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({"templates": [
        {"name": "X", "filename": "demo/x.png", "iconCode": "",
         "categories": ["Demo"]}]}))
    r = _run(MERGE, dev, bad, "-o", tmp_path / "out.json")
    assert r.returncode == 1
    assert "extension" in r.stderr


@pytest.mark.parametrize("script", ["install/install.sh", "install/uninstall.sh",
                                    "scripts/setup-github.sh"])
def test_shell_scripts_parse(script):
    assert subprocess.run(["bash", "-n", REPO / script]).returncode == 0


def test_justfile_quotes_every_interpolation():
    """`just` substitutes recipe variables unquoted.

    On a path containing a space — a checkout in `~/Downloads/Some Folder/`, say
    — an unquoted `{{out}}` splits into two shell words. In a `rm -rf` that
    deletes the wrong thing, which is exactly what happened here once.
    """
    import re
    text = (REPO / "Justfile").read_text()
    offenders = []
    for line in text.splitlines():
        if not line.startswith(("    ", "\t")) or line.lstrip().startswith("#"):
            continue
        for m in re.finditer(r'(.?)\{\{\s*([A-Za-z_][\w]*)', line):
            before, name = m.group(1), m.group(2)
            end = line.find("}}", m.end())
            after = line[end + 2:end + 3] if end != -1 else ""
            # *ARGS is a variadic passthrough; quoting it would make one word.
            if name == "ARGS":
                continue
            if before != '"' or after != '"':
                offenders.append(line.strip())
                break
    assert not offenders, "unquoted interpolation(s):\n" + "\n".join(offenders)


def test_no_shell_glob_deletes_through_an_interpolated_path():
    text = (REPO / "Justfile").read_text()
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        assert not (stripped.startswith("rm -rf") and "{{" in stripped), (
            f"destructive shell glob over an interpolated path: {stripped}")
