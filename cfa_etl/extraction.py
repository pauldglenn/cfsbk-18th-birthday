"""Extract today's programming from WordPress content with source evidence."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date

from bs4 import BeautifulSoup, Comment, NavigableString, Tag

from .movements import component_tag, tag_movements

HEADING = re.compile(r"^h[1-6]$")
ANCHOR = re.compile(r"^(?:workout of the day|today.s programming)\s*:?$", re.I)
SECTION = re.compile(
    r"^(?:floater strength|(?:partner |team )?(?:metcon|wod|workout|conditioning)|"
    r"strength|gymnastics|skill|assistance|accessor(?:y|ies)|bodybuilding|at home workout|"
    r"warm[ -]?up|cash[ -]?out|buy[ -]?in|a la carte)\b", re.I,
)
OTHER_CLASS = re.compile(
    r"^(?:alchemy|fit\s*55|short circuit|mythic strength|teens|active recovery)\b", re.I,
)
HOME = re.compile(r"^cfsbk\s*@\s*home\s*:?$", re.I)
BOUNDARY = re.compile(
    r"^(?:(?:crossfit group class )?programming template|today.s schedule|"
    r"class schedule|schedule\b|upcoming\b|related links|a closer look|"
    r"happy birthday|register\b|registration\b|yesterday.s whiteboard|"
    r"compare to|virtual class zoom room|password:|watch:)", re.I,
)
NOTES = re.compile(r"^(?:coach(?:ing|.s)? )?notes\s*:?\s*$", re.I)
FUTURE = re.compile(
    r"^(?:tomorrow|next week|next cycle|yesterday)\b|^\bpost .{0,80}\bto comments\b",
    re.I,
)
SCHEME = re.compile(
    r"\b(?:for time|amrap|emom|as many (?:rounds|reps) as possible|max (?:rounds|reps) in|(?:r|rds?|rounds?)\s*n[./]?f[./]?t\b|"
    r"not for (?:time|rounds)|tabata|intervals?|\d+\s*(?:sets?|rounds?|reps?|rm)\b|"
    r"every\s+(?:\d|minute)|(?:work|build|take)\b.{0,60}\b(?:up to|heavy|max|minutes?)\b)"
    r"|(?<!\w)\d+(?:\s*[-×x]\s*\d+)+", re.I,
)
START_SCHEME = re.compile(
    r"^(?:amrap|emom|for time|tabata|as many (?:rounds|reps) as possible|max (?:rounds|reps) in|\d+\s*(?:rounds?\b|rnft\b|minutes? (?:for|not)|"
    r"(?:[-–]\d+)+\s+reps)|every\s+(?:\d|minute))", re.I,
)
DOSE = re.compile(
    r"^(?:(?:[A-Z]\d?|\(?\d\))\s*[.):]\s*)?(?:[~+]?\d+\b|"
    r"(?:run|row|bike|ski|rest)\s+\d)|\b(?:fitness|performance|novice|intermediate\+?)\s*:",
    re.I,
)
TRACK = re.compile(r"^(?:fitness|performance|novice|intermediate|advanced|scaled|rx)\+?\s*:?$", re.I)
VIRTUAL_PROMO = re.compile(r"\bwhiteboard (?:explanation|brief)\b", re.I)


@dataclass(frozen=True)
class Block:
    number: int
    text: str
    kind: str
    emphasized: bool = False


def source_blocks(soup: BeautifulSoup) -> list[Block]:
    """Keep leaf paragraphs, list entries and headings in visual order."""
    blocks: list[Block] = []
    block_tags = {"p", "li", "figcaption", "hr", "div", "section", "figure", "ul", "ol", "table", "tr"}
    ignored = {"script", "style", "iframe", "blockquote", "noscript"}

    def walk(parent: Tag) -> None:
        pending: list[str] = []

        def emit(text: str, kind: str, emphasized: bool = False) -> None:
            lines = [" ".join(line.split()) for line in text.splitlines()]
            clean = "\n".join(line for line in lines if line)
            if kind == "text":
                parts = re.split(r"(?im)(?<=\n)(?=(?:notes\s*:?|[_–—-]{3,})\s*$)", clean)
            else:
                parts = [clean]
            for part in parts:
                if part.strip() or kind in {"separator", "media"}:
                    blocks.append(Block(len(blocks) + 1, part.strip(), kind, emphasized))

        def flush() -> None:
            emit("".join(pending), "text")
            pending.clear()

        for child in parent.children:
            if isinstance(child, Comment):
                continue
            if isinstance(child, NavigableString):
                pending.append(str(child))
                continue
            if not isinstance(child, Tag):
                continue
            if child.name in ignored:
                flush()
                if child.name in {"iframe", "blockquote"}:
                    emit("", "media")
            elif child.name == "br":
                pending.append("\n")
            elif child.name == "hr":
                flush()
                emit("", "separator")
            elif child.name in {"figure", "figcaption", "img"}:
                flush()
                emit("", "media")
            elif HEADING.fullmatch(child.name):
                flush()
                emit(child.get_text("", strip=False), "heading", True)
            elif child.name in block_tags:
                flush()
                if child.find(block_tags):
                    walk(child)
                else:
                    text = (
                        " | ".join(cell.get_text(" ", strip=True) for cell in child.find_all(["th", "td"], recursive=False))
                        if child.name == "tr" else child.get_text("", strip=False)
                    )
                    media = child.find(["img", "iframe"]) or child.select_one(".full-image-block")
                    empty_link = any(not a.get_text(strip=True) and a.get("href") for a in child.find_all("a"))
                    emit(text, "media" if media or empty_link else "text", bool(child.find(["strong", "b", "u"])))
            else:
                pending.append(child.get_text("", strip=False))
        flush()

    # Explicit break elements are significant even inside inline formatting.
    for br in soup.find_all("br"):
        br.replace_with(NavigableString("\n"))
    walk(soup)
    return blocks


def workout_formats(text: str) -> list[str]:
    """Return all explicit scoring/timing formats in a component."""
    return [
        name
        for name, pattern in (
            ("amrap", r"\bamrap\b|as many (?:rounds|reps) as possible|max (?:rounds|reps) in"),
            ("for time", r"(?<!not )\bfor time\b"),
            ("emom", r"\bemom\b|every (?:1 minute|minute|1:00)\b"),
            ("interval", r"\bintervals?\b|\btabata\b|\bevery (?:[2-9]|\d{2,})(?::\d\d|\s*min)"),
            ("not for time", r"\b(?:r?\s?n[./]?f[./]?t|not for time)\b"),
            ("for reps", r"\bfor (?:(?:max|total) )?reps\b"),
        )
        if re.search(pattern, text, re.I)
    ]


def extract_programming(blocks: list[Block], title: str, patterns) -> tuple[str, list[dict]]:
    if re.match(r"^rest day\b", title, re.I):
        return "rest_day", []

    anchor = next((i for i, b in enumerate(blocks) if b.kind == "heading" and ANCHOR.fullmatch(b.text)), None)
    modern = anchor is not None
    start = anchor + 1 if modern else 0
    candidates = blocks[start:]
    has_crossfit = any(b.kind == "heading" and b.text.casefold() == "crossfit" for b in candidates)
    first_label = re.split(r"\s*[|]\s*", title, maxsplit=1)[0]
    if not (tag_movements(first_label, patterns) and re.search(r"\b(?:squat|press|lift|snatch|clean|jerk|row|pull|push|swing)\w*\b", first_label, re.I)):
        first_label = "Workout"
    components: list[dict] = []
    label = "Workout" if modern else first_label
    label_block: int | None = None
    rows: list[tuple[int, str]] = []
    notes: list[tuple[int, str]] = []
    notes_mode = False
    skip_track = False
    finished_prescription = False

    def finish() -> None:
        nonlocal rows, notes, notes_mode, finished_prescription
        details = "\n".join(text for _, text in rows)
        if details:
            components.append({
                "component": label,
                "details": details,
                "notes": "\n".join(text for _, text in notes),
                "source_blocks": sorted({i for i, _ in rows + notes} | ({label_block} if label_block is not None else set())),
            })
        rows, notes, notes_mode, finished_prescription = [], [], False, False

    for index, block in enumerate(candidates):
        text = block.text
        if block.kind == "separator":
            if not rows:
                continue
            finish()
            if modern and components:
                break
            label, label_block = "Workout", None
            continue
        if block.kind == "media":
            if rows or components:
                break
            continue
        if not text:
            continue
        first = text.splitlines()[0]
        if block.kind == "heading":
            if text.casefold() == "crossfit":
                skip_track = False
                continue
            if OTHER_CLASS.match(text) or HOME.fullmatch(text):
                finish()
                skip_track = not HOME.fullmatch(text) or has_crossfit
                continue
            if skip_track:
                continue
            # Main WOD headings may share a heading level with the blog title.
            normalized = text.strip('🎃⭐️"“” ').casefold()
            next_block = candidates[index + 1] if index + 1 < len(candidates) else None
            preceding_scheme = (
                not modern and not rows and not components and len(text.split()) <= 15
                and next_block and next_block.kind == "text" and SCHEME.search(next_block.text)
            )
            known = (
                ANCHOR.fullmatch(text) or SECTION.match(text) or START_SCHEME.match(text)
                or text.startswith(('"', '“')) or (len(text.split()) <= 8 and tag_movements(text, patterns))
                or re.match(r"^(?:crossfit open|open workout|fight gone bad)\b", normalized)
                or preceding_scheme or (not modern and re.match(r"^\d+%\s*[x×]\s*\d+", text))
            )
            if BOUNDARY.match(text) or (not known and (not modern or rows or components)):
                break
            finish()
            label, label_block = text, block.number
            if "\n" in text and START_SCHEME.match(first):
                label = "Workout"
                rows.append((block.number, text))
            elif not modern and re.match(r"^\d+%\s*[x×]\s*\d+", text):
                label = first_label if first_label != "Workout" else title
                rows.append((block.number, text))
                notes_mode = True
            if SECTION.match(label) and re.search(r"^skill(?: work)?:\s*\S", label, re.I):
                rows.append((block.number, label.split(":", 1)[1].strip()))
            continue
        if OTHER_CLASS.match(first) and (finished_prescription or block.emphasized and "wod" in first.lower()):
            finish()
            break
        if skip_track:
            continue
        if first.casefold() == label.casefold() and "\n" not in text:
            continue
        if re.fullmatch(r"[_–—-]{3,}", first):
            if not rows:
                continue
            finish()
            label, label_block = "Workout", None
            continue
        if BOUNDARY.match(first):
            if rows or components:
                break
            continue
        if not rows and re.search(r"\b(?:gym|cfsbk) is closed\b", first, re.I):
            continue
        if VIRTUAL_PROMO.search(first):
            continue
        if FUTURE.match(first):
            if rows and first.lower().startswith("post "):
                finished_prescription = True
                notes_mode = False
            continue
        if re.match(r"^(?:exposure \d+ of \d+|week \d+ of \d+|e\d+/\d+)\b", first, re.I):
            continue
        if NOTES.fullmatch(first):
            notes_mode = True
            remainder = text.partition("\n")[2]
            if remainder:
                notes.append((block.number, remainder))
            continue
        if re.match(r"^notes\s*:", first, re.I):
            notes_mode = True
            notes.append((block.number, text.split(":", 1)[1].strip()))
            continue
        if SECTION.fullmatch(first.rstrip(":")) and block.emphasized and (not notes_mode or first.isupper()):
            finish()
            label, label_block = first, block.number
            remainder = text.partition("\n")[2]
            if remainder:
                rows.append((block.number, remainder))
            continue
        if notes_mode and rows and re.match(r"^[A-D][1-9]\s*[):.]", first, re.I):
            previous_label = label
            finish()
            label, label_block = previous_label, None
            rows.append((block.number, text))
            continue
        if TRACK.fullmatch(first) and not notes_mode:
            rows.append((block.number, text))
            continue
        starts_scheme = START_SCHEME.match(first)
        has_movement = bool(tag_movements(text, patterns))
        has_scheme = SCHEME.search(text)
        movement_row = has_movement and DOSE.match(first) and len(first.split()) <= 20
        named_intro = label.startswith(('"', '“')) and has_scheme
        prescribed = bool(starts_scheme or named_intro or (has_scheme and (has_movement or block.emphasized)) or movement_row)
        if not modern and rows and re.match(r"^(?:scale|substitute|use |aim |choose |with one partner|each partner|scaled loads|each .* terminates|the .* can be performed)", first, re.I):
            notes.append((block.number, text))
            continue
        if not modern and rows and starts_scheme and finished_prescription:
            finish()
            label, label_block = "Workout", None
        if finished_prescription and not notes_mode:
            if not prescribed:
                continue
            finish()
            label, label_block = "Workout", None
        if notes_mode:
            notes.append((block.number, text))
        elif not modern and rows and re.match(r"^(?:build up|work up|load the|partition the)\b", first, re.I):
            notes.append((block.number, text))
        elif (modern and (rows or prescribed or block.emphasized)) or prescribed or (rows and (block.emphasized or has_movement and len(first.split()) < 9)):
            rows.append((block.number, text))
        elif not rows and block.emphasized and (has_movement and len(first.split()) < 10 or first.startswith(('"', '“'))):
            label, label_block = first, block.number
        elif rows and re.match(r"^(?:rest|there is a .*cap)", first, re.I):
            notes.append((block.number, text))
        elif not modern and not rows and re.fullmatch(r"(?:today is a )?rest day[.!]?", first, re.I):
            return "rest_day", []
    finish()

    # A title or caption alone is insufficient evidence to call a legacy post a workout.
    if not components:
        return "needs_review", []
    evidence = any(
        SCHEME.search(c["details"])
        or tag_movements(c["details"], patterns)
        or component_tag(c["component"]) and re.search(r"\d", c["details"])
        or c["component"].lower().startswith(("skill", "gymnastics"))
        for c in components
    )
    return ("extracted", components) if evidence else ("needs_review", components)


def valid_date(value: str) -> str | None:
    try:
        return date.fromisoformat(value).isoformat()
    except ValueError:
        return None
