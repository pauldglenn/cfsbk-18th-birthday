from __future__ import annotations

import json
import os
import random
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import requests
import yaml

from .paths import CONFIG_DIR, ROOT
from .movements import load_movement_patterns, tag_movements


def load_canonical_movement_labels(config_dir: Path = CONFIG_DIR) -> List[str]:
    config_path = config_dir / "movements.yml"
    with config_path.open() as f:
        data = yaml.safe_load(f) or []
    labels: List[str] = []
    for entry in data:
        name = entry.get("name")
        if name:
            labels.append(str(name))
    return labels


def load_dotenv(path: Path = ROOT / ".env") -> None:
    """
    Minimal .env loader (no external dependency).
    - Supports KEY=VALUE lines
    - Ignores blank lines and comments
    - Does not overwrite existing environment variables
    """
    try:
        if not path.exists():
            return
        for raw_line in path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip("'").strip('"')
            if not key or key in os.environ:
                continue
            os.environ[key] = value
    except Exception:
        return


def build_llm_tagging_prompt(*, movement_labels: Sequence[str]) -> str:
    """
    Returns the instruction prompt to send alongside a single post's full text.
    """
    labels = "\n".join(f"- {m}" for m in movement_labels)
    return f"""You are helping audit a workout parser for the CrossFit South Brooklyn blog.

You will be given ONE blog post (title, URL, and full text). Your job:
1) Decide whether the post represents a true \"Rest Day\" (no workout prescribed).
2) Extract the workout programming components (e.g. STRENGTH, METCON, ASSISTANCE, FLOATER STRENGTH).
3) Tag the post with movements, component tags, and a workout format in a machine-readable way.

Important rules (match our existing ETL behavior):
- Only treat the day as a rest day if TODAY'S post is actually a rest day.
  - If the title contains \"Rest Day\", it is a rest day.
  - Ignore phrases like \"Yesterday's Whiteboard: Rest Day\" or other references to rest days in unrelated sections.
  - If any workout prescription is present (AMRAP / EMOM / For Time / intervals / sets & reps), it is NOT a rest day.
- Ignore future/promo content:
  - Ignore lines that reference future workouts, e.g. \"Tomorrow...\", \"Next week...\", \"Monday:\" schedule blocks.
  - Ignore \"News and Notes\", \"This week at CFSBK\", recaps, equipment announcements, newsletters, and unrelated articles.
- Components:
  - Use component headings if present (e.g. STRENGTH, METCON, ASSISTANCE, FLOATER STRENGTH).
  - If headings are missing but a workout is present, use a single component named \"Workout\".
  - Keep component details concise: include the actual prescription + short notes that affect interpretation.
- FLOATER STRENGTH:
  - Some posts include a \"FLOATER STRENGTH\" (or similar) section listing multiple optional strength items.
  - You should capture it as a component (so we can audit it) and include the `floater_strength` component tag.
  - However, DO NOT use the floater strength section to populate `movements` or `format` for the day.
    (Treat it as optional background programming, not the main prescribed WOD.)
- component_tags:
  - Use only these tags: strength, conditioning, assistance, partner, floater_strength
  - strength: barbell/skill strength work; conditioning: metcon/intervals; assistance: accessory/assistance/bodybuilding
  - partner: partner/team workouts; floater_strength: \"FLOATER STRENGTH\" programming blocks
- format:
  - Choose one of: \"amrap\", \"for time\", \"emom\", \"interval\", or \"\" if none.
  - \"interval\" includes Tabata / intervals / \"every 5:00\" style work blocks.
- movements:
  - You MUST choose movements ONLY from the canonical list below.
  - If the post includes a movement you cannot map to a canonical label, add it to `unmapped_movements`.
  - Prefer canonical mapping over generic terms. If the workout says "Row" / "Rower" / "Erg" / "Cal Row", map it to the canonical label `row (erg)` (not `row`).
  - Do NOT confuse `clean` vs `snatch`:
    - Only tag `snatch` if the workout explicitly prescribes snatches (e.g. "snatch", "power snatch", "hang snatch", "squat snatch").
    - Tag `clean` for cleans (e.g. "clean", "power clean", "hang clean", "squat clean", "clean pull").
    - If it's ambiguous, prefer leaving the movement out over guessing.
  - Do not include movements that appear ONLY inside the floater strength section.
  - Map common variants to the canonical label even if the post uses a different name:
    - "Power Snatch" / "Hang Power Snatch" / "Snatches" → `snatch`
    - "Shoulder Press" → `strict press`
  - If a movement appears ONLY in FLOATER STRENGTH, it MUST NOT be included in `movements`.

Examples (canonical mapping):
- If a workout says: "11/9 Cal Row" or "Row 500m" → movements should include `row (erg)`.
  Example output snippet:
  {{
    "movements": ["row (erg)", "burpee"],
    "unmapped_movements": []
  }}
- If a workout says: "3 Power Snatches" + "Shoulder Press" → movements should include `snatch` and `strict press`.
- If FLOATER STRENGTH lists pull-ups/squats/cleans, but the METCON is KB swings + push-ups, then `movements` should NOT include pull-ups/squats/cleans.

Canonical movement labels:
{labels}

Return ONLY valid JSON matching this schema:
{{
  \"id\": number | null,
  \"date\": \"YYYY-MM-DD\" | null,
  \"title\": string,
  \"link\": string,
  \"is_rest_day\": boolean,
  \"components\": [{{\"component\": string, \"details\": string}}],
  \"component_tags\": string[],
  \"format\": string,
  \"movements\": string[],
  \"unmapped_movements\": string[],
  \"notes\": string
}}

    Be conservative: prefer missing a movement over hallucinating one.
"""


