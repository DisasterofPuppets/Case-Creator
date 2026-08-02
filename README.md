# Case Creator + Case Lookup

Two apps that share one folder of case data.

* **Case Creator** (`CaseCreator.dc.html`) — full authoring: build cases, edit bins
and levels, edit thumbnails, search, and view cases in 2D/3D.
* **Case Lookup** (`CaseLookup.dc.html`) — read-only terminal: search and browse only.

Both read the same `Cases/*.zip` files and use the same login. You can deploy either
one alone, or both side by side in the same folder. Everything from **Files** down to
**Troubleshooting** applies to both; the two short app-specific sections at the end
cover only what differs.

## Files

|File|Required|Notes|
|-|-|-|
|`CaseCreator.dc.html`|for authoring|The full app.|
|`CaseLookup.dc.html`|for lookup only|The read-only app.|
|`support.js`|yes|Runtime. Must sit next to the HTML.|
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
See the HA section below.

## Running the server locally (Windows)

(I used a random port 6040, you can choose whatever you like.)

From a Command Prompt (`Win+R` → `cmd`) — not the Python interpreter:

```
python -m http.server 6040 --directory "K:\path\to\casecreator"
```

Then open `http://localhost:6040/CaseCreator.dc.html`
(or `.../CaseLookup.dc.html`).

Reachable from your phone on the same Wi-Fi at `http://<pc-ip>:6040/CaseCreator.dc.html`
(find the IP with `ipconfig`; allow the Windows Firewall prompt on private networks).

### Start it automatically

Save as `start-cases.bat` and put a shortcut to it in `shell:startup`:

```bat
@echo off
python -m http.server 6040 --directory "K:\path\to\casecreator"
```

For a server that runs before login, use Task Scheduler instead: trigger *At startup*,
action *Start a program* → `python`, arguments
`-m http.server 6040 --directory "K:\path\to\casecreator"`, and enable
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

## Sign in

**Default credentials: `admin` / `admin`**

Stored in the HTML as one base64 string of `username:password` — currently
`YWRtaW46YWRtaW4=` — so the password isn't sitting in the file as plain text.
"Keep me signed in" stores the credential on that device.

### Changing the credentials

1. Open any browser, press `F12`, go to the **Console** tab.
2. Run `btoa('newuser:newpassword')` with your own values.
3. Copy the quoted result, e.g. `bmV3dXNlcjpuZXdwYXNzd29yZA==`.
4. Search the HTML for `YWRtaW46YWRtaW4=` and replace **both** occurrences — one in
the `data-props` attribute, one in `cfgCred()`. Do this in each app you deploy.

After changing it, sign out on every device where you used "Keep me signed in" — the
saved token no longer matches and login will fail until you do.

### What this protects (and what it doesn't)

Base64 is encoding, not encryption — `atob('YWRtaW46YWRtaW4=')` reverses it instantly.
It keeps the password off the screen in View Source; it is not security.

More importantly, **any login that runs in the browser is decorative**: the page
already holds the data before the check happens, and the case zips can be fetched
straight from their URLs without ever seeing the login screen.

So: never put a password you use elsewhere in here. Treat this as a "keep the
household out of it" gate, not access control. For real protection, put the folder
behind NGINX Proxy Manager basic auth or another server-side login.

## Mobile

Single-column layout on phones, 16px inputs (prevents iOS zoom), 44–50px touch
targets, no horizontal page overflow. Search results stack thumbnail → grid → 3D
vertically. Case Creator switches at 760px with a two-column nav; Case Lookup at 720px.

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
