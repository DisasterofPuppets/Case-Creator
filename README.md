# Case Creator + Case Lookup

Visual inventory for physical storage cases. Draw the bins the way they actually sit
in the case, label them, and find any part later by name, label, or note — with a 2D
grid and a 3D view showing exactly where it lives.

Two single-file browser apps that share one folder of case data. No build step, no
database, no server code — just static files.

![Search results](.github/screenshots/search.png)

| | |
|-|-|
| **Case Creator** (`CaseCreator.dc.html`) | Full authoring — build cases, edit bins and levels, edit thumbnails, search, browse in 2D/3D. |
| **Case Lookup** (`CaseLookup.dc.html`) | Read-only terminal — search and browse only. |

**The intended setup:** run both from one folder on the machine that holds your case
data, served by a local Python server and opened in Edge or Chrome. Optionally publish
**Case Lookup alone** to Home Assistant as a read-only terminal — Case Creator cannot
save from there, so it stays local. See
[Running Case Lookup on Home Assistant](#running-case-lookup-on-home-assistant-optional).

Everything from **Files** down to **Troubleshooting** applies to both apps; the
app-specific sections at the end cover only what differs.

---

## Contents

- [Quick start](#quick-start)
- [Files](#files)
- [Where case data comes from](#where-case-data-comes-from)
- [Search](#search)
- [Running the server locally (Windows)](#running-the-server-locally-windows)
- [Running Case Lookup on Home Assistant](#running-case-lookup-on-home-assistant-optional)
- [Access to files and folders](#access-to-files-and-folders)
- [Access and security](#access-and-security)
- [Mobile](#mobile)
- [Troubleshooting](#troubleshooting)
- [Case Creator — specifics](#case-creator--specifics)
- [Case Lookup — specifics](#case-lookup--specifics)

---

## Quick start

1. Put `CaseCreator.dc.html`, `CaseLookup.dc.html` and `support.js` in a folder.
2. Create a `Cases/` subfolder next to them and drop your case `.zip` files in.
3. Serve the folder over HTTP — `python -m http.server 6040` is enough.
4. Open `http://localhost:6040/CaseCreator.dc.html` in **Edge or Chrome** — only
   those expose the folder-access API Case Creator needs to write to disk, and only
   on `localhost` or HTTPS. Everything else works in any browser.

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
|`Cases/index.html`|recommended|File list for servers with no directory index. Once it exists it **overrides** directory listing on every server, local included. Rebuilt automatically on save when folder access is granted.|
|`Backup/`|auto|Dated `.bak` copies written before each save. Sibling of `Cases/`, created on demand.|
|`OrphanedBins/`|auto|Holds `OrphanedBins.zip`. Sibling of `Cases/`, created on demand.|
|`Tools/`|no|Local-only helper scripts. Never deployed.|
|`.github/`|no|README screenshots. Repo furniture — not part of a deployment. Hidden from GitHub's file listing by the leading dot.|
|`Tools/make-index.bat`|no|Windows helper that regenerates `Cases/index.html`. Local use only — never copied to a server.|
|`Tools/make-index.ps1`|no|Does the actual work; the `.bat` calls it. Its `$CasesFolder` setting points at `..\Cases` by default.|

## Where case data comes from

On load the app lists the `Cases/` folder and loads **every `.zip` inside it**.
Each zip may be a single case or a multi-case export — both work, and they can be
mixed. Cases are sorted by filename; duplicate case names get `(2)`, `(3)` suffixes.

To add a case: drop its zip into `Cases/` and reload. To remove one: delete the zip
and reload. No config changes needed.

If some zips fail to parse, the rest still load and a banner names the ones skipped.
If nothing loads at all, the last cached copy in that browser is shown with a warning.

**Directory listing required.** Folder discovery works because the web server returns
an index for `Cases/`. Python's `http.server` generates one — but **only while the
folder contains no `index.html` of its own.** Add one and Python serves that file
instead, which makes it the source of truth locally as well as on Home Assistant.
`/local/` never generates a listing, so there the file is mandatory.

The practical consequence: **a stale `Cases/index.html` hides cases on every server.**
The zip sits in the folder and simply never appears, with nothing logged. Case Creator
rebuilds the file after every save when folder access is granted; without that, rebuild
it by hand with `make-index.bat`.

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

Task Scheduler runs a small **pure-PowerShell** launcher directly — no VBScript, no
Python needed for this. (VBScript is deprecated in Windows and can silently fail to
fire when Task Scheduler triggers it at the SYSTEM level; running `powershell.exe`
with `-WindowStyle Hidden` needs no VBS wrapper to stay invisible.)

**1. Drop `CaseCreator_Server_Port_6040.ps1` into this folder.** It's a self-contained
static file server built on `System.Net.HttpListener` — serves this folder over HTTP,
no Python install required. It logs to `caseserver.log` / `caseserver.err.log` beside
itself.

**One-time setup required — a URL reservation.** `HttpListener` bound to `+` (all
interfaces, so the server is reachable from other devices, not just this PC) needs
Windows' permission the first time, or it fails immediately with "Access Denied" when
run as a normal user (which the scheduled task does). Run this **once**, as
Administrator:

```powershell
netsh http add urlacl url=http://+:6040/ user=Everyone
```

Skip this if you only need `http://localhost:6040/` on the same machine — swap
`http://+:6040/` for `http://localhost:6040/` inside the script and this step isn't
needed, but then it won't be reachable from your phone or other devices on the LAN.

**2. Create the scheduled task.** `Win+R` → `taskschd.msc` → **Create Basic Task**.

|Screen|Enter|
|-|-|
|Name|Something you will recognise, e.g. *CaseLookup Server Startup*.|
|Trigger|**When I log on**|
|Action|**Start a program**|
|Start a Program|Program/script: `powershell.exe` &nbsp;&nbsp; Add arguments: `-WindowStyle Hidden -ExecutionPolicy Bypass -File "K:\WIP Projects\Case Creator REDUX\CaseCreator_Server_Port_6040.ps1"`|

On the final screen tick **Open the Properties dialog for this task when I click
Finish** — the wizard doesn't expose the settings that matter.

**3. Fix the settings the wizard cannot reach.** In the Properties dialog:

> ### Settings tab — untick **Stop the task if it runs longer than**
>
> **This is the one that will bite you.** Create Basic Task sets it to *3 days*
> automatically. A web server is meant to run indefinitely, so after three days of
> uptime Windows kills it with no warning and no log entry — the page simply stops
> responding, and the task still shows as healthy because it *completed* rather than
> failed.
>
> Untick the box entirely. Do not set a longer time; there is no value that means
> "forever" except unticking it.

While you are in there, two more worth setting:

|Tab|Setting|Why|
|-|-|-|
|Conditions|Untick **Start the task only if the computer is on AC power**|Ticked by default. On a laptop the server silently will not start on battery.|
|Settings|**If the task is already running** → *Do not start a new instance*|Stops a second trigger fighting for port 6040.|
|Settings|Tick **If the task fails, restart every** → 1 minute, up to 3 times|A transient failure recovers itself instead of leaving you with no server until next logon.|

If you closed the wizard without ticking the Properties box, right-click the task in
the Task Scheduler Library and choose **Properties** — same dialog.

**4. Test it** without rebooting: right-click the task → **Run**, then open
`http://localhost:6040/`. If nothing responds, check `caseserver.log` /
`caseserver.err.log` beside the `.ps1`. A missing `caseserver.err.log` plus no response
usually means the urlacl reservation (step 1) hasn't been done — the listener fails to
bind and exits before logging anything to `caseserver.log`.

**Verifying the time limit actually stuck** — export the task (right-click → *Export*)
and open the XML. You want:

```xml
<ExecutionTimeLimit>PT0S</ExecutionTimeLimit>
```

`PT0S` means no limit. If you see `P3D` the box is still ticked.

**To stop the server**: the scheduled task launches `powershell.exe` running the
listener directly (no child process, unlike the old Python version) — end that
`powershell.exe` process in Task Manager. If you have other PowerShell windows open,
check the **Command line** column (Task Manager → Details → right-click header →
Select columns) to find the one referencing `CaseCreator_Server_Port_6040.ps1`.

## Running Case Lookup on Home Assistant (optional)

A read-only terminal on your HA dashboard, so you can look a part up from the couch
without touching the authoring machine. Entirely optional — the local server is the
whole product; this is a convenience layer on top of it.

**Deploy Case Lookup only. Do not put Case Creator on Home Assistant.**

It would load and appear to work, but it cannot save anything useful from there:

- `http://homeassistant.local:8123` is plain HTTP, so the browser withholds the
  folder-access API entirely — see [Local folder access](#local-folder-access).
- Even over HTTPS it would be worse, not better. The folder picker selects a folder on
  **the machine running the browser**, not on the HA host. You would end up reading
  cases from HA over the network while writing saves, backups and orphans to a folder
  on your laptop — two diverging copies, silently.

Author locally, publish to HA. That keeps one source of truth.

### What to copy

Two files and one folder:

```
/config/www/casecreator/
    CaseLookup.dc.html      required
    support.js              required - the app is a blank page without it
    Cases/                  copy the whole folder across
```

`Cases/` holds only case data and `index.html` now, so copying it wholesale is
correct - there is nothing in there that should not go up.

Nothing else. Leave behind `CaseCreator.dc.html`, the root `index.html` launcher,
`Backup/`, `OrphanedBins/`, `Tools/`, `README.md` and `.github/`. None of them do
anything on HA, and `Backup/` in particular is pure bulk.

`OrphanedBins/` is not copied deliberately — parked and orphaned parts are an
authoring concept, and Case Lookup cannot read them anyway.

### First-time setup

1. Copy the files above into `/config/www/casecreator/` — Samba, the File Editor
   add-on, or SSH all work.
2. **Restart Home Assistant.** The `www` folder is only scanned at startup, so a newly
   created folder will 404 until you do.
3. Browse to `http://homeassistant.local:8123/local/casecreator/CaseLookup.dc.html`
   and confirm the cases load.
4. Add it to a dashboard: Settings → Dashboards → **+ Add Dashboard** → *Webpage*,
   URL `/local/casecreator/CaseLookup.dc.html`. In YAML the card is:

   ```yaml
   type: iframe
   url: /local/casecreator/CaseLookup.dc.html
   ```

   `panel_iframe:` in `configuration.yaml` was removed from recent HA versions — add
   the dashboard through the UI instead.

> **Dashboard URLs are not folders.** A dashboard at `/case-lookup/` is handled by
> HA's frontend router, so `/case-lookup/Cases/index.html` returns the dashboard app,
> not your file. When you are checking whether a file landed, always test the
> `/local/...` path.

### Getting to it quickly

The dashboard URL path is arbitrary — pick anything; these examples use
`/case-lookup/`. Two shortcuts worth adding once it works:

**A button on your default dashboard.** Add a `custom:button-card`
([button-card](https://github.com/custom-cards/button-card), via HACS):

```yaml
type: custom:button-card
icon: mdi:briefcase-search
name: Cases
tap_action:
  action: navigate
  navigation_path: /case-lookup/0
show_name: true
show_icon: true
show_state: false
grid_options:
  columns: 2
  rows: 1
color: rgb(232, 93, 31)
```

`rgb(232, 93, 31)` is the app's own accent orange, so the button matches what it opens.
The trailing `/0` is the view index — the first view of that dashboard.

**A sidebar link**, so it sits alongside your other HA panels. The
[browser_mod](https://github.com/thomasloven/hass-browser_mod) integration can add one
pointing at the same dashboard path.

Both are optional. A plain bookmark to
`/local/casecreator/CaseLookup.dc.html` works just as well, it is just less tidy.

### Updating cases after you edit them

`Cases/index.html` is what HA reads to discover the zips, and it is **not** rebuilt on
HA — the automatic rebuild only happens locally, on save, with folder access granted.
So every publish is three steps:

1. **Locally**, double-click `Tools/make-index.bat`. It rewrites `Cases/index.html`
   from whatever zips are in that folder.
2. **Copy your whole `Cases` folder across**, replacing the one on HA.
3. Hard-refresh the dashboard (`Ctrl+Shift+R`). HA caches `/local/` hard; appending
   `?v=2` to the URL also works. A restart is only needed if you added new folders.

Copying the whole folder is the point of step 2 - `index.html` lists every zip in your
local `Cases/`, so cherry-picking a few zips leaves the index naming files that are not
there, and those cases fail to load with a "skipped" banner. Send the lot and the two
stay in step.

### Cases/index.html — what it looks like

Only `.zip` links are read; the heading and everything else is ignored.

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

Don't hand-write it. `Tools/make-index.ps1` percent-encodes `&`, `#`, `%`, spaces and
apostrophes correctly; a hand-typed file breaks on the first awkward filename. The two
scripts are Windows-only development tools — only the `index.html` they produce goes
to HA.

**A stale index fails silently.** The missing case simply does not appear, no error,
because the index still parses fine. If a case goes missing on HA, regenerate and
re-copy before debugging anything else.

**Alternative:** skip the index entirely by serving `Cases/` from something that does
list directories — NGINX Proxy Manager, or a small Python server on the Pi — and
point `casesFolder` in `CaseLookup.dc.html` at that URL.

## Access to files and folders

Full disclosure on what is read and written, when, and by which app. Nothing below is
optional behaviour hidden behind a setting - this is everything the two apps do.

Throughout, **install directory** means the folder the web server serves, the one
holding `CaseCreator.dc.html`, `CaseLookup.dc.html` and `support.js`. It is also the
folder you grant access to. The expected layout:

```
<install>/
    CaseCreator.dc.html
    CaseLookup.dc.html
    support.js
    Cases/              case zips + index.html - the only folder ever scanned
    Backup/             dated .bak copies
    OrphanedBins/       OrphanedBins.zip
    Tools/              local-only helper scripts, never read by the apps
    .github/            README screenshots, not part of a deployment
```

`Backup/` and `OrphanedBins/` sit beside `Cases/`, not inside it, so `Cases/` holds
nothing but the case data - copy that one folder to Home Assistant and you carry
exactly what it needs and nothing else. Both are created on demand; you never make
them by hand. Their names are set at the top of the logic block in
`CaseCreator.dc.html` under **USER SETTINGS** if you want them elsewhere.

### Reads over HTTP - both apps, automatic

These happen on page load and whenever you press **Reload from folder**. They are
ordinary web requests to your own server; nothing leaves your network.

|Path|What is read|
|-|-|
|`<install>/Cases/`|The directory listing, **or** `Cases/index.html` if that file exists. Used to discover which zips are present.|
|`<install>/Cases/*.zip`|Every zip the listing names, in full. Bins, labels, notes and embedded images are parsed into memory.|
|`<install>/support.js`|The runtime. Loaded by a `<script>` tag.|

### Reads over HTTP - Case Creator only, conditional

|Path|Triggered by|
|-|-|
|`<install>/OrphanedBins/OrphanedBins.zip`|Ticking **Show Orphaned Parts**, and again at save time when parked bins are merged in - the latter only if folder access is *not* granted.|
|`<install>/Cases/<Case Name>.zip`|**Save Case**, as a fallback only. Used to fetch the copy currently on disk for backup when the direct folder read fails.|

### Reads from the internet - both apps

**The apps are not fully offline.** Two external origins are contacted on every page
load, before any of your data is touched:

|Origin|What for|
|-|-|
|`fonts.googleapis.com`, `fonts.gstatic.com`|Webfonts - Archivo, Roboto Condensed, IBM Plex Mono. Declared in the `<head>` of both HTML files.|
|`unpkg.com`|React 18.3.1, ReactDOM 18.3.1 and Babel Standalone 7.29.0, requested by `support.js` with Subresource Integrity hashes so a tampered file is rejected.|

Neither request carries any of your data - they are plain asset downloads. Both are
removable if you want a fully air-gapped install: delete the two `<link>` tags from the
HTML (the pages fall back to system fonts), and self-host the three scripts.

### Reads from the internet - user-initiated only

|Trigger|What happens|
|-|-|
|Dragging an **image URL** onto a bin|That URL is fetched as an image, cross-origin. Only when you drag a link. Dragging or picking a **file** never touches the network.|

### Writes to disk - Case Creator only, folder access granted

Every one of these is triggered by a single action: clicking **Save Case**. Nothing is
written in the background, on a timer, or on page load.

|Path|What is written|
|-|-|
|`<install>/Cases/<Case Name>.zip`|The case you are editing. Overwrites the existing file.|
|`<install>/Backup/<Case Name>_dd_mm_yyyy.bak`|The copy that was on disk *before* the overwrite. Written first, so the previous state is safe before anything is replaced. Skipped if the case has never been saved.|
|`<install>/OrphanedBins/OrphanedBins.zip`|Only when parked bins are flushed and you confirm the warning. Merged with what is already there; nothing is removed.|
|`<install>/Cases/index.html`|Rebuilt from the zips actually present, so the file list can never go stale.|
|`<install>/.casecreator-folder-check`|Temporary, deleted straight away. See [The folder check](#the-folder-check).|

**Writes are confined to the folder you granted and its subfolders.** The browser
enforces this, not the app - there is no way for it to reach anything else on the disk,
including the rest of the drive the folder sits on.

### The folder check

One extra write, worth explaining because it is the only file the app creates that is
not yours: `.casecreator-folder-check` in the install directory.

The browser's permission prompt names the folder you picked, but only its **name** -
`Case Creator REDUX`, not its path. Two copies of the project share a name, and a saved
grant outlives the server being repointed at a different folder entirely. Get that wrong
and the app reads cases over HTTP from one folder while writing saves and backups into
another, silently.

So before trusting a folder, the app writes a random token into that file through the
folder handle, then tries to fetch the same file over HTTP. Only the folder the server
is actually serving can satisfy both. The file is deleted immediately either way, and
the grant is refused if the check fails.

This runs when you click **Grant folder access**, and once per session against a saved
grant. If you ever see a stray `.casecreator-folder-check`, the delete failed - it is
inert, delete it.

### Reads from disk - Case Creator only, folder access granted

|Path|Triggered by|
|-|-|
|`<install>/Cases/<Case Name>.zip`|**Save Case** - read so it can be copied to `Backup/`.|
|`<install>/OrphanedBins/OrphanedBins.zip`|**Show Orphaned Parts**, and **Save Case** when merging parked bins.|
|`<install>/Cases/` (listing)|**Save Case** - enumerated to rebuild `index.html`. Filenames only; the zips are not opened.|
|`<install>/.casecreator-folder-check`|**Grant folder access**, and once per session on the saved grant. A short random token is written, read back over HTTP, then the file is deleted. See below.|

### Writes without folder access - downloads only

With no folder access granted, nothing is written to the install directory at all. Saves
become browser downloads, landing wherever your browser puts them:

|File|Triggered by|
|-|-|
|`<Case Name>.zip`|**Save Case**|
|`OrphanedBins.zip`|**Save Case** with parked bins|
|`<name>.png`|**Save Thumbnail** in the thumbnail editor - both apps|

You then move them into place yourself. **No backup is taken on this path** - backups
need to read and write without a dialog in between.

### Browser storage

Stored by the browser, per origin, on your machine only. Never transmitted.

|Store|Key|Contents|
|-|-|-|
|`localStorage`|`cc_cases_v1`|Every loaded case in full - bins, labels, notes, and images as base64 data URLs - plus any bins parked in the holding area. Rewritten on every change. Both apps.|
|`IndexedDB`|`cc_fs_v1`|The folder-access handle you granted. A permission token, not a path you can read back. Case Creator only.|

Because this is per origin, `localhost:6040` and `cases.home:6040` keep separate copies.
Clearing site data for an origin discards unsaved cases and the folder grant - anything
already saved into `Cases/` is untouched.

### Files you choose

|Trigger|What happens|
|-|-|
|Picking or dropping an image on a bin, or pasting into the thumbnail editor|Read into memory, scaled, and embedded in the case as a data URL. The original file is never modified, moved, or uploaded.|

### What never happens

- **No telemetry, analytics, tracking or error reporting.** There is no endpoint to send it to.
- **No accounts, no login, no credentials** stored or transmitted.
- **Nothing is ever deleted.** Not old backups, not orphaned bins, not cases. Every removal is a manual job.
- **Nothing outside the granted folder is touched.** The browser enforces the boundary.
- **No server-side code.** Both apps are static files; the web server only ever serves them.

### Tools/make-index.bat and Tools/make-index.ps1

Two optional Windows helpers living in `Tools/`, beside `Cases/` rather than inside it,
so `Cases/` holds nothing but case data. Both are development tools - there is no
reason to copy them to a server.

`make-index.bat` is a one-line launcher that runs the PowerShell script beside it. It
exists so the tool can be double-clicked.

`make-index.ps1` does the work. It targets the folder named by `$CasesFolder` in its
**USER SETTINGS** block, which resolves to `..\Cases` by default - one level up from
`Tools/`. Point it somewhere else if your layout differs; it stops with a clear error
rather than writing an empty index if the folder is missing.

|Action|Detail|
|-|-|
|**Reads**|The folder named by `$CasesFolder`, `..\Cases` by default. Filenames only, `*.zip`, **not recursive** - subfolders are ignored. The zips are never opened.|
|**Writes**|`index.html`, inside that Cases folder, overwriting any existing one. UTF-8 without BOM. Percent-encodes hrefs and HTML-escapes link text, so `&`, `#`, `%`, spaces and apostrophes survive.|
|**Deletes**|Nothing.|
|**Network**|None.|
|**Output**|Prints the zips it indexed, or a warning if it found none.|

Case Creator rebuilds `index.html` itself after every save when folder access is
granted, so this is now only needed for hand-copying files to Home Assistant, or when
you add zips without going through the app.

## Access and security

**There is no login.** Both apps open straight into the interface, and anyone who can
reach the URL can read - and in Case Creator, edit - the data.

This is deliberate. A login implemented in the page is decorative: the browser already
holds the data before any check runs, and the case zips can be fetched directly from
their URLs regardless. It offered no protection while adding a step to every visit, so
it was removed rather than left to imply a safety that was never there.

If the apps need to be reachable from outside your network, put real authentication in
front of the folder - NGINX Proxy Manager basic auth, Authelia, a Cloudflare Access
policy, or a VPN. That is server-side and actually enforces something. Serving them
from behind Home Assistant's own login works the same way.

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
loads instead. Remember the dashboard URL is not a folder; test the `/local/...` path.

**A case is missing, but its zip is sitting in `Cases/`** — `Cases/index.html` is
stale. It overrides the server's own directory listing, so a zip it doesn't name is
invisible, locally and on HA alike. This failure is silent; nothing is logged.
Save any case with folder access granted to rebuild it, or run `make-index.bat`. On HA,
copy the regenerated `index.html` up as well.

**`NetworkError`** — you opened the HTML by double-clicking it (`file://`). Browsers
block reading local files that way; it must be served over HTTP.

**The server worked for days, then stopped** — the scheduled task's **Stop the task if
it runs longer than** is still ticked. Create Basic Task sets it to 3 days by default
and Windows kills the server on schedule, silently. Untick it in the task's Properties
→ Settings tab.

**The server did not start at logon** — check `caseserver.log` / `caseserver.err.log`
beside the `.ps1`. Both missing means the task never ran at all: check Task
Scheduler's **Last Run Result** and whether the trigger is *At log on*. Task shows
success (`Last Run Result: 0`) but no logs and nothing listening on the port usually
means the `netsh http add urlacl` reservation (see "Start it automatically") hasn't
been run — `HttpListener` fails to bind under a non-admin account without it.

**Cases vanish after reload** — they were never saved into `Cases/`. Save each case
as a zip and copy it to the folder.

**Changes don't appear** — hard-refresh (`Ctrl+Shift+R`). HA caches `/local/`
aggressively; appending `?v=2` to the URL also works.

---

# Case Creator — specifics

Authoring app. Everything Case Lookup does, plus creating and editing cases.

![Case Creator](.github/screenshots/builder.png)

## Tabs

|Tab|What it does|
|-|-|
|Search|Find parts by name, bin label, or note. Shows thumbnail, 2D grid, 3D view. The **Find Empty** button here lists free cells per case — hover a result to x-ray the case and see them.|
|Case Creator|Create/edit cases: draw bins, resize, colour-code levels, add notes.|
|View Cases|Browse any loaded case level by level.|
|Cases Folder|Folder status, skipped zips, a **Reload from folder** button, and **Grant folder access** — see [Local folder access](#local-folder-access).|
|Thumbnail Editor|Crop, layer, and edit case and bin images.|
|Help|In-app guide with animated demos.|

## Thumbnail editor

Every case and every bin can carry its own image. The thumbnail editor is a small
layered image editor built into Case Creator — no external tool needed to crop a
product photo down to something that reads at 100px.

![Thumbnail editor](.github/screenshots/thumbnail-editor.png)

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

## Holding area

A collapsible strip under the case grid, for rearranging a full case without bins
overwriting each other on the way past.

- Drag a bin off the grid and drop it on the strip. It leaves the case and is parked:
  size is kept, row, column and levels are discarded.
- Drag it back onto the grid to place it again. The drop is refused if it would
  overlap a bin already there.
- Click a parked bin to edit its label, notes and picture in the panel on the right.
  Position and Levels occupied are hidden, because a parked bin has neither. With
  nothing selected the panel reads *Locked*.
- Right-click a parked bin to delete it. Drag within the strip to reorder.
- Parked bins are stored with the case in browser storage, so they survive a reload.
  They are **not** written into the case zip.

### Show Orphaned Parts

Tick this in the open strip to load every part from `OrphanedBins/OrphanedBins.zip`
alongside the parked bins. They are packed into the same grid, growing downwards as
needed, and are editable like any parked bin. Drag one onto the grid to adopt it into
the case — it is removed from the orphan list on the next save.

## Orphaned bins

`OrphanedBins/OrphanedBins.zip` is a global parking file with the same layout as
a case zip:

```
OrphanedBins/OrphanedBins.csv
OrphanedBins/Images/<part>.png
```

The CSV keeps the standard columns but writes `row`, `col` and `levels` empty — an
orphan carries no grid position out of the case it came from. `rowSpan` and `colSpan`
are kept so the part still has its shape.

It lives in a subfolder, so the normal `Cases/` scan never loads it as a case.

Saving a case that still has parked bins raises a warning with a **Yes / No** choice.
On Yes the parked bins are merged into `OrphanedBins.zip` — parts already there
(matched on label **and** notes) are skipped — the holding area is emptied, and the
case is written.

## Backups

Immediately before a case zip is overwritten, the copy already on disk is duplicated to:

```
Backup/<Case Name>-<W>x<H>_dd_mm_yyyy.bak
```

**This happens on every save.** It has nothing to do with the holding area or orphaned
bins — those are a separate step in the same save. What decides it:

|Situation|Backed up?|
|-|-|
|Folder access granted, the case already exists in `Cases/`|Yes, every save|
|Folder access granted, brand-new case never saved before|No — there is nothing to copy|
|No folder access, so the save is a download|**No, never**|

The stamp is the date, not the time, so saving the same case twice in one day
overwrites that day's backup. You get **one backup per case per calendar day you edit
it** — not one per save.

### Housekeeping

**Nothing prunes `Backup/` — clearing it out is a manual job.** There is no
retention limit and no age cutoff, by design: the app never deletes your data.

Growth is roughly one case-sized zip per case per active day. Case zips run about 1 MB
each (images dominate the size), so a day spent editing three cases costs ~3 MB. That
is slow enough to ignore for months, but it never stops.

**Recommended:** open `Backup/` every few months, sort by date, and delete
everything older than the last few entries per case. Filenames sort naturally into
per-case groups, so it is quick to scan:

```
Craft-9x6_02_08_2026.bak
Craft-9x6_17_08_2026.bak        <- keep
Hardware-9x6_09_09_2026.bak     <- keep
Hardware-9x6_28_07_2026.bak
```

Keep at least the most recent one for any case you still care about. A `.bak` is a
plain case zip, so a backup you delete is gone — check the current case in `Cases/`
opens correctly before clearing its history.

### Restoring from a backup

A `.bak` is an ordinary case zip with a different extension. Nothing inside it needs
editing — the case name comes from the `#case` line in the CSV, not from any filename.

**To roll a case back**, replacing what is there now:

1. Copy `Backup/Hardware-9x6_09_09_2026.bak` into `Cases/`
2. Rename it to `Hardware-9x6.zip`, replacing the current file
3. Reload the app

That is the whole process. Do not rename anything inside the zip.

**To load a backup alongside the current case**, for comparison:

1. Copy the `.bak` into `Cases/` and rename it to `Hardware-restored.zip`
2. Open the zip and edit the `.csv` — change `#case,Hardware,9,6` to
   `#case,Hardware restored,9,6`
3. Reload

Step 2 matters. Two cases sharing a name load as *Hardware* and *Hardware (2)*, and the
suffix is assigned by filename order, so it is not obvious which is which. The internal
folder and CSV filenames can stay as they are — only the `#case` line decides the name.

**If the restored case does not appear**, `Cases/index.html` is stale — see
[Troubleshooting](#troubleshooting).

## Local folder access

By default the browser can only *download* a saved case — it can't write into `Cases/`,
create backups, or update `OrphanedBins.zip`.

**Cases Folder → Grant folder access** fixes that. Pick the folder holding
`CaseCreator.dc.html` and its `Cases` subfolder; from then on saves, backups and
orphaned bins are written straight to disk with no download prompt.

- Chrome and Edge on the desktop only. Firefox and Safari fall back to downloads.
- **The URL must be `localhost` or HTTPS.** The browser only exposes this API on a
  secure origin, so `http://cases.home:6040` cannot use it no matter which browser
  you open it in — you get the download fallback and no backups. Author on
  `http://localhost:6040/` and use the hostname for lookups.
- The permission is remembered, but the browser asks you to reconfirm it once per
  browser restart — click **Re-grant folder access** and pick the same folder.
- Without it everything still works, it just downloads instead: you move the files into
  `Cases/`, `Backup/` and `OrphanedBins/` yourself.

## Saving a case

**Save Case** writes straight into `Cases/`, takes a dated backup first, flushes any
parked bins, and rebuilds the file index — provided
[folder access](#local-folder-access) is granted. Without it the zip is downloaded
instead and you move it into `Cases/` yourself, with no backup taken.

Cases you create in the browser but haven't got into `Cases/` yet live in that
browser's local storage and appear alongside the folder cases. A folder case with the
same name wins on reload. There is no manual import — the folder is the only way in.

---

# Case Lookup — specifics

Read-only inventory terminal. Search across every bin in every case, or browse a case
grid visually. No editing, no builder, no thumbnail editor — pair it with Case Creator
for authoring.

Two tabs only: **Search** (including Find Empty) and **View Cases**.
