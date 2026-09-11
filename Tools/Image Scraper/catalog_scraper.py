#!/usr/bin/env python3
"""
catalog_scraper.py — image fetcher for parts-catalog grid CSVs

Reads a parts-catalog grid CSV (the format exported from grid layout
tools like "Hardware-9x6.csv" or "Electronics-9x6.csv" — works for any
category: hardware, electronics, or anything else laid out the same
way) and, for each row, finds up to IMAGES_PER_ROW product images for
the `label` column via a Bing image crawl (icrawler) and saves them
locally, numbered -1, -2, -3... appended to the filename given in the
`image` column. Only candidates that already have a genuinely white,
opaque, neutral background are accepted (see REQUIRE_WHITE_BG below) —
so accepted images are saved directly, with no cutout/compositing step.

Example: label "M3 Locknut" with image "M3-Locknut.png" and
IMAGES_PER_ROW = 5 produces:
    M3-Locknut-1.png
    M3-Locknut-2.png
    M3-Locknut-3.png
    M3-Locknut-4.png
    M3-Locknut-5.png
(fewer if not enough qualifying candidates are found)

RUN THIS ON YOUR OWN MACHINE, NOT IN A SANDBOXED ENVIRONMENT.
It needs normal internet access to reach Bing and various image hosts.

Images are saved under OUTPUT_BASE_DIR/<csv filename>/, e.g. switching
CSV_PATH from "Hardware-9x6.csv" to "Fasteners-v2.csv" automatically
saves into a separate "Fasteners-v2" subfolder, so sets from different
CSVs never mix.

------------------------------------------------------------------
SETUP
------------------------------------------------------------------
pip install requests pillow icrawler tqdm

tqdm gives you a live progress bar in the terminal; it's optional —
the script runs fine without it, just with plain row-by-row printing
instead.

No API key or account signup needed.

------------------------------------------------------------------
USAGE
------------------------------------------------------------------
Edit the CONFIG block below (CSV_PATH, OUTPUT_DIR, IMAGES_PER_ROW, etc.)
to match your setup, then just press F5 in VS Code or run:

    python catalog_scraper.py

No arguments needed — everything is read from CONFIG.

Optional: any CLI flag overrides the matching CONFIG value for a single
run, e.g.:

    python catalog_scraper.py --limit 5
    python catalog_scraper.py --dry-run
    python catalog_scraper.py --images-per-row 3
    python catalog_scraper.py other.csv --outdir D:/out

Images below 200x200px are rejected in favor of the next candidate
(MIN_SIZE_PX in CONFIG, or --min-size). Candidates without a white,
OPAQUE, color-NEUTRAL background are also rejected (REQUIRE_WHITE_BG /
WHITE_BG_TOLERANCE / WHITE_BG_MAX_CHANNEL_DIFF in CONFIG, or
--no-white-bg / --white-tolerance / --white-max-diff) — this
deliberately excludes transparent cutout PNGs (not just non-white ones)
and color-tinted "whites" (e.g. a cool-lit background with a slight
blue hue), which a brightness-only check would miss. Rows where every
candidate fails one of these checks are reported at the end for manual
follow-up ("too-small", "not-white-bg", "failed-processing"). There is
no separate post-processing/cutout step — an accepted candidate is
saved exactly as downloaded, since it's already been verified white.

SEARCHING BY NOTES: some CSVs have model/serial numbers in the `notes`
column, e.g. "DIN985, ISO10511" — a comma-separated list, one term per
segment. Set SEARCH_FIELDS in CONFIG (or pass --search-fields) to
control what the search query is built from:

    SEARCH_FIELDS = {"label"}            # search ALL rows, using label
    SEARCH_FIELDS = {"notes"}            # search ONLY rows that have notes;
                                          # rows with no notes are skipped
                                          # entirely, not searched at all
    SEARCH_FIELDS = {"label", "notes"}   # search ALL rows; label + notes
                                          # combined where notes exist,
                                          # label alone otherwise

Rows skipped because SEARCH_FIELDS = {"notes"} finds no notes are
reported at startup ("Skipping N row(s) with no notes") and don't count
against the end-of-run summary.

PER-TERM SPLITTING: when a row's notes have MULTIPLE comma-separated
terms, each term is treated as its own item — its own filename (the
term itself, sanitized) and its own search query — rather than being
blended into one combined query. E.g. a row labeled "Audio Boards" with
notes "PAM8403 Amplifier, KA2284 Indicator" produces two separate,
independently-searched image sets:
    PAM8403-Amplifier-1.png ... PAM8403-Amplifier-5.png
    KA2284-Indicator-1.png ... KA2284-Indicator-5.png
A row with just one note term (or no notes, or SEARCH_FIELDS excluding
notes) still produces a single image set named after the label as usual.

RESUMING: each numbered file is checked independently. If a row already
has all IMAGES_PER_ROW files, the whole row is skipped. If it has some
but not all (e.g. you increased IMAGES_PER_ROW after an earlier run),
only the missing numbers are fetched — existing numbered files are left
untouched.

NOTE ON RE-RUNS: search results and candidate order are the same every
time for a given query, and normal runs always fill numbered slots in
that same order — so clearing the output folder and re-running gives
you back the same set of images. To swap out just ONE numbered image
you don't like, use --reroll with the exact label and the number:

    python catalog_scraper.py --reroll "M3 Locknut" --reroll-index 2

This deletes only M3-Locknut-2.png and refills it with a random
qualifying candidate that isn't already used by the other numbered
files for that row. Omit --reroll-index to reroll ALL numbered files
for that label at once.

For a row that split into multiple note-term targets, add --reroll-term
to target just one of them:

    python catalog_scraper.py --reroll "Audio Boards" --reroll-term "KA2284 Indicator"

Omit --reroll-term to reroll every term's images for that label.
"""

