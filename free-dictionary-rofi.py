#!/usr/bin/env python3
from __future__ import annotations

import html
import json
import re
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import quote

import requests

API_BASE = "https://api.dictionaryapi.dev/api/v2/entries/en"
MAX_HISTORY = 200
PAGE_SIZE = 7
REQUEST_HEADERS = {"User-Agent": "free-dictionary-rofi/1.2"}

HISTORY_FILE = Path.home() / ".local" / "share" / "free-dictionary-rofi" / "history.txt"
CACHE_DIR = Path.home() / ".cache" / "free-dictionary-rofi"

# Dynamic Noctalia Theme Override
ROFI_THEME_OVERRIDE = (
    '@import "~/.config/rofi/noctalia.rasi"\n'
    "* { font: \"Iosevka Nerd Font 13\"; }\n"
    "window { transparency: \"real\"; width: 850px; border: 2px; border-radius: 9px; border-color: @border; background-color: #161306CC; padding: 16px; }\n"
    "mainbox { background-color: transparent; spacing: 10px; }\n"
    "inputbar { border-radius: 100%; }\n" # <--- This makes the search area cylindrical
    "textbox { text-color: @fg; background-color: transparent; padding: 4px; }\n"
    "listview { columns: 1; lines: 8; spacing: 5px; background-color: transparent; }\n"
    "element { border: 1px; border-radius: 6px; border-color: transparent; padding: 6px 10px; background-color: transparent; text-color: @fg; }\n"
    "element selected.normal { background-color: @accent; text-color: @accent-fg; border-color: @accent; }\n"
    "element-text { text-color: inherit; background-color: transparent; }\n"
)
ROFI_BASE = ["rofi", "-dmenu", "-i", "-matching", "fuzzy", "-theme-str", ROFI_THEME_OVERRIDE]


def normalize(text: str) -> str:
    return " ".join(text.split()).strip()


def as_text(value: Any) -> str:
    return normalize(value) if isinstance(value, str) else ""


def show_message(message: str) -> None:
    try:
        subprocess.run(
            ["rofi", "-theme-str", ROFI_THEME_OVERRIDE, "-e", message],
            text=True,
            capture_output=True,
        )
    except FileNotFoundError:
        print(message, file=sys.stderr)


def run_rofi(prompt: str, items: List[str], allow_custom: bool = True) -> Optional[str]:
    cmd = ROFI_BASE[:]
    if not allow_custom:
        cmd.append("-no-custom")

    try:
        proc = subprocess.run(
            cmd + ["-p", prompt],
            input="\n".join(items),
            text=True,
            capture_output=True,
        )
    except FileNotFoundError:
        show_message("rofi is not installed or is not available in PATH.")
        return None

    choice = proc.stdout.strip()
    return choice or None


def run_rofi_index(prompt: str, items: List[str]) -> Optional[int]:
    try:
        proc = subprocess.run(
            ROFI_BASE + ["-no-custom", "-format", "i", "-p", prompt],
            input="\n".join(items),
            text=True,
            capture_output=True,
        )
    except FileNotFoundError:
        show_message("rofi is not installed or is not available in PATH.")
        return None

    choice = proc.stdout.strip()
    if not choice:
        return None

    try:
        idx = int(choice)
    except ValueError:
        return None

    return idx if 0 <= idx < len(items) else None


def load_history() -> List[str]:
    if not HISTORY_FILE.exists():
        return []

    try:
        lines = HISTORY_FILE.read_text(encoding="utf-8", errors="replace").splitlines()
    except Exception:
        return []

    seen = set()
    history: List[str] = []

    for line in reversed(lines):
        term = normalize(line)
        if not term:
            continue
        key = term.casefold()
        if key in seen:
            continue
        seen.add(key)
        history.append(term)

    return history


def save_history(term: str) -> None:
    term = normalize(term)
    if not term:
        return

    HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)

    history = load_history()
    key = term.casefold()
    history = [item for item in history if item.casefold() != key]
    history.insert(0, term)
    history = history[:MAX_HISTORY]

    try:
        HISTORY_FILE.write_text("\n".join(history) + "\n", encoding="utf-8")
    except Exception:
        pass


def clean_html(raw: str) -> str:
    cleaned = re.sub(r"<[^>]+>", "", raw)
    cleaned = html.unescape(cleaned)
    return normalize(cleaned)


def get_cache_path(term: str) -> Path:
    safe_name = quote(term.lower(), safe="").replace("%", "_")
    return CACHE_DIR / f"{safe_name}.json"


def load_cached_entry(term: str) -> Optional[List[Dict[str, Any]]]:
    cache_file = get_cache_path(term)
    if not cache_file.exists():
        return None
    try:
        data = json.loads(cache_file.read_text(encoding="utf-8"))
        if isinstance(data, list) and data:
            return data
    except Exception:
        pass
    return None


