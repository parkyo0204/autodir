"""
Hacker News Trending Topics Collector
HN API를 사용하여 테크/스타트업 트렌딩 토픽을 수집합니다.
무료, 인증 불필요, 제한 없음.
"""
import json
from typing import Optional
import requests
from datetime import datetime, timezone
from pathlib import Path
from collections import Counter

DATA_DIR = Path(__file__).parent.parent / "data"

HN_API = "https://hacker-news.firebaseio.com/v0"
HN_ALGOLIA = "https://hn.algolia.com/api/v1"


def fetch_top_stories(limit: int = 100) -> list[int]:
    """상위 스토리 ID를 가져옵니다."""
    resp = requests.get(f"{HN_API}/topstories.json", timeout=10)
    resp.raise_for_status()
    return resp.json()[:limit]


def fetch_story(story_id: int) -> Optional[dict]:
    """개별 스토리를 가져옵니다."""
    try:
        resp = requests.get(f"{HN_API}/item/{story_id}.json", timeout=10)
        resp.raise_for_status()
        return resp.json()
    except Exception:
        return None


def extract_niche_signals(title: str) -> list[dict]:
    """HN 제목에서 니치 시그널을 추출합니다.
    각 시그널은 {keyword, type, confidence} 형태로 반환합니다."""
    import re
    signals = []

    # "Show HN: ..." 패턴 → 프로덕트/서비스 (높은 신뢰도)
    show_hn = re.findall(r"Show HN:\s*(.+?)(?:\s*[-—–(]|$)", title, re.IGNORECASE)
    if show_hn:
        for match in show_hn:
            cleaned = match.strip()
            if len(cleaned) > 3:
                signals.append({"keyword": cleaned, "type": "product", "confidence": 0.9})

    # "Ask HN: ..." 패턴 → 문제/니치 (중간 신뢰도)
    ask_hn = re.findall(r"Ask HN:\s*(.+?)(?:\?|$)", title, re.IGNORECASE)
    if ask_hn:
        for match in ask_hn:
            cleaned = match.strip()
            if len(cleaned) > 5:
                signals.append({"keyword": cleaned, "type": "problem", "confidence": 0.7})

    # "X vs Y" 패턴 → 비교 니치 (높은 신뢰도)
    vs_pattern = re.findall(r"(\w[\w\s]+?)\s+vs\.?\s+(\w[\w\s]+)", title, re.IGNORECASE)
    for a, b in vs_pattern:
        signals.append({"keyword": f"{a.strip()} vs {b.strip()}", "type": "comparison", "confidence": 0.85})

    # "Best X for Y" 패턴
    best_pattern = re.findall(r"best\s+(\w[\w\s]+?)\s+for\s+(\w[\w\s]+)", title, re.IGNORECASE)
    for a, b in best_pattern:
        signals.append({"keyword": f"best {a.strip()} for {b.strip()}", "type": "best-for", "confidence": 0.9})

    # "Alternative to X" 패턴
    alt_pattern = re.findall(r"alternative[s]?\s+to\s+(\w[\w\s]+)", title, re.IGNORECASE)
    for match in alt_pattern:
        signals.append({"keyword": f"alternative to {match.strip()}", "type": "alternative", "confidence": 0.85})

    # 카테고리 키워드 (낮은 신뢰도이지만 필터링용)
    category_map = {
        "AI": ["ai", "llm", "gpt", "machine learning", "deep learning"],
        "SaaS": ["saas", "software", "platform", "dashboard"],
        "Developer Tools": ["api", "sdk", "framework", "library", "cli", "devtool"],
        "Database": ["database", "db", "postgres", "sqlite", "redis"],
        "Hosting": ["hosting", "deploy", "cloud", "serverless", "cdn"],
        "Analytics": ["analytics", "monitoring", "observability", "metrics"],
        "Automation": ["automation", "scraper", "crawler", "bot", "workflow"],
        "Security": ["security", "auth", "encryption", "privacy"],
        "No-Code": ["nocode", "no-code", "lowcode", "low-code"],
        "E-commerce": ["ecommerce", "e-commerce", "shop", "store", "payment"],
    }
    title_lower = title.lower()
    for category, keywords in category_map.items():
        if any(kw in title_lower for kw in keywords):
            signals.append({"keyword": category, "type": "category", "confidence": 0.5})

    return signals


def collect_stories(limit: int = 100) -> dict:
    """HN 상위 스토리를 수집하고 분석합니다."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    story_ids = fetch_top_stories(limit)
    stories = []
    all_signals = Counter()

    for sid in story_ids:
        story = fetch_story(sid)
        if not story or story.get("type") != "story":
            continue

        signals = extract_niche_signals(story.get("title", ""))
        for sig in signals:
            kw = sig["keyword"] if isinstance(sig, dict) else sig
            all_signals[kw] += 1

        stories.append({
            "id": story.get("id"),
            "title": story.get("title", ""),
            "url": story.get("url", ""),
            "score": story.get("score", 0),
            "comments": story.get("descendants", 0),
            "by": story.get("by", ""),
            "time": story.get("time", 0),
            "niche_signals": signals,
            "collected_at": datetime.now(timezone.utc).isoformat(),
        })

    # 시그널 집계 (타입 정보 포함)
    signal_map = {}
    for story in stories:
        for sig in story.get("niche_signals", []):
            kw = sig["keyword"] if isinstance(sig, dict) else sig
            sig_type = sig.get("type", "category") if isinstance(sig, dict) else "category"
            if kw not in signal_map:
                signal_map[kw] = {"keyword": kw, "count": 0, "type": sig_type}
            signal_map[kw]["count"] += 1

    signal_list = sorted(signal_map.values(), key=lambda x: x["count"], reverse=True)[:30]

    output = {
        "stories": stories,
        "signal_summary": signal_list,
        "total_stories": len(stories),
        "collected_at": datetime.now(timezone.utc).isoformat(),
    }

    output_path = DATA_DIR / "hn_trends.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"[HN] {len(stories)} stories collected, {len(signal_list)} signals found")
    print(f"[HN] Saved to {output_path}")
    return output


if __name__ == "__main__":
    collect_stories()
