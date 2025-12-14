from __future__ import annotations

import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from typing import Dict, Iterable, List, Tuple

from bs4 import BeautifulSoup

from .movements import extract_rep_scheme


_STOPWORDS = {
    "a",
    "about",
    "above",
    "after",
    "again",
    "all",
    "am",
    "an",
    "and",
    "any",
    "are",
    "as",
    "at",
    "be",
    "because",
    "been",
    "before",
    "being",
    "below",
    "between",
    "both",
    "but",
    "by",
    "can",
    "could",
    "did",
    "do",
    "does",
    "doing",
    "down",
    "during",
    "each",
    "few",
    "for",
    "from",
    "further",
    "had",
    "has",
    "have",
    "having",
    "he",
    "her",
    "here",
    "hers",
    "herself",
    "him",
    "himself",
    "his",
    "how",
    "i",
    "if",
    "in",
    "into",
    "is",
    "it",
    "its",
    "itself",
    "just",
    "me",
    "more",
    "most",
    "my",
    "myself",
    "no",
    "nor",
    "not",
    "now",
    "of",
    "off",
    "on",
    "once",
    "only",
    "or",
    "other",
    "our",
    "ours",
    "ourselves",
    "out",
    "over",
    "own",
    "s",
    "same",
    "she",
    "should",
    "so",
    "some",
    "such",
    "t",
    "than",
    "that",
    "the",
    "their",
    "theirs",
    "them",
    "themselves",
    "then",
    "there",
    "these",
    "they",
    "this",
    "those",
    "through",
    "to",
    "too",
    "under",
    "until",
    "up",
    "very",
    "was",
    "we",
    "were",
    "what",
    "when",
    "where",
    "which",
    "while",
    "who",
    "whom",
    "why",
    "will",
    "with",
    "you",
    "your",
    "yours",
    "yourself",
    "yourselves",
}


def build_comments_analysis(canonical: List[Dict], comments: Iterable[Dict]) -> Dict:
    posts_by_id: Dict[int, Dict] = {}
    for item in canonical:
        pid = item.get("id")
        if isinstance(pid, int):
            posts_by_id[pid] = item

    comment_list = [c for c in comments if c.get("post_id")]
    total_comments = len(comment_list)

    def plain_text(html: str) -> str:
        if not html:
            return ""
        return BeautifulSoup(html, "html.parser").get_text(" ", strip=True)

    month_counts = Counter()
    post_counts = Counter()
    commenter_counts = Counter()
    commenter_texts: Dict[str, List[str]] = defaultdict(list)
    global_words = Counter()

    for c in comment_list:
        date = c.get("date") or ""
        if date and len(date) >= 7:
            month_counts[date[:7]] += 1
        pid = c.get("post_id")
        if pid:
            post_counts[int(pid)] += 1
        author = (c.get("author_name") or "Anonymous").strip() or "Anonymous"
        commenter_counts[author] += 1

        text = plain_text(c.get("content_html") or "")
        if text:
            commenter_texts[author].append(text)
            for w in tokenize(text):
                global_words[w] += 1

    monthly_series = build_month_series(month_counts)

    top_posts = []
    for pid, cnt in post_counts.most_common(5):
        post = posts_by_id.get(pid) or {}
        top_posts.append(
            {
                "id": pid,
                "date": post.get("date") or "",
                "title": post.get("title") or f"Post {pid}",
                "link": post.get("link") or "",
                "comment_count": cnt,
                "summary": post_summary(post),
            }
        )

    top_commenters = []
    for name, cnt in commenter_counts.most_common(20):
        texts = commenter_texts.get(name, [])
        topics = top_terms(texts, limit=6)
        samples = sample_comments(texts, limit=2)
        top_commenters.append(
            {
                "name": name,
                "count": cnt,
                "topics": topics,
                "sample_comments": samples,
            }
        )

    wordcloud = [{"word": w, "count": c} for w, c in global_words.most_common(160)]

    return {
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "total_comments": total_comments,
        "monthly": monthly_series,
        "top_posts": top_posts,
        "top_commenters": top_commenters,
        "wordcloud": wordcloud,
    }


def tokenize(text: str) -> List[str]:
    words = re.findall(r"[a-z']{2,}", (text or "").lower())
    out = []
    for w in words:
        w = w.strip("'")
        if not w or w in _STOPWORDS:
            continue
        out.append(w)
    return out


def build_month_series(month_counts: Counter) -> List[Dict]:
    if not month_counts:
        return []
    months_sorted = sorted(month_counts.keys())
    start_y, start_m = map(int, months_sorted[0].split("-"))
    end_y, end_m = map(int, months_sorted[-1].split("-"))

    series = []
    y, m = start_y, start_m
    while (y, m) <= (end_y, end_m):
        key = f"{y:04d}-{m:02d}"
        series.append({"month": key, "count": int(month_counts.get(key, 0))})
        m += 1
        if m == 13:
            y += 1
            m = 1
    return series


def post_summary(post: Dict) -> str:
    components = post.get("components") or []
    if components:
        summary = extract_rep_scheme(components)
        if summary:
            return summary
        first = (components[0].get("details") or "").strip()
        return re.sub(r"\s+", " ", first)[:220]
    return ""


def top_terms(texts: List[str], limit: int = 6) -> List[str]:
    c = Counter()
    for t in texts:
        for w in tokenize(t):
            c[w] += 1
    return [w for w, _ in c.most_common(limit)]


def sample_comments(texts: List[str], limit: int = 2) -> List[str]:
    cleaned = []
    for t in texts:
        s = re.sub(r"\s+", " ", (t or "").strip())
        if len(s) < 25:
            continue
        cleaned.append(s[:220])
    return cleaned[:limit]