def build_llm_judge_prompt(*, movement_labels: Sequence[str]) -> str:
    labels = "\n".join(f"- {m}" for m in movement_labels)
    return f"""You are the *judge* for an audit of workout tagging for the CrossFit South Brooklyn blog.

You will receive:
- The blog post metadata and full text
- A regex-based tagging result (baseline)
- A first-pass LLM tagging result (candidate)

Your task:
1) Read the blog post and decide what the correct tags should be for that day.
2) Use the regex result and the first-pass LLM result as references, but do NOT blindly trust either.
3) Output a final corrected tagging result in the same JSON schema as the first-pass LLM.

Rules (must follow):
- Rest days:
  - Title contains \"Rest Day\" => rest day.
  - Ignore \"Yesterday's Whiteboard: Rest Day\" references in other sections.
  - If there is any workout prescription (AMRAP / EMOM / For Time / intervals / sets & reps), it is NOT a rest day.
- Ignore future/promo/news/recap sections (tomorrow/next week schedules, newsletters, events, unrelated articles).
- FLOATER STRENGTH:
  - Capture floater strength as a component if present and include `floater_strength` in component_tags.
  - Do NOT include movements that appear ONLY inside the floater strength section in `movements`.
- movements must be chosen ONLY from the canonical list below.
  - Map common variants:
    - "Row/Erg/Rower/Cal Row" => `row (erg)`
    - "Power Snatch/Hang Power Snatch" => `snatch`
    - "Shoulder Press" => `strict press`
  - Do NOT confuse `clean` vs `snatch`:
    - Only tag `snatch` if the workout explicitly prescribes snatches (e.g. "snatch", "power snatch", "hang snatch", "squat snatch").
    - Tag `clean` for cleans (e.g. "clean", "power clean", "hang clean", "squat clean", "clean pull").
    - If it's ambiguous, prefer leaving the movement out over guessing.

Canonical movement labels:
{labels}

Return ONLY valid JSON matching this schema:
{{
  \"id\": number | null,
  \"date\": \"YYYY-MM-DD\" | null,
  \"title\": string,
  \"link\": string,
  \"is_rest_day\": boolean,
  \"components\": [{{\"component\": string, \"details\": string}}],
  \"component_tags\": string[],
  \"format\": string,
  \"movements\": string[],
  \"unmapped_movements\": string[],
  \"notes\": string
}}

In `notes`, briefly justify any correction you made vs regex/LLM results (1-3 sentences).
"""


def _require_openai_api_key() -> str:
    load_dotenv()
    key = os.getenv("OPENAI_API_KEY", "").strip()
    if not key:
        raise SystemExit("Missing OPENAI_API_KEY. Set it in your environment to run LLM tagging.")
    return key


@dataclass(frozen=True)
class LLMTaggingConfig:
    model: str = "gpt-4o-mini"
    temperature: float = 0.0
    max_tokens: int = 800
    timeout_s: int = 60
    max_retries: int = 6
    min_pause_s: float = 0.0


@dataclass(frozen=True)
class OpenAIAPIError(RuntimeError):
    status_code: int
    message: str
    retry_after_s: Optional[float] = None


_RETRY_AFTER_RE = re.compile(r"try again in\s+(\d+(?:\.\d+)?)(ms|s)\b", re.IGNORECASE)


def _parse_retry_after_s_from_error_text(text: str) -> Optional[float]:
    """
    Best-effort parser for OpenAI error payloads that include a hint like:
    "Please try again in 225ms."
    """
    m = _RETRY_AFTER_RE.search(text or "")
    if not m:
        return None
    value = float(m.group(1))
    unit = m.group(2).lower()
    if unit == "ms":
        return value / 1000.0
    return value


