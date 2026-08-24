# Installing

Three routes, in ascending order of what they ask of you and descending order
of how easily they break.

| | Developer mode | Appears in the template picker | Survives a firmware update |
| --- | --- | --- | --- |
| **PDF** | no | no — it is a notebook | yes |
| **SSH (this repo's installer)** | yes | yes | yes, via `just relink` |
| **RCU** | yes | yes | yes, automatically |

## 1. PDF — no developer mode

`templates/pdf/` holds one PDF per court plus a bundle per orientation. Drag one
into the reMarkable desktop or mobile app and it syncs to the tablet as a
notebook you write on top of.

```bash
just bundle COPIES=10        # ten pages of each court, ready to fill
```

This is not a template in reMarkable's sense — it is a document — so it will not
show up when you tap the page menu and choose a template, and you cannot apply
it to an existing notebook. What you get instead is a fixed stack of pages,
which for a season of play diagrams is usually what you actually wanted. Pages
are sized to the panel exactly: 509.34 × 679.13 pt at 229 PPI, so nothing is
rescaled on the way in.

## 2. SSH — the template picker

This puts the courts alongside reMarkable's own templates, so you can apply one
to any page of any notebook.

**Enable developer mode.** Settings → General → Software → Advanced. On a Paper
Pro this **factory resets the tablet**, so sync everything you care about first.
The root password appears under Settings → General → Help → Copyrights and
licenses, together with the USB address (10.11.99.1).

```bash
just build
install/install.sh --dry-run          # prints exactly what will change
just install                          # asks before it changes anything
```

Over WiFi instead of USB, pass the tablet's address:

```bash
RM_HOST=192.168.1.42 just install
```

What the installer does, in order:

1. Copies the PNGs to `/home/root/.local/share/remarkable/templates/basketball/`.
2. Remounts `/` read-write and symlinks that directory into
   `/usr/share/remarkable/templates/basketball`.
3. Backs up `templates.json` on the tablet — once as
   `templates.json.orig`, and again per run with a timestamp.
4. Fetches `templates.json`, merges the manifest fragment **on your machine**,
   and writes it back. reMarkable devices ship no Python, and this is the step
   where a mistake costs you your stock templates, so it happens where there is
   real tooling.
5. Reads `templates.json` back **from the device** and checks that every
   template it lists resolves to a readable file.
6. Restarts xochitl.

Then, on the tablet: open a notebook, tap the page menu, choose a template, and
look under the **Basketball** tab.

### After a firmware update

The update replaces `/usr/share`, so the symlink and the manifest entries go.
The artwork under `/home/root` does not.

```bash
just relink
```

### Removing them

```bash
just uninstall              # entries and symlink go, artwork stays
just uninstall --purge      # delete the artwork too
```

Notebook pages that already use one of these templates keep referring to it by
filename. Reinstall under the same names later and those pages look right again.

### The legacy set

```bash
just legacy "~/Downloads/Remarkable Basketball Court Templates (PNG)"
just install-legacy
```

This builds a second, separately namespaced set from artwork this repository
does not ship. See [NOTICE.md](../NOTICE.md).

### SVG instead of PNG

xochitl prefers an SVG over a PNG when both are present under the same name.
`install/install.sh --svg` uploads both. It is left off by default because the
PNGs are rendered at exactly the panel's pixel grid, which is a known quantity,
whereas how a given firmware rasterises an SVG is not something this project has
measured on a device. If you try it and it looks good, say so in an issue.

## 3. RCU

[reMarkable Connection Utility](http://www.davisr.me/projects/rcu/) is a paid
desktop application that manages templates, among much else, and repairs them
automatically after a firmware update. It accepts the PNGs in `templates/png/`
directly. If you would rather not run shell scripts against your tablet, use it.

## Troubleshooting

**"cannot reach root@10.11.99.1"** — the tablet must be plugged in by USB and
awake. `ping 10.11.99.1` first. Over WiFi, developer mode also needs SSH over
WLAN turned on.

**Templates do not appear after installing** — the UI restart may not have
taken. `ssh root@10.11.99.1 systemctl restart xochitl`. If they are still
missing, check that the entries survived:
`ssh root@10.11.99.1 'grep -c basketball /usr/share/remarkable/templates/templates.json'`.

**Blank squares instead of icons in the picker** — the `iconCode` characters
come from stock templates and should exist on any device, but if your firmware's
icon font differs, rebuild with `--blank-icons` to use only the two "Blank"
glyphs.

**Restoring the original templates.json**

```bash
ssh root@10.11.99.1 'mount -o remount,rw / && cp \
  /home/root/.local/share/remarkable/templates/templates.json.orig \
  /usr/share/remarkable/templates/templates.json && systemctl restart xochitl'
```
