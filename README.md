# Case Creator + Case Lookup

Visual inventory for physical storage cases. Draw the bins the way they actually sit
in the case, label them, and find any part later by name, label, or note — with a 2D
grid and a 3D view showing exactly where it lives.

Two single-file browser apps that share one folder of case data. No build step, no
database, no server code — just static files.

![Search results](screenshots/search.png)

| | |
|-|-|
| **Case Creator** (`CaseCreator.dc.html`) | Full authoring — build cases, edit bins and levels, edit thumbnails, search, browse in 2D/3D. |
| **Case Lookup** (`CaseLookup.dc.html`) | Read-only terminal — search and browse only. |

Deploy either alone, or both side by side in the same folder. Everything from
**Files** down to **Troubleshooting** applies to both; the app-specific sections at
the end cover only what differs.

---

## Contents

- [Quick start](#quick-start)
- [Files](#files)
- [Where case data comes from](#where-case-data-comes-from)
- [Search](#search)
- [Running the server locally (Windows)](#running-the-server-locally-windows)
- [Running on Home Assistant](#running-on-home-assistant)
- [Access and security](#access-and-security)
- [Mobile](#mobile)
- [Troubleshooting](#troubleshooting)
- [Case Creator — specifics](#case-creator--specifics)
- [Case Lookup — specifics](#case-lookup--specifics)

---

---

## Quick start

1. Put `CaseCreator.dc.html`, `CaseLookup.dc.html` and `support.js` in a folder.
2. Create a `Cases/` subfolder next to them and drop your case `.zip` files in.
3. Serve the folder over HTTP — `python -m http.server 6040` is enough.
4. Open `http://localhost:6040/CaseCreator.dc.html`.

The apps must be served over HTTP. Opening the HTML by double-clicking it (`file://`)
will not work — see [Troubleshooting](#troubleshooting).

## Files

|File|Required|Notes|
|-|-|-|
|`CaseCreator.dc.html`|for authoring|The full app.|
|`CaseLookup.dc.html`|for lookup only|The read-only app.|
|`support.js`|yes|Runtime. Must sit next to the HTML.|
|`index.html`|no|Landing page linking to both apps.|
|`Cases/*.zip`|yes|Your case data — see below.|
|`Cases/index.html`|HA only|File list for servers with no directory index.|
|`Cases/make-index.bat`|no|Windows helper that regenerates `index.html`. Local use only.|
|`Cases/make-index.ps1`|no|Does the actual work; the `.bat` calls it.|

## Where case data comes from

On load the app lists the `Cases/` folder and loads **every `.zip` inside it**.
Each zip may be a single case or a multi-case export — both work, and they can be
mixed. Cases are sorted by filename; duplicate case names get `(2)`, `(3)` suffixes.

To add a case: drop its zip into `Cases/` and reload. To remove one: delete the zip
and reload. No config changes needed.

If some zips fail to parse, the rest still load and a banner names the ones skipped.
If nothing loads at all, the last cached copy in that browser is shown with a warning.

**Directory listing required.** Folder discovery works because the web server returns
an index for `Cases/`. Python's `http.server` does this by default. Home Assistant's
`/local/` does **not** — there you supply a hand-built `Cases/index.html` instead.
See the [Home Assistant](#running-on-home-assistant) section.

## Search

Search matches bin **labels** and bin **notes**, across every case at once.

**Notes are treated as a parts list.** A note split by commas or newlines is indexed
per entry, and each matching entry becomes its own result row — so a bin whose notes
list 34 components behaves like 34 searchable parts. The matching entry is shown in
quotes after the bin name and highlighted in the result.

**Plurals are handled.** Searching `resistors` finds `Resistor`, `fuses` finds `Fuse`,
`batteries` finds `Battery`, `boxes` finds `Box`. Only the last word of the query is
varied, so `red leds` still finds `Red LED`. Matching is case-insensitive.

Irregular plurals (`feet`, `dice`, `mice`) are not covered — the rules are
suffix-based, not a dictionary.

## Running the server locally (Windows)

(I used a random port 6040, you can choose whatever you like.)

From a Command Prompt (`Win+R` → `cmd`) — not the Python interpreter:

```
python -m http.server 6040 --directory "D:\path\to\casecreator"
```

Then open `http://localhost:6040/CaseCreator.dc.html`
(or `.../CaseLookup.dc.html`).

Reachable from your phone on the same Wi-Fi at `http://<pc-ip>:6040/CaseCreator.dc.html`
(find the IP with `ipconfig`; allow the Windows Firewall prompt on private networks).

### Start it automatically

Create a .bat file:

Open your favourite text editor, paste in the below:

```
@echo off
python -m http.server 6040 --directory "D:\Your_Case_Folder_Location"

@don't forget to Save the start-caselookup.vbs, shortcut it into shell:startup
```

Save it as CaseCreator.bat, make note of where you save it, you will need it for the next step.

Again, in a new text editor, paste in the below:

CreateObject("WScript.Shell").Run """D:\\Path_To_Your_Bat\CaseCreator.bat""", 0, False

Save as `start-cases.vbc` or whatever your whim for naming strikes at the time, copy the file
Pres the Windows Key and R, (or Start > Run) and enter shell:startup
Paste the file in the new window.

For a server that runs before login, use Task Scheduler (%windir%\system32\taskschd.msc /s) instead: trigger *At startup*,
action *Start a program* → `python`, arguments
`-m http.server 6040 --directory "D:\CaseCreator_Directory_Path\casecreator"`, and enable
"Restart if the task fails".

## Running on Home Assistant

Copy the files into `/config/www/casecreator/`, restart Home Assistant (the `www`
folder is only scanned at startup), then browse to:

```
http://homeassistant.local:8123/local/casecreator/CaseCreator.dc.html
```

Add it to a dashboard via Settings → Dashboards → **+ Add Dashboard** → *Webpage*,
URL `/local/casecreator/CaseCreator.dc.html` (swap in `CaseLookup.dc.html` as needed).
`panel_iframe:` in YAML was removed from recent HA versions — use the UI.

> **Dashboard URLs are not folders.** A dashboard at `/case-creator/` is handled by
> HA's frontend router, so `/case-creator/Cases/index.html` returns the dashboard app,
> not your file. Always test the `/local/...` path.

### Cases/index.html (required on HA)

**`/local/` serves no directory index** — requesting `/local/casecreator/Cases/`
returns `403`. The app handles this: if the folder itself can't be listed it retries
`Cases/index.html` and reads the file list from there.

So HA needs an `index.html` inside `Cases/` listing every zip:

```html
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><title>Cases</title></head>
<body>
<h1>Index of Cases/</h1>
<ul>
  <li><a href="Hardware-9x6.zip">Hardware-9x6.zip</a></li>
  <li><a href="Craft-9x6.zip">Craft-9x6.zip</a></li>
</ul>
</body>
</html>
```

Only `.zip` links are read; the heading and anything else is ignored.

**Generating it.** Don't hand-write this. Keep `make-index.bat` and
`make-index.ps1` in your **local** `Cases/` folder, double-click the `.bat`, and it
writes `index.html` from whatever zips are present — percent-encoding `&`, spaces
and other awkward characters correctly. Then copy `index.html` up to the HA
`Cases/` folder along with any new zips.

**Regenerate every time you add, rename or delete a zip.** A stale index fails
silently — the missing case simply won't appear, with no error, because the index
still parses fine. If a case goes missing, regenerate before debugging anything else.

The scripts are Windows-only and are development tools — there's no need to copy
them to Home Assistant, only the `index.html` they produce.

Alternatively, skip all of this by serving `Cases/` from something that does list
directories — NGINX Proxy Manager, or a small Python server on the Pi — and pointing
`casesFolder` in the HTML at that URL.

## Access and security

**There is no login.** Both apps open straight into the interface, and anyone who can
reach the URL can read — and in Case Creator, edit — the data.

This is deliberate. A login implemented in the page is decorative: the browser already
holds the data before any check runs, and the case zips can be fetched directly from
their URLs regardless. It offered no protection while adding a step to every visit.

If the apps need to be reachable from outside your network, put real authentication in
front of the folder — NGINX Proxy Manager basic auth, Authelia, a Cloudflare Access
policy, or a VPN. That is server-side and actually enforces something.

## Mobile

Single-column layout on phones, 16px inputs (prevents iOS zoom), 44–50px touch
targets, no horizontal page overflow. Search results stack thumbnail → grid → 3D
vertically. Case Creator switches at 760px with a two-column nav; Case Lookup at 720px.

On narrow screens the 3D views are tap-to-toggle rather than always-on, so idle
results don't re-render — tapping a result opens its 3D view instead of navigating
away.

The Case Creator and Thumbnail Editor tabs are usable on a tablet but are designed for
a mouse — do authoring on a desktop.

## Troubleshooting

**`HTTP 404` or `403` listing `Cases/`** — the path is wrong relative to the served
root, or the server doesn't list directories. Open `http://<host>/Cases/` in a
browser: you should see a file list. Names are case-sensitive. On Home Assistant a
`403` here is normal — check `http://<host>/local/casecreator/Cases/index.html`
loads instead.

**A case is missing on HA but present locally** — `Cases/index.html` is stale.
Re-run `make-index.bat` locally and copy the new `index.html` up. This failure is
silent; nothing is logged.

**`NetworkError`** — you opened the HTML by double-clicking it (`file://`). Browsers
block reading local files that way; it must be served over HTTP.

**Cases vanish after reload** — they were never saved into `Cases/`. Save each case
as a zip and copy it to the folder.

**Changes don't appear** — hard-refresh (`Ctrl+Shift+R`). HA caches `/local/`
aggressively; appending `?v=2` to the URL also works.

---

# Case Creator — specifics

Authoring app. Everything Case Lookup does, plus creating and editing cases.

## Tabs

|Tab|What it does|
|-|-|
|Search|Find parts by name, bin label, or note. Shows thumbnail, 2D grid, 3D view.|
|Find Empty|Lists free cells per case. Hover a result to x-ray the case and see them.|
|Case Creator|Create/edit cases: draw bins, resize, colour-code levels, add notes.|
|View Cases|Browse any loaded case level by level.|
|Cases Folder|Folder status, skipped zips, and a **Reload from folder** button.|
|Thumbnail Editor|Crop, layer, and edit case and bin images.|
|Help|In-app guide with animated demos.|

## Thumbnail editor

Every case and every bin can carry its own image. The thumbnail editor is a small
layered image editor built into Case Creator — no external tool needed to crop a
product photo down to something that reads at 100px.

![Thumbnail editor](screenshots/thumbnail-editor.png)

Open it three ways: the **Thumbnail Editor** tab, clicking a bin's image in the case
properties panel, or the edit button on an existing thumbnail. Dropping an image
straight onto a bin opens it too.

|Control|What it does|
|-|-|
|Select / move|Move, scale and rotate the active layer. Drag a corner handle to rotate; hold `Shift` to snap to 45°.|
|Fill area|Flood-fill with the current colour — useful for knocking out a background.|
|Selection|Rectangular marquee.|
|Freehand selection|Lasso an irregular shape.|
|Delete selection|Clears the selected area of the active layer.|
|Colour swatch|Sets the fill colour.|
|Undo / redo|`Ctrl+Z` / `Ctrl+Y`.|
|Zoom / default view|Zoom in and out; **Default view** resets zoom and pan.|
|Import image|Adds a file as a new layer.|

**Layers** stack in the panel on the right — drag to reorder, click the eye to hide,
the bin to delete. Paste (`Ctrl/Cmd+V`) adds whatever is on the clipboard as a new
layer, so you can build a thumbnail from several photos.

Pasted and imported images are scaled to **fit inside** the canvas rather than filling
it, so nothing is silently cropped on the way in.

**Save Thumbnail** writes the flattened result back to the case or bin you opened it
from. It's stored inside that case's zip, so it travels with the case.

## Saving a case

Case Creator → save the case; the browser downloads `<Case Name>.zip`. Move that zip
into the `Cases/` folder on the server and it loads for everyone next time.

Cases you create in the browser but haven't copied into `Cases/` yet live in that
browser's local storage and appear alongside the folder cases. A folder case with the
same name wins on reload. There is no manual import — the folder is the only way in.

---

# Case Lookup — specifics

Read-only inventory terminal. Search across every bin in every case, or browse a case
grid visually. No editing, no builder, no thumbnail editor — pair it with Case Creator
for authoring.

Two tabs only: **Search** (including Find Empty) and **View Cases**.