def _sleep_s_for_retry(attempt: int, err: Exception) -> float:
    """
    Centralized retry backoff policy.

    Notes:
    - For 429s we back off aggressively because concurrent workers can exhaust TPM
      and short Retry-After hints (e.g. 200ms) are often insufficient.
    """
    jitter = random.uniform(0.0, 1.0)
    if isinstance(err, OpenAIAPIError) and err.status_code == 429:
        # attempt=1 -> 5s, then 10, 20, 40... up to 5 minutes
        base = min(300.0, 5.0 * (2.0 ** (attempt - 1)))
        retry_after = (err.retry_after_s or 0.0) * 4.0
        return max(base, retry_after) + jitter
    # Other errors: smaller exponential backoff up to 30s
    return min(30.0, 1.5 ** attempt) + random.uniform(0.0, 0.25)


def _chat_completions(
    *,
    session: requests.Session,
    api_key: str,
    model: str,
    messages: List[Dict[str, str]],
    temperature: float,
    max_tokens: int,
    timeout_s: int,
) -> str:
    resp = session.post(
        "https://api.openai.com/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": model,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "response_format": {"type": "json_object"},
            "messages": messages,
        },
        timeout=timeout_s,
    )
    if resp.status_code >= 400:
        retry_after_s: Optional[float] = None
        if "retry-after" in resp.headers:
            try:
                retry_after_s = float(resp.headers["retry-after"])
            except Exception:
                retry_after_s = None
        if retry_after_s is None:
            retry_after_s = _parse_retry_after_s_from_error_text(resp.text)
        msg = resp.text
        raise OpenAIAPIError(resp.status_code, f"OpenAI API error {resp.status_code}: {msg}", retry_after_s=retry_after_s)
    data = resp.json()
    return data["choices"][0]["message"]["content"]


def _validate_llm_result(
    obj: Dict[str, Any], *, movement_labels: Sequence[str]
) -> Dict[str, Any]:
    required = [
        "id",
        "date",
        "title",
        "link",
        "is_rest_day",
        "components",
        "component_tags",
        "format",
        "movements",
        "unmapped_movements",
        "notes",
    ]
    for k in required:
        if k not in obj:
            raise ValueError(f"Missing key {k}")

    if not isinstance(obj["components"], list):
        raise ValueError("components must be a list")
    for c in obj["components"]:
        if not isinstance(c, dict) or "component" not in c or "details" not in c:
            raise ValueError("components entries must be objects with component/details")

    allowed_tags = {"strength", "conditioning", "assistance", "partner", "floater_strength"}
    obj["component_tags"] = [t for t in (obj.get("component_tags") or []) if t in allowed_tags]

    fmt = str(obj.get("format") or "").strip().lower()
    fmt_map = {
        "amrap": "amrap",
        "for time": "for time",
        "fortime": "for time",
        "for_time": "for time",
        "emom": "emom",
        "interval": "interval",
        "intervals": "interval",
        "tabata": "interval",
        "": "",
        "none": "",
        "n/a": "",
    }
    obj["format"] = fmt_map.get(fmt, "")

    allowed_movements = set(movement_labels)
    movements = list(obj.get("movements") or [])
    unmapped = list(obj.get("unmapped_movements") or [])
    # Normalize a few common movement aliases to canonical labels before comparing.
    alias_to_canonical = {
        "row": "row (erg)",
        "rowing": "row (erg)",
        "rower": "row (erg)",
        "erg": "row (erg)",
        "power snatch": "snatch",
        "hang power snatch": "snatch",
        "power clean": "clean",
        "hang power clean": "clean",
        "shoulder press": "strict press",
        "db bench": "bench press",
        "db bench press": "bench press",
        "dumbbell bench": "bench press",
        "dumbbell bench press": "bench press",
        "renegade row": "row (weighted)",
        "renegade rows": "row (weighted)",
    }
    normalized: List[str] = []
    for m in movements:
        if not isinstance(m, str):
            continue
        key = m.strip().lower()
        normalized.append(alias_to_canonical.get(key, m))
    movements = normalized

    # Also normalize unmapped movements: if they map cleanly to a canonical label,
    # move them into movements (this keeps audits focused on semantic differences).
    normalized_unmapped: List[str] = []
    for m in unmapped:
        if not isinstance(m, str):
            continue
        key = m.strip().lower()
        mapped = alias_to_canonical.get(key)
        if mapped and mapped in allowed_movements:
            movements.append(mapped)
        else:
            normalized_unmapped.append(m)
    unmapped = normalized_unmapped

    unknown = [m for m in movements if m not in allowed_movements]
    if unknown:
        unmapped.extend(unknown)
        movements = [m for m in movements if m in allowed_movements]
        obj["notes"] = (obj.get("notes") or "").strip()
        extra = ", ".join(sorted(set(unknown)))
        obj["notes"] = (obj["notes"] + (" " if obj["notes"] else "") + f"(Coerced unknown movements to unmapped: {extra})").strip()

    # De-dupe and keep stable-ish ordering.
    seen = set()
    obj["movements"] = [m for m in movements if not (m in seen or seen.add(m))]
    seen2 = set()
    obj["unmapped_movements"] = [m for m in unmapped if isinstance(m, str) and m and not (m in seen2 or seen2.add(m))]

    # Enforce the floater-strength rule: movements that appear only in floater strength
    # should not be in the main movements list.
    components = obj.get("components") or []
    floater_components = [
        c
        for c in components
        if isinstance(c, dict)
        and isinstance(c.get("component"), str)
        and "floater" in c.get("component", "").lower()
        and "strength" in c.get("component", "").lower()
    ]
    if floater_components:
        compiled = load_movement_patterns()
        floater_text = " ".join(str(c.get("details") or "") for c in floater_components)
        non_floater_text = " ".join(
            str(c.get("details") or "")
            for c in components
            if c not in floater_components
        )
        floater_movs = set(tag_movements(floater_text.lower(), compiled))
        non_floater_movs = set(tag_movements(non_floater_text.lower(), compiled))
        floater_only = floater_movs - non_floater_movs
        if floater_only:
            before = obj["movements"]
            obj["movements"] = [m for m in before if m not in floater_only]
            removed = sorted(set(before) - set(obj["movements"]))
            if removed:
                note = (obj.get("notes") or "").strip()
                extra = ", ".join(removed)
                obj["notes"] = (note + (" " if note else "") + f"(Removed floater-only movements: {extra})").strip()

    return obj


