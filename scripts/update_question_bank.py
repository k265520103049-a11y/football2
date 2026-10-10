#!/usr/bin/env python3
"""Build a sourced, automatically refreshed Football Universe quiz bank.

Questions are deterministic templates over Wikipedia article lead summaries.
The script does not invent football facts: every answer is an article title,
all clues come from that article's plain-text summary, and each question keeps
its source URL and retrieval timestamp.
"""
from __future__ import annotations

import html
import json
import random
import re
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "data" / "generated-questions.json"
API = "https://en.wikipedia.org/w/api.php"
USER_AGENT = "FootballUniverseEducationalDemo/1.0 (automated sourced quiz bank; GitHub Actions)"
PER_CATEGORY_LIMIT = 18
CANDIDATE_LIMIT = 80

CURATED: dict[str, list[str]] = {
    "player": [
        "Lionel Messi", "Cristiano Ronaldo", "Pelé", "Diego Maradona", "Kylian Mbappé",
        "Erling Haaland", "Neymar", "Son Heung-min", "Mohamed Salah", "Virgil van Dijk",
        "Andrés Iniesta", "Zinedine Zidane", "Ronaldinho", "Xavi", "Thierry Henry",
        "Luka Modrić", "Kevin De Bruyne", "Marta (footballer)", "Alexia Putellas",
        "Megan Rapinoe", "Franz Beckenbauer", "Ronaldo (Brazilian footballer)",
    ],
    "club": [
        "Real Madrid CF", "FC Barcelona", "Manchester United F.C.", "Liverpool F.C.",
        "Manchester City F.C.", "FC Bayern Munich", "Juventus FC", "Arsenal F.C.",
        "Chelsea F.C.", "Paris Saint-Germain F.C.", "AC Milan", "Inter Milan",
        "Ajax (football club)", "Borussia Dortmund", "Santos FC", "Atlético Madrid",
        "Tottenham Hotspur F.C.", "Boca Juniors", "Flamengo (football club)",
        "Hanoi FC", "Ho Chi Minh City FC",
    ],
    "competition": [
        "FIFA World Cup", "UEFA Champions League", "UEFA European Championship",
        "Copa América", "Africa Cup of Nations", "AFC Asian Cup", "Premier League",
        "La Liga", "Bundesliga", "Serie A", "Ligue 1", "FIFA Women's World Cup",
        "UEFA Women's Champions League", "CONCACAF Gold Cup", "Copa Libertadores",
        "V.League 1", "AFF Championship", "Olympic football tournament",
    ],
}
CATEGORY_PAGES = {
    "player": ["Category:Association football players", "Category:Women's association football players"],
    "club": ["Category:Association football clubs", "Category:Association football clubs by country"],
    "competition": ["Category:Football competitions", "Category:Association football competitions"],
}
QUESTION_TEXT = {
    "player": "Cầu thủ nào được mô tả trong tư liệu Wikipedia này?",
    "club": "Câu lạc bộ nào được mô tả trong tư liệu Wikipedia này?",
    "competition": "Giải đấu bóng đá nào được mô tả trong tư liệu Wikipedia này?",
}
GENERIC_TITLE = {"player": "cầu thủ này", "club": "câu lạc bộ này", "competition": "giải đấu này"}


def api(params: dict[str, Any]) -> dict[str, Any]:
    params = {**params, "format": "json", "formatversion": "2"}
    url = API + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as response:
        return json.load(response)


def category_members(category_title: str, limit: int = CANDIDATE_LIMIT) -> list[str]:
    try:
        result = api({
            "action": "query", "list": "categorymembers", "cmtitle": category_title,
            "cmtype": "page", "cmlimit": str(limit), "cmsort": "timestamp", "cmdir": "desc",
            "cmprop": "title|timestamp",
        })
        return [p["title"] for p in result.get("query", {}).get("categorymembers", []) if p.get("title")]
    except Exception as exc:
        print(f"Warning: category unavailable: {category_title}: {exc}")
        return []


def search_titles(query: str, limit: int = 30) -> list[str]:
    try:
        result = api({
            "action": "query", "list": "search", "srsearch": query,
            "srnamespace": "0", "srlimit": str(limit), "srwhat": "text",
        })
        return [p["title"] for p in result.get("query", {}).get("search", []) if p.get("title")]
    except Exception as exc:
        print(f"Warning: search failed for {query!r}: {exc}")
        return []


def collect_title_groups() -> dict[str, list[str]]:
    groups: dict[str, list[str]] = {}
    search_fallback = {
        "player": ["association football player biography", "women's footballer biography"],
        "club": ["association football club", "football club history"],
        "competition": ["association football competition tournament", "football league competition"],
    }
    for group, curated in CURATED.items():
        recent: list[str] = []
        for category in CATEGORY_PAGES[group]:
            recent.extend(category_members(category))
        if len(recent) < 12:
            for query in search_fallback[group]:
                recent.extend(search_titles(query))
        # Curated famous names improve distractors and keep the set broadly recognisable;
        # category/search results supply newly discovered and recently categorised material.
        unique: list[str] = []
        seen = set()
        for title in curated + recent:
            normalized = re.sub(r"\s+", " ", title.replace("_", " ")).strip()
            if normalized and normalized.casefold() not in seen and not normalized.casefold().startswith("category:"):
                seen.add(normalized.casefold())
                unique.append(normalized)
        groups[group] = unique
        print(f"Collected {len(unique)} candidate titles for {group}")
    return groups


