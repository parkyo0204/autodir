"""
Google Trends RSS Collector
실시간 급상승 검색어를 RSS 피드에서 수집합니다.
차단 위험 0% — 공식 RSS 피드 사용.
"""
import feedparser
import json
from datetime import datetime, timezone
from pathlib import Path

FEEDS = {
    "KR": "https://trends.google.com/trending/rss?geo=KR",
    "US": "https://trends.google.com/trending/rss?geo=US",
}

DATA_DIR = Path(__file__).parent.parent / "data"


def fetch_trends(geo: str = "KR") -> list[dict]:
    """Google Trends RSS에서 급상승 키워드를 수집합니다."""
    url = FEEDS.get(geo)
    if not url:
        raise ValueError(f"Unsupported geo: {geo}")

    feed = feedparser.parse(url)
    trends = []

    for entry in feed.entries:
        trend = {
            "title": entry.get("title", ""),
            "traffic": entry.get("ht_approx_traffic", ""),
            "description": entry.get("summary", ""),
            "link": entry.get("link", ""),
            "published": entry.get("published", ""),
            "geo": geo,
            "collected_at": datetime.now(timezone.utc).isoformat(),
        }
        # 관련 뉴스/검색어 추출
        if "ht_news_item" in entry:
            news_items = entry.get("ht_news_item", [])
            if isinstance(news_items, list):
                trend["related_news"] = [
                    {
                        "title": item.get("ht_news_item_title", ""),
                        "url": item.get("ht_news_item_url", ""),
                        "source": item.get("ht_news_item_source", ""),
                    }
                    for item in news_items
                ]
        trends.append(trend)

    return trends


def collect_all() -> dict:
    """모든 지역의 트렌드를 수집하고 저장합니다."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    all_trends = {}
    for geo in FEEDS:
        trends = fetch_trends(geo)
        all_trends[geo] = trends
        print(f"[Trends] {geo}: {len(trends)} trends collected")

    # 파일 저장
    output_path = DATA_DIR / "google_trends.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(all_trends, f, ensure_ascii=False, indent=2)

    print(f"[Trends] Saved to {output_path}")
    return all_trends


if __name__ == "__main__":
    collect_all()