def save_cached_entry(term: str, entries: List[Dict[str, Any]]) -> None:
    if not entries:
        return
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        cache_file = get_cache_path(term)
        cache_file.write_text(json.dumps(entries, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass


def clear_cache() -> None:
    if CACHE_DIR.exists():
        try:
            shutil.rmtree(CACHE_DIR)
        except Exception:
            pass


def fetch_from_api(term: str) -> Optional[List[Dict[str, Any]]]:
    url = f"{API_BASE}/{quote(term)}"
    try:
        resp = requests.get(url, headers=REQUEST_HEADERS, timeout=3.5)
        if resp.status_code == 200:
            data = resp.json()
            if isinstance(data, list) and data:
                return data
    except Exception:
        pass
    return None


def fetch_from_wiktionary(term: str) -> Optional[List[Dict[str, Any]]]:
    variants = [term]
    if term.lower() not in variants:
        variants.append(term.lower())
    if term.capitalize() not in variants:
        variants.append(term.capitalize())

    data = None
    matched_word = term
    for variant in variants:
        url = f"https://en.wiktionary.org/api/rest_v1/page/definition/{quote(variant)}"
        try:
            r = requests.get(url, headers=REQUEST_HEADERS, timeout=5)
            if r.status_code == 200:
                data = r.json()
                matched_word = variant
                break
        except requests.RequestException:
            continue

    if not data or "en" not in data:
        return None

    meanings: List[Dict[str, Any]] = []
    for item in data.get("en", []):
        pos = as_text(item.get("partOfSpeech"))
        defs: List[Dict[str, Any]] = []
        for d in item.get("definitions", []):
            raw_def = as_text(d.get("definition"))
            cleaned_def = clean_html(raw_def)
            if not cleaned_def:
                continue

            example = ""
            ex_list = d.get("parsedExamples") or d.get("examples") or []
            if ex_list:
                first = ex_list[0]
                if isinstance(first, dict):
                    example = clean_html(as_text(first.get("example")))
                elif isinstance(first, str):
                    example = clean_html(as_text(first))

            defs.append({
                "definition": cleaned_def,
                "example": example,
                "synonyms": [],
                "antonyms": [],
            })

        if defs:
            meanings.append({
                "partOfSpeech": pos,
                "definitions": defs,
            })

    if not meanings:
        return None

    phonetic = ""
    try:
        dm_url = f"https://api.datamuse.com/words?sp={quote(term)}&md=dr&ipa=1&max=1"
        dm_resp = requests.get(dm_url, timeout=2)
        if dm_resp.status_code == 200:
            dm_data = dm_resp.json()
            if dm_data and isinstance(dm_data, list):
                for tag in dm_data[0].get("tags", []):
                    if tag.startswith("ipa_pron:"):
                        phonetic = "/" + tag.split(":", 1)[1].strip() + "/"
                        break
    except Exception:
        pass

    return [{
        "word": matched_word,
        "phonetic": phonetic,
        "phonetics": [{"text": phonetic}] if phonetic else [],
        "origin": "",
        "meanings": meanings,
    }]


def fetch_entries(term: str) -> Optional[List[Dict[str, Any]]]:
    # 1. Local disk cache (fast and offline-friendly)
    cached = load_cached_entry(term)
    if cached:
        return cached

    # 2. Primary Free Dictionary API
    entries = fetch_from_api(term)
    if entries:
        save_cached_entry(term, entries)
        return entries

    # 3. Fast, reliable Wiktionary fallback
    entries = fetch_from_wiktionary(term)
    if entries:
        save_cached_entry(term, entries)
        return entries

    # 4. Check whether host is completely offline
    try:
        requests.get("https://en.wiktionary.org", timeout=3)
    except Exception:
        show_message("Network error:\n\nCould not reach dictionary services. Please check your internet connection.")
        return None

    return []


def build_rows(entries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []

    for entry in entries:
        word = as_text(entry.get("word"))
        phonetic = as_text(entry.get("phonetic"))
        origin = as_text(entry.get("origin"))
        phonetics = entry.get("phonetics", [])
        if not phonetic and isinstance(phonetics, list):
            for ph in phonetics:
                if isinstance(ph, dict) and ph.get("text"):
                    phonetic = as_text(ph.get("text"))
                    break

        meanings = entry.get("meanings", [])

        if not isinstance(meanings, list):
            continue

        for meaning in meanings:
            if not isinstance(meaning, dict):
                continue

            pos = as_text(meaning.get("partOfSpeech"))
            definitions = meaning.get("definitions", [])

            if not isinstance(definitions, list):
                continue

            for definition_block in definitions:
                if not isinstance(definition_block, dict):
                    continue

                definition = as_text(definition_block.get("definition"))
                example = as_text(definition_block.get("example"))
                synonyms = definition_block.get("synonyms", [])
                antonyms = definition_block.get("antonyms", [])

                rows.append(
                    {
                        "word": word,
                        "phonetic": phonetic,
                        "phonetics": phonetics,
                        "origin": origin,
                        "partOfSpeech": pos,
                        "definition": definition,
                        "example": example,
                        "synonyms": synonyms if isinstance(synonyms, list) else [],
                        "antonyms": antonyms if isinstance(antonyms, list) else [],
                    }
                )

    return rows


def preview_definition(text: str, width: int = 72) -> str:
    text = normalize(text)
    if not text:
        return "(no definition)"
    return textwrap.shorten(text, width=width, placeholder="...")


def format_row(row: Dict[str, Any]) -> str:
    pos = row.get("partOfSpeech", "") or "?"
    definition = preview_definition(str(row.get("definition", "")), width=76)
    return f"{pos:<14} | {definition}"


def format_detail(row: Dict[str, Any]) -> str:
    word = str(row.get("word", "")).strip() or "(unknown)"
    pos = str(row.get("partOfSpeech", "")).strip()
    phonetic = str(row.get("phonetic", "")).strip()
    definition = normalize(str(row.get("definition", "")))
    example = normalize(str(row.get("example", "")))
    origin = normalize(str(row.get("origin", "")))

    def fmt_list(label: str, items: Any, limit: int = 8) -> List[str]:
        if not isinstance(items, list):
            return []
        cleaned = [normalize(str(x)) for x in items if x is not None and normalize(str(x))]
        if not cleaned:
            return []
        shown = cleaned[:limit]
        suffix = "" if len(cleaned) <= limit else f" … (+{len(cleaned) - limit} more)"
        return [f"{label}: {', '.join(shown)}{suffix}"]

    parts: List[str] = [word]

    if pos:
        parts.append(f"Part of speech: {pos}")
    if phonetic:
        parts.append(f"Phonetic: {phonetic}")
    if origin:
        parts.extend(["", "Origin:", textwrap.fill(origin, width=76)])

    parts.extend(["", "Definition:", textwrap.fill(definition or "(no definition)", width=76)])

    if example:
        parts.extend(["", "Example:", textwrap.fill(example, width=76)])

    parts.extend(fmt_list("Synonyms", row.get("synonyms"), limit=10))
    parts.extend(fmt_list("Antonyms", row.get("antonyms"), limit=10))

    return "\n".join(parts)


def page_rows(rows: List[Dict[str, Any]], page: int) -> List[Dict[str, Any]]:
    start = page * PAGE_SIZE
    end = start + PAGE_SIZE
    return rows[start:end]


def page_menu_items(rows: List[Dict[str, Any]], page: int) -> List[str]:
    chunk = page_rows(rows, page)
    items = [format_row(row) for row in chunk]

    if page > 0:
        items.append("◀ Previous page")
    if (page + 1) * PAGE_SIZE < len(rows):
        items.append("Next page ▶")

    return items


def total_pages(item_count: int) -> int:
    return max(1, (item_count + PAGE_SIZE - 1) // PAGE_SIZE)


def choose_term() -> Optional[str]:
    if len(sys.argv) > 1:
        args = sys.argv[1:]
        if args[0] in {"--history", "-h"}:
            history = load_history()
            choice = run_rofi("Dictionary history", history, allow_custom=True)
            return normalize(choice) if choice else None
        if args[0] == "--clear-history":
            try:
                HISTORY_FILE.unlink(missing_ok=True)
            except Exception:
                pass
            show_message("History cleared.")
            return None
        if args[0] in {"--clear-cache", "-c"}:
            clear_cache()
            show_message("Cache cleared.")
            return None
        return normalize(" ".join(args))

    history = load_history()
    choice = run_rofi("Free Dictionary", history, allow_custom=True)
    return normalize(choice) if choice else None


def main() -> int:
    term = choose_term()
    if not term:
        return 0

    save_history(term)

    entries = fetch_entries(term)
    if entries is None:
        return 0
    if not entries:
        show_message(f"No results found for:\n\n{term}")
        return 0

    rows = build_rows(entries)
    if not rows:
        show_message(f"No usable definitions found for:\n\n{term}")
        return 0

    page = 0

    while True:
        menu_items = page_menu_items(rows, page)
        choice_idx = run_rofi_index(
            f"Free Dictionary ({page + 1}/{total_pages(len(rows))})",
            menu_items,
        )
        if choice_idx is None:
            return 0

        chunk = page_rows(rows, page)
        nav_idx = len(chunk)

        if page > 0 and choice_idx == nav_idx:
            page = max(0, page - 1)
            continue

        if (page + 1) * PAGE_SIZE < len(rows) and choice_idx == nav_idx + (1 if page > 0 else 0):
            if (page + 1) * PAGE_SIZE < len(rows):
                page += 1
            continue

        if choice_idx >= len(chunk):
            return 0

        show_message(format_detail(chunk[choice_idx]))
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