import argparse
import csv
import io
import random
import re
import sys
import time
import traceback
from pathlib import Path

import requests
from PIL import Image

try:
    from tqdm import tqdm
    HAVE_TQDM = True
except ImportError:
    HAVE_TQDM = False

# =======================================================================
# CONFIG — edit these to your setup. This lets the script run with F5
# in VS Code (or a plain double-click) with no arguments needed at all.
# CLI flags, if you do use the terminal, override these defaults.
# =======================================================================

SCRIPT_DIR = Path(__file__).resolve().parent

CSV_PATH = SCRIPT_DIR / "Random.csv"   # CSV file to read
OUTPUT_BASE_DIR = SCRIPT_DIR / "images"      # images are saved under
                                              # OUTPUT_BASE_DIR / <csv filename>,
                                              # e.g. images/Hardware-9x6/...
                                              # so switching CSVs keeps sets separate
LIMIT = None                                 # e.g. 5 to test on first 5 rows, None for all
DRY_RUN = False                              # True = print queries only, no downloads
SLEEP_SECONDS = 1.0                          # pause between rows (be polite to Bing)
IMAGES_PER_ROW = 5                           # how many numbered images to save per label
CANDIDATES_PER_ROW = 15                      # images to fetch per row before giving up
                                              # (higher than IMAGES_PER_ROW to allow for
                                              # failures / too-small rejects)
MIN_SIZE_PX = 200                            # reject images smaller than this (w or h)
REQUIRE_WHITE_BG = True                       # reject candidates whose corners aren't white
WHITE_BG_TOLERANCE = 25                       # how far below 255 a channel can be (0-255,
                                              # lower = stricter, e.g. 0 demands pure white)
WHITE_BG_MAX_CHANNEL_DIFF = 12                # max gap between the brightest and dimmest of
                                              # R/G/B at a corner (0-255); catches color casts
                                              # (e.g. a "slight blue hue") that WHITE_BG_TOLERANCE
                                              # alone misses since it only checks brightness, not
                                              # color neutrality. Lower = stricter about tints;
                                              # 0 demands perfectly neutral gray/white.

