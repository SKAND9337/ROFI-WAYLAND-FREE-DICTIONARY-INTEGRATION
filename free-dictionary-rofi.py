#!/usr/bin/env python3
from __future__ import annotations

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

HISTORY_FILE = Path.home() / ".local" / "share" / "free-dictionary-rofi" / "history.txt"
ROFI_BASE = ["rofi", "-dmenu", "-i", "-matching", "fuzzy"]


def normalize(text: str) -> str:
    return " ".join(text.split()).strip()


def show_message(message: str) -> None:
    theme_override = (
        "window { width: 980px; background-color: #111111DD; border: 2px; "
        "border-color: #66d9ef; padding: 10px; }"
        "mainbox { background-color: transparent; }"
        "textbox { text-color: #f8f8f2; background-color: transparent; }"
    )
    subprocess.run(
        ["rofi", "-theme-str", theme_override, "-e", message],
        text=True,
        capture_output=True,
    )


def run_rofi(prompt: str, items: List[str], allow_custom: bool = True) -> Optional[str]:
    cmd = ROFI_BASE[:]
    if not allow_custom:
        cmd.append("-no-custom")

    proc = subprocess.run(
        cmd + ["-p", prompt],
        input="\n".join(items),
        text=True,
        capture_output=True,
    )
    choice = proc.stdout.strip()
    return choice or None


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


def fetch_entries(term: str) -> List[Dict[str, Any]]:
    url = f"{API_BASE}/{quote(term)}"
    try:
        resp = requests.get(url, timeout=12)
    except requests.RequestException as exc:
        show_message(f"Network error:\n\n{exc}")
        return []

    if resp.status_code == 404:
        return []

    try:
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        show_message(f"Failed to parse dictionary response:\n\n{exc}")
        return []

    if not isinstance(data, list):
        return []

    return data


def build_rows(entries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []

    for entry in entries:
        word = str(entry.get("word", "")).strip()
        phonetic = str(entry.get("phonetic", "")).strip()
        origin = str(entry.get("origin", "")).strip()
        phonetics = entry.get("phonetics", [])
        meanings = entry.get("meanings", [])

        if not isinstance(meanings, list):
            continue

        for meaning in meanings:
            if not isinstance(meaning, dict):
                continue

            pos = str(meaning.get("partOfSpeech", "")).strip()
            definitions = meaning.get("definitions", [])

            if not isinstance(definitions, list):
                continue

            for definition_block in definitions:
                if not isinstance(definition_block, dict):
                    continue

                definition = normalize(str(definition_block.get("definition", "")))
                example = normalize(str(definition_block.get("example", "")))
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
        cleaned = [str(x).strip() for x in items if str(x).strip()]
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
        choice = run_rofi(f"Free Dictionary ({page + 1})", menu_items, allow_custom=False)
        if choice is None:
            return 0

        chunk = page_rows(rows, page)

        if choice == "◀ Previous page":
            page = max(0, page - 1)
            continue

        if choice == "Next page ▶":
            if (page + 1) * PAGE_SIZE < len(rows):
                page += 1
            continue

        expected = [format_row(row) for row in chunk]
        try:
            idx = expected.index(choice)
        except ValueError:
            return 0

        show_message(format_detail(chunk[idx]))
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