def fetch_pages(titles: list[str]) -> dict[str, dict[str, Any]]:
    output: dict[str, dict[str, Any]] = {}
    # MediaWiki can return up to 50 pages per query for an unauthenticated request.
    for start in range(0, len(titles), 40):
        batch = titles[start:start + 40]
        if not batch:
            continue
        try:
            data = api({
                "action": "query", "prop": "extracts|pageimages|info", "titles": "|".join(batch),
                "exintro": "1", "explaintext": "1", "exsentences": "3",
                "piprop": "thumbnail", "pithumbsize": "320", "inprop": "url", "redirects": "1",
            })
            canonical_pages: dict[str, dict[str, Any]] = {}
            for page in data.get("query", {}).get("pages", []):
                if "missing" in page or page.get("ns", 0) != 0:
                    continue
                title = str(page.get("title", "")).strip()
                extract = html.unescape(str(page.get("extract", "")))
                extract = re.sub(r"\s+", " ", extract).strip()
                if not title or len(extract) < 70:
                    continue
                low = extract.casefold()
                if any(bad in low for bad in ("may refer to:", "is a disambiguation page", "wikipedia does not have an article")):
                    continue
                pageid = page.get("pageid")
                if not pageid:
                    continue
                record = {
                    "title": title,
                    "extract": extract,
                    "pageid": pageid,
                    "url": f"https://en.wikipedia.org/?curid={pageid}",
                    "thumbnail": page.get("thumbnail", {}).get("source", ""),
                }
                canonical_pages[title.casefold()] = record
                output[title] = record
            # Preserve requested aliases after Wikipedia resolves redirects, while retaining
            # the canonical article title as the answer shown to players.
            redirects = {r.get("from", "").casefold(): r.get("to", "") for r in data.get("query", {}).get("redirects", [])}
            for requested in batch:
                canonical = redirects.get(requested.casefold(), requested)
                record = canonical_pages.get(canonical.casefold())
                if record:
                    output[requested] = record
            time.sleep(0.3)
        except Exception as exc:
            print(f"Warning: page batch failed: {exc}")
    return output


def clue_from_extract(title: str, extract: str, group: str) -> str:
    clue = re.sub(r"\s+", " ", extract).strip()
    # The article title is the answer; suppress direct repetitions in the clue.
    forms = sorted({title, title.replace("_", " "), title.replace(" F.C.", ""), title.replace(" FC", "")}, key=len, reverse=True)
    for form in forms:
        form = form.strip()
        if form and len(form) >= 3:
            clue = re.sub(re.escape(form), GENERIC_TITLE[group], clue, flags=re.IGNORECASE)
    clue = re.sub(r"\s+", " ", clue).strip(" -:;,.\t")
    # Remove common page-meta boilerplate which doesn't function as a clue.
    clue = re.sub(r"\b(also known as|commonly known as)\s+\1\b", "", clue, flags=re.I)
    return clue[:520].strip()


def build_questions(groups: dict[str, list[str]], pages: dict[str, dict[str, Any]], stamp: str) -> list[dict[str, Any]]:
    rng = random.Random(stamp[:10])  # A different, reproducible draw for each scheduled date.
    questions: list[dict[str, Any]] = []
    for group, titles in groups.items():
        available_by_pageid: dict[int, dict[str, Any]] = {}
        for title in titles:
            page = pages.get(title)
            if page and page.get("pageid"):
                available_by_pageid[int(page["pageid"])] = page
        available = list(available_by_pageid.values())
        # Blend familiar entries with recently categorised pages, then select a varied weekly set.
        rng.shuffle(available)
        chosen = available[:PER_CATEGORY_LIMIT]
        if len(chosen) < 5:
            print(f"Warning: only {len(chosen)} pages available for {group}")
        candidates = [p["title"] for p in available]
        for page in chosen:
            clue = clue_from_extract(page["title"], page["extract"], group)
            if len(clue) < 40:
                continue
            distractors = [title for title in candidates if title.casefold() != page["title"].casefold()]
            rng.shuffle(distractors)
            choices = [page["title"]] + distractors[:3]
            if len(set(x.casefold() for x in choices)) < 4:
                continue
            rng.shuffle(choices)
            questions.append({
                "id": f"wiki-{page['pageid']}-{stamp[:10]}",
                "kind": group,
                "q": QUESTION_TEXT[group] + "\n\n" + clue,
                "a": choices,
                "correct": choices.index(page["title"]),
                "ex": f"Đáp án lấy từ tiêu đề bài viết Wikipedia: {page['title']}.",
                "sourceUrl": page["url"],
                "sourceTitle": page["title"],
                "updatedAt": stamp,
            })
    # Avoid a bank of duplicate questions if aliases/redirects resolved to the same page.
    seen_ids = set()
    unique = []
    for q in questions:
        if q["id"] not in seen_ids:
            unique.append(q)
            seen_ids.add(q["id"])
    rng.shuffle(unique)
    return unique


def main() -> None:
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    groups = collect_title_groups()
    all_titles = list(dict.fromkeys(title for values in groups.values() for title in values))
    pages = fetch_pages(all_titles)
    questions = build_questions(groups, pages, stamp)
    # Keep the previous bank if upstream pages are briefly unavailable.
    if len(questions) < 8:
        raise SystemExit(f"Only {len(questions)} questions generated; refusing to overwrite the previous bank.")
    payload = {
        "schemaVersion": 1,
        "updatedAt": stamp,
        "source": "Wikipedia / MediaWiki Action API",
        "sourceApi": "https://www.mediawiki.org/wiki/API:Main_page",
        "generationMethod": "Deterministic question templates from Wikipedia article lead summaries; options are drawn from the same topic group.",
        "count": len(questions),
        "questions": questions,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Generated {len(questions)} sourced questions in {OUTPUT}")


if __name__ == "__main__":
    main()