# Which CSV columns to build the search query from. Valid values are
# "label" and "notes" — set includes either or both:
#   {"label"}            -> search ALL rows, using the `label` column (default)
#   {"notes"}            -> search ONLY rows that have notes; rows with
#                            no notes are skipped entirely (not searched)
#   {"label", "notes"}   -> search ALL rows; combine label + notes where
#                            notes exist, label alone otherwise
# `notes` is expected in the form "term one, term two, term three" — each
# comma-separated segment (e.g. a model or serial number) is treated as
# its own search term.
SEARCH_FIELDS = {"label", "notes"}

# =======================================================================

# ---------------------------------------------------------------------
# Query construction
# ---------------------------------------------------------------------

# Matches labels like "M4 10mm", "M6 45mm >", "M3 8mm"
SCREW_PATTERN = re.compile(r"^M\d+\s+\d+\s*mm\b", re.IGNORECASE)

# Labels too vague for a direct image search — these get a broader,
# hand-tuned query instead of "<label> hardware component".
MANUAL_QUERY_OVERRIDES = {
    "M3 Threads": "M3 threaded rod hardware",
    "M8 Misc": "M8 bolts and nuts assortment",
    "Misc Washers": "assorted washers hardware",
    "Misc Imperial": "imperial screws assortment",
    "PC Screws etc": "PC case screws standoffs kit",
    "Screws Large": "assorted large screws",
    "EZ Connect": "EZ connect cable connector hardware",
}


def clean_label(label: str) -> str:
    """Strip trailing row-continuation markers like ' >' from labels."""
    return label.replace(" >", "").strip()


def build_query(label: str) -> str:
    label = clean_label(label)
    if label in MANUAL_QUERY_OVERRIDES:
        return MANUAL_QUERY_OVERRIDES[label]
    if SCREW_PATTERN.match(label):
        return f"{label} machine screw"
    return f"{label} hardware component"


VALID_SEARCH_FIELDS = {"label", "notes"}


def normalize_search_fields(fields) -> set:
    """Validate a SEARCH_FIELDS-style value (set/list/string), falling
    back to {"label"} if it's empty or contains nothing recognized."""
    if isinstance(fields, str):
        fields = fields.split(",")
    fields = {str(f).strip().lower() for f in fields if str(f).strip()}
    fields = fields & VALID_SEARCH_FIELDS
    return fields or {"label"}


def parse_notes(notes: str) -> list:
    """Split a notes field like 'this, is, a, note' into individual
    search terms: ['this', 'is', 'a', 'note']. Empty segments and
    surrounding whitespace are dropped."""
    if not notes:
        return []
    return [term.strip() for term in notes.split(",") if term.strip()]


def has_notes(row: dict) -> bool:
    """True if this row has at least one usable (non-blank) notes term."""
    return bool(parse_notes(row.get("notes", "")))


def row_is_searchable(row: dict, fields: set) -> bool:
    """
    Whether a row should be processed at all under the current
    SEARCH_FIELDS:
      {"label"}            -> any row with a label
      {"notes"}            -> only rows that actually have notes
      {"label", "notes"}   -> any row with a label (notes used if present)
    """
    if not row.get("label", "").strip():
        return False
    if fields == {"notes"}:
        return has_notes(row)
    return True


def assemble_query(row: dict, fields: set) -> str:
    """
    Build the final search query for a row according to SEARCH_FIELDS:
      {"label"}          -> the usual label-based query
      {"notes"}          -> notes terms joined into one query
      {"label", "notes"} -> label-based query + notes terms appended
    Returns "" if fields == {"notes"} and the row has no usable notes —
    callers should skip such rows via row_is_searchable() before ever
    calling this, but the empty-string case is handled safely regardless.
    """
    label = row.get("label", "").strip()
    notes_terms = parse_notes(row.get("notes", "")) if "notes" in fields else []

    parts = []
    if "label" in fields:
        parts.append(build_query(label))
    if notes_terms:
        parts.append(" ".join(notes_terms))

    return " ".join(parts).strip()