def tag_post_with_llm(
    *,
    post_id: Optional[int],
    date: Optional[str],
    title: str,
    link: str,
    full_text: str,
    movement_labels: Sequence[str],
    cfg: LLMTaggingConfig = LLMTaggingConfig(),
    session: Optional[requests.Session] = None,
) -> Dict[str, Any]:
    api_key = _require_openai_api_key()
    prompt = build_llm_tagging_prompt(movement_labels=movement_labels)
    payload = {
        "id": post_id,
        "date": date,
        "title": title,
        "link": link,
        "text": full_text,
    }
    messages = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
    ]

    s = session or requests.Session()
    last_err: Optional[Exception] = None

    for attempt in range(1, cfg.max_retries + 1):
        if cfg.min_pause_s:
            time.sleep(cfg.min_pause_s)
        try:
            text = _chat_completions(
                session=s,
                api_key=api_key,
                model=cfg.model,
                messages=messages,
                temperature=cfg.temperature,
                max_tokens=cfg.max_tokens,
                timeout_s=cfg.timeout_s,
            )
            obj = json.loads(text)
            return _validate_llm_result(obj, movement_labels=movement_labels)
        except Exception as e:
            last_err = e
            time.sleep(_sleep_s_for_retry(attempt, e))
            continue

    raise RuntimeError(f"LLM tagging failed after {cfg.max_retries} retries: {last_err}")


def judge_post_tags_with_llm(
    *,
    post_payload: Dict[str, Any],
    regex_result: Dict[str, Any],
    llm_result: Dict[str, Any],
    movement_labels: Sequence[str],
    cfg: LLMTaggingConfig = LLMTaggingConfig(),
    session: Optional[requests.Session] = None,
) -> Dict[str, Any]:
    api_key = _require_openai_api_key()
    prompt = build_llm_judge_prompt(movement_labels=movement_labels)
    payload = {
        "post": post_payload,
        "regex_result": regex_result,
        "llm_result": llm_result,
    }
    messages = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
    ]

    s = session or requests.Session()
    last_err: Optional[Exception] = None
    for attempt in range(1, cfg.max_retries + 1):
        if cfg.min_pause_s:
            time.sleep(cfg.min_pause_s)
        try:
            text = _chat_completions(
                session=s,
                api_key=api_key,
                model=cfg.model,
                messages=messages,
                temperature=cfg.temperature,
                max_tokens=cfg.max_tokens,
                timeout_s=cfg.timeout_s,
            )
            obj = json.loads(text)
            return _validate_llm_result(obj, movement_labels=movement_labels)
        except Exception as e:
            last_err = e
            time.sleep(_sleep_s_for_retry(attempt, e))
            continue

    raise RuntimeError(f"LLM judge failed after {cfg.max_retries} retries: {last_err}")

def iter_jsonl(path: Path) -> Iterable[Dict[str, Any]]:
    with path.open() as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            yield json.loads(line)


def upsert_jsonl_record(out_path: Path, record: Dict[str, Any]) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("a", encoding="utf-8") as f:
        json.dump(record, f, ensure_ascii=False)
        f.write("\n")