def build_term_query(label: str, term: str, fields: set) -> str:
    """Query for a single note-term target: label context + the term
    itself if 'label' is part of SEARCH_FIELDS, otherwise just the term."""
    if "label" in fields:
        return f"{build_query(label)} {term}".strip()
    return term


def get_row_targets(row: dict, fields: set) -> list:
    """
    Decide what to search/save for a row, returning a list of
    (image_name, query) pairs:

      - If "notes" is part of SEARCH_FIELDS and the row has notes, each
        comma-separated note term becomes its OWN target: its own
        filename (the term itself, sanitized) and its own search query
        — so "Audio Boards" with 5 part numbers in notes produces 5
        separately-named, separately-searched image sets instead of one
        blended query saved under "Audio-Boards".
      - Otherwise, the row produces a single target using the usual
        image filename (derive_image_name) and query (assemble_query) —
        unchanged from prior behavior.
    """
    label = row.get("label", "").strip()

    if "notes" in fields and has_notes(row):
        terms = parse_notes(row.get("notes", ""))
        return [
            (f"{sanitize_filename(term)}.png", build_term_query(label, term, fields))
            for term in terms
        ]

    return [(derive_image_name(row), assemble_query(row, fields))]


def sanitize_filename(text: str) -> str:
    """Fallback filename sanitizer: spaces -> '-', strip anything else
    that isn't filesystem-safe (slashes, punctuation, etc.)."""
    text = re.sub(r"\s+", "-", text.strip())
    text = re.sub(r"[^\w\-]+", "-", text)
    text = re.sub(r"-{2,}", "-", text).strip("-")
    return text


def derive_image_name(row: dict) -> str:
    """
    Some CSV exports leave the `image` column blank. In that case, fall
    back to the `id` column (already sanitized in these exports, e.g.
    "7-8-Pin-Terminals" for label "7/8 Pin Terminals"), or as a last
    resort sanitize the label itself. Always returns a '.png' filename.
    """
    image = row.get("image", "").strip()
    if image:
        return image

    base = row.get("id", "").strip()
    if not base:
        base = sanitize_filename(clean_label(row.get("label", "")))

    return f"{base}.png"


def numbered_path(out_dir: Path, image_name: str, index: int) -> Path:
    """'M3-Locknut.png', 3 -> out_dir/'M3-Locknut-3.png'"""
    p = Path(image_name)
    return out_dir / f"{p.stem}-{index}{p.suffix}"


def log(msg: str):
    """Print a line without corrupting an active tqdm progress bar."""
    if HAVE_TQDM:
        tqdm.write(msg)
    else:
        print(msg)


# ---------------------------------------------------------------------
# Image search
# ---------------------------------------------------------------------

def search_icrawler(query: str, n: int) -> list:
    """Use icrawler (Bing) to grab candidate images into a temp folder
    and return their local paths, best-ranked first.

    Biases results toward "medium" size and up, toward images Bing
    itself tags as having a white color scheme, and toward "photo" type
    — explicitly excluding Bing's own "transparent" and "clipart"
    categories, since those are cutout/icon PNGs (often tagged "white"
    color despite having no real background at all) rather than actual
    white-background product photos. This is still a rough heuristic on
    Bing's end, so it's paired with a local corner-sampling check in
    fill_slots() as a second line of defense.
    """
    from icrawler.builtin import BingImageCrawler

    tmp_dir = Path("./_icrawler_tmp") / re.sub(r"[^a-zA-Z0-9]+", "_", query)
    tmp_dir.mkdir(parents=True, exist_ok=True)
    crawler = BingImageCrawler(storage={"root_dir": str(tmp_dir)}, log_level=50)
    crawler.crawl(
        keyword=query,
        max_num=n,
        file_idx_offset=0,
        filters={
            "size": "medium",   # excludes Bing's smallest thumbnails
            "color": "white",   # bias toward images Bing tags as white/light
            "type": "photo",    # excludes "transparent"/"clipart"/"linedrawing"/"animated"
        },
    )
    return sorted(tmp_dir.glob("*"))


# ---------------------------------------------------------------------
# Download + background handling
# ---------------------------------------------------------------------

def fetch_bytes(url: str) -> bytes:
    headers = {"User-Agent": "Mozilla/5.0 (compatible; ImageFetcher/1.0)"}
    resp = requests.get(url, headers=headers, timeout=15)
    resp.raise_for_status()
    return resp.content


def load_image(source) -> Image.Image:
    """source can be a URL (str) or a local Path."""
    if isinstance(source, str) and source.startswith("http"):
        raw = fetch_bytes(source)
        return Image.open(io.BytesIO(raw)).convert("RGBA")
    else:
        return Image.open(source).convert("RGBA")


def prepare_for_save(img: Image.Image) -> Image.Image:
    """
    By the time an image reaches here, has_white_background() has
    already verified it genuinely has a white, opaque, neutral
    background — so there's nothing left to fix. Just flatten to RGB
    and save as-is; no cutout/compositing step needed.
    """
    return img.convert("RGB")


def has_white_background(img: Image.Image, tolerance: int = 25, alpha_threshold: int = 250,
                          max_channel_diff: int = 12) -> bool:
    """
    Cheap local check for a genuinely (near-)white, OPAQUE, NEUTRAL
    background: samples a small patch at each of the four corners and
    checks they're all close to pure white, fully opaque, AND color-
    neutral (not tinted blue/yellow/etc). Not perfect (a white product
    photographed off-center could fail this), but a good, fast filter
    for typical product shots where the background fills the corners.

    Checking opacity matters: many transparent cutout PNGs have their
    underlying RGB data already set to white even in fully-transparent
    areas (a common export artifact), so an RGB-only check would
    wrongly accept them as "white background" when they actually have
    no background at all. Requiring alpha >= alpha_threshold at the
    corners filters those out.

    Checking neutrality matters too: a corner like (235, 235, 250) has
    every channel bright enough to pass a brightness-only check, but the
    10-15pt gap toward blue is exactly what reads as a "slight blue hue"
    to the eye — common in studio product photos with cool-white
    lighting. Requiring max(R,G,B) - min(R,G,B) <= max_channel_diff
    catches that even when every individual channel is bright enough.

    tolerance: how far below 255 an RGB channel can be and still count
    as "white" (e.g. 25 accepts down to RGB ~230).
    alpha_threshold: minimum average alpha (0-255) for a corner to count
    as opaque; images with no alpha channel are always fully opaque.
    max_channel_diff: max allowed gap between the brightest and dimmest
    of R/G/B at a corner (0-255); lower = stricter about color casts
    like blue/yellow/pink tints. 0 demands perfectly neutral gray/white.
    """
    rgba = img.convert("RGBA")
    w, h = rgba.size
    patch = max(1, min(w, h) // 20)

    corners = [
        rgba.crop((0, 0, patch, patch)),
        rgba.crop((w - patch, 0, w, patch)),
        rgba.crop((0, h - patch, patch, h)),
        rgba.crop((w - patch, h - patch, w, h)),
    ]

    white_corners = 0
    for corner in corners:
        pixels = list(corner.getdata())
        if not pixels:
            continue
        avg = [sum(channel) / len(pixels) for channel in zip(*pixels)]
        r, g, b, a = avg
        is_opaque = a >= alpha_threshold
        is_bright = all(v >= 255 - tolerance for v in (r, g, b))
        is_neutral = (max(r, g, b) - min(r, g, b)) <= max_channel_diff
        if is_opaque and is_bright and is_neutral:
            white_corners += 1

    return white_corners >= 3  # at least 3 of 4 corners must read as white


def fill_slots(candidates, slot_paths, min_size: int = 200, randomize: bool = False,
               require_white_bg: bool = True, white_tolerance: int = 25, white_max_diff: int = 12):
    """
    Given a list of candidate image sources and a list of destination
    paths ("slots"), process candidates in order and save each
    successfully-processed, size-qualifying, (optionally) white-background
    candidate into the next empty slot, until slots run out or candidates
    run out.

    Returns (saved_count, saw_too_small: bool, saw_failure: bool,
    saw_not_white: bool).

    By default candidates are tried in Bing's own ranked order, so a
    normal run is deterministic — clearing the output folder and
    re-running with the same query fills the same slots with the same
    pictures. Pass randomize=True to shuffle the order instead (used by
    --reroll).
    """
    candidates = list(candidates)
    if randomize:
        random.shuffle(candidates)

    saved_count = 0
    saw_too_small = False
    saw_failure = False
    saw_not_white = False
    slot_idx = 0

    for cand in candidates:
        if slot_idx >= len(slot_paths):
            break
        try:
            img = load_image(cand)
            if img.width < min_size or img.height < min_size:
                saw_too_small = True
                continue
            if require_white_bg and not has_white_background(img, tolerance=white_tolerance, max_channel_diff=white_max_diff):
                saw_not_white = True
                continue
            final = prepare_for_save(img)
            final.save(slot_paths[slot_idx])
            slot_idx += 1
            saved_count += 1
        except Exception:
            saw_failure = True
            continue

    return saved_count, saw_too_small, saw_failure, saw_not_white


# ---------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("csv_path", nargs="?", default=None,
                     help=f"Path to the parts-catalog CSV file (default: {CSV_PATH})")
    ap.add_argument("--outdir", default=None,
                     help=f"Base output directory; images go in <outdir>/<csv filename>/ "
                          f"(default base: {OUTPUT_BASE_DIR})")
    ap.add_argument("--limit", type=int, default=None, help="Only process first N rows")
    ap.add_argument("--dry-run", action="store_true", default=None, help="Print queries only, no downloads")
    ap.add_argument("--sleep", type=float, default=None, help="Seconds to sleep between rows")
    ap.add_argument("--images-per-row", type=int, default=None,
                     help="How many numbered images to save per label")
    ap.add_argument("--candidates", type=int, default=None, help="Images to fetch per row before giving up")
    ap.add_argument("--min-size", type=int, default=None, help="Minimum width/height in pixels")
    ap.add_argument("--no-white-bg", action="store_true", default=None,
                     help="Disable the white-background requirement (accept any background)")
    ap.add_argument("--white-tolerance", type=int, default=None,
                     help="How far below 255 a channel can be and still count as white (0-255)")
    ap.add_argument("--white-max-diff", type=int, default=None,
                     help="Max gap between brightest/dimmest of R,G,B at a corner (0-255); "
                          "lower = stricter about color casts/tints like a blue hue")
    ap.add_argument("--search-fields", default=None,
                     help="Comma-separated: 'label', 'notes', or 'label,notes' "
                          "(default from SEARCH_FIELDS in CONFIG)")
    ap.add_argument("--reroll", metavar="LABEL", default=None,
                     help="Delete existing numbered image(s) for this exact label and fetch "
                          "fresh, randomly-picked replacement(s) (leaves other rows untouched).")
    ap.add_argument("--reroll-index", type=int, default=None,
                     help="With --reroll, only replace this one numbered image (e.g. 2 for "
                          "'-2.png'). Omit to reroll all numbered images for that label.")
    ap.add_argument("--reroll-term", default=None,
                     help="With --reroll on a row whose notes split into multiple targets, "
                          "only reroll the target matching this note term (e.g. 'PAM8403'). "
                          "Omit to reroll every term's images for that label.")
    args = ap.parse_args()

    # CLI values override CONFIG defaults; if a flag wasn't passed, fall
    # back to the CONFIG block at the top of the file.
    csv_path = Path(args.csv_path) if args.csv_path else CSV_PATH
    out_base = Path(args.outdir) if args.outdir else Path(OUTPUT_BASE_DIR)
    limit = args.limit if args.limit is not None else LIMIT
    dry_run = args.dry_run if args.dry_run is not None else DRY_RUN
    sleep_seconds = args.sleep if args.sleep is not None else SLEEP_SECONDS
    images_per_row = args.images_per_row if args.images_per_row is not None else IMAGES_PER_ROW
    candidates_per_row = args.candidates if args.candidates is not None else CANDIDATES_PER_ROW
    min_size = args.min_size if args.min_size is not None else MIN_SIZE_PX
    require_white_bg = (not args.no_white_bg) if args.no_white_bg is not None else REQUIRE_WHITE_BG
    white_tolerance = args.white_tolerance if args.white_tolerance is not None else WHITE_BG_TOLERANCE
    white_max_diff = args.white_max_diff if args.white_max_diff is not None else WHITE_BG_MAX_CHANNEL_DIFF
    search_fields = normalize_search_fields(args.search_fields) if args.search_fields else normalize_search_fields(SEARCH_FIELDS)

    if not csv_path.exists():
        print(f"ERROR: CSV file not found: {csv_path}")
        print("Edit CSV_PATH in the CONFIG block at the top of this script, "
              "or pass a path as the first argument.")
        return

    # Images are saved under <out_base>/<csv filename stem>/ so switching
    # between CSVs keeps each set of images clearly separated and traceable
    # back to the source file.
    out_dir = out_base / csv_path.stem
    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"Saving images to: {out_dir}")
    print(f"Searching using: {'+'.join(sorted(search_fields))}")

    if not HAVE_TQDM:
        print("(tip: `pip install tqdm` for a progress bar — running without one for now)")

    # Read rows, skipping the '#'-prefixed metadata lines at the top.
    with open(csv_path, newline="", encoding="utf-8") as f:
        lines = [line for line in f if not line.startswith("#")]
    reader = csv.DictReader(lines)
    rows = list(reader)

    # -------------------------------------------------------------
    # --reroll: handle one label and exit
    # -------------------------------------------------------------
    if args.reroll:
        target = clean_label(args.reroll)
        match = next(
            (r for r in rows if clean_label(r.get("label", "")) == target),
            None,
        )
        if not match:
            print(f"ERROR: no row with label {args.reroll!r} found in {csv_path.name}")
            return

        if not row_is_searchable(match, search_fields):
            print(f"ERROR: {args.reroll!r} has no notes, and SEARCH_FIELDS is {{'notes'}} only "
                  f"— nothing to search on for this row. Use --search-fields label (or "
                  f"label,notes) to reroll it, or add notes to the CSV.")
            return

        label = match["label"].strip()
        row_targets = get_row_targets(match, search_fields)

        if args.reroll_term:
            wanted = sanitize_filename(args.reroll_term).lower()
            filtered = [t for t in row_targets if Path(t[0]).stem.lower() == wanted]
            if not filtered:
                available = [Path(t[0]).stem for t in row_targets]
                print(f"ERROR: no note term matching {args.reroll_term!r} found for {label!r}. "
                      f"Available terms: {available}")
                return
            row_targets = filtered

        index_targets = [args.reroll_index] if args.reroll_index is not None else list(range(1, images_per_row + 1))

        for image_name, query in row_targets:
            base_name = Path(image_name).stem
            slot_paths = [numbered_path(out_dir, image_name, i) for i in index_targets]
            display_label = f"{label} [{base_name}]" if len(row_targets) > 1 else label

            print(f"Rerolling {display_label!r} slots {index_targets} -> query: {query!r}")
            for p in slot_paths:
                if p.exists():
                    p.unlink()
                    print(f"    removed {p.name}")

            candidates = search_icrawler(query, n=max(candidates_per_row, len(slot_paths) * 3))
            if not candidates:
                print("    no results found")
                continue

            saved, too_small, failure, not_white = fill_slots(
                candidates, slot_paths, min_size=min_size, randomize=True,
                require_white_bg=require_white_bg, white_tolerance=white_tolerance, white_max_diff=white_max_diff,
            )
            print(f"    saved {saved}/{len(slot_paths)} image(s)")
            if saved < len(slot_paths):
                if too_small:
                    print(f"    some candidates were under {min_size}x{min_size}px")
                if not_white:
                    print("    some candidates didn't have a white background")
                if failure:
                    print("    some candidates failed to load/process")
        return

    # -------------------------------------------------------------
    # Normal bulk run
    # -------------------------------------------------------------
    if limit:
        rows = rows[:limit]

    all_labeled_rows = [r for r in rows if r.get("label", "").strip()]
    valid_rows = [r for r in all_labeled_rows if row_is_searchable(r, search_fields)]
    skipped_no_notes = len(all_labeled_rows) - len(valid_rows)

    if skipped_no_notes:
        print(f"Skipping {skipped_no_notes} row(s) with no notes "
              f"(SEARCH_FIELDS={{'notes'}} only searches rows that have notes)")

    results = []
    bar = tqdm(valid_rows, desc="Fetching", unit="row", file=sys.stdout) if HAVE_TQDM else valid_rows

    for i, row in enumerate(bar, 1):
        row_label = row["label"].strip()
        targets = get_row_targets(row, search_fields)
        multi = len(targets) > 1

        if HAVE_TQDM:
            bar.set_postfix_str(row_label[:30])

        for image_name, query in targets:
            slot_paths = [numbered_path(out_dir, image_name, n) for n in range(1, images_per_row + 1)]
            base_name = Path(image_name).stem
            # When a row splits into multiple note-term targets, disambiguate
            # each one in logs/summary as "Label [term]"; otherwise just "Label".
            display_label = f"{row_label} [{base_name}]" if multi else row_label

            if dry_run:
                log(f"[{i}/{len(valid_rows)}] {display_label!r} -> query: {query!r} "
                    f"-> {base_name}-1..{images_per_row}")
                continue

            if not HAVE_TQDM:
                print(f"[{i}/{len(valid_rows)}] {display_label!r} -> query: {query!r} "
                      f"-> {base_name}-1..{images_per_row}")

            missing_slots = [p for p in slot_paths if not p.exists()]
            if not missing_slots:
                results.append((display_label, "skipped-exists"))
                continue

            try:
                candidates = search_icrawler(query, n=candidates_per_row)

                if not candidates:
                    log(f"  {display_label!r}: no results found")
                    results.append((display_label, "no-results"))
                    continue

                saved, too_small, failure, not_white = fill_slots(
                    candidates, missing_slots, min_size=min_size,
                    require_white_bg=require_white_bg, white_tolerance=white_tolerance, white_max_diff=white_max_diff,
                )
                got_all = saved >= len(missing_slots)

                if got_all:
                    status = "ok"
                elif saved > 0:
                    status = "partial"
                elif too_small:
                    status = "too-small"
                elif not_white:
                    status = "not-white-bg"
                else:
                    status = "failed-processing"
                results.append((display_label, status))

                if not got_all:
                    detail = []
                    if too_small:
                        detail.append(f"some under {min_size}x{min_size}px")
                    if not_white:
                        detail.append("some lacked a white background")
                    if failure:
                        detail.append("some failed to load/process")
                    log(f"  {display_label!r}: saved {saved}/{len(missing_slots)} — "
                        f"{', '.join(detail) or 'incomplete'}")

            except Exception as e:
                log(f"  {display_label!r}: ERROR — {e}")
                traceback.print_exc(limit=1)
                results.append((display_label, f"error: {e}"))

            time.sleep(sleep_seconds)

    if HAVE_TQDM:
        bar.close()

    # Summary
    print("\n--- Summary ---")
    failed = [r for r in results if r[1] not in ("ok", "skipped-exists")]
    print(f"Total rows processed: {len(results)}")
    print(f"Fully complete:       {len(results) - len(failed)}")
    print(f"Needs manual review:  {len(failed)}")
    if failed:
        print("\nRows needing manual attention:")
        for label, status in failed:
            print(f"  - {label}: {status}")


if __name__ == "__main__":
    main()