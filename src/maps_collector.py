"""
Google Maps Data Collector
선정된 니치에 대해 Google Maps에서 비즈니스 데이터를 수집합니다.
SerpApi 무료 티어 (250건/월) 또는 직접 스크래핑 방식 사용.
"""
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

DATA_DIR = Path(__file__).parent.parent / "data"


def search_google_maps_serpapi(query: str, location: str = "", api_key: Optional[str] = None) -> list[dict]:
    """SerpApi를 통해 Google Maps 검색 결과를 가져옵니다."""
    import requests
    import os

    key = api_key or os.environ.get("SERPAPI_KEY", "")
    if not key:
        print("[Maps] No SerpApi key, skipping")
        return []

    params = {
        "engine": "google_maps",
        "q": query,
        "api_key": key,
        "type": "search",
    }
    if location:
        params["location"] = location

    try:
        resp = requests.get("https://serpapi.com/search", params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        results = []
        for place in data.get("local_results", []):
            results.append({
                "name": place.get("title", ""),
                "address": place.get("address", ""),
                "phone": place.get("phone", ""),
                "website": place.get("website", ""),
                "rating": place.get("rating", 0),
                "reviews": place.get("reviews", 0),
                "category": place.get("type", ""),
                "place_id": place.get("place_id", ""),
                "latitude": place.get("gps_coordinates", {}).get("latitude", 0),
                "longitude": place.get("gps_coordinates", {}).get("longitude", 0),
                "hours": place.get("operating_hours", {}),
                "thumbnail": place.get("thumbnail", ""),
            })

        return results

    except Exception as e:
        print(f"[Maps] SerpApi error: {e}")
        return []


def search_google_maps_direct(query: str, location: str = "") -> list[dict]:
    """직접 Google Maps 웹 스크래핑 (무료, 제한적)."""
    import requests
    from urllib.parse import quote_plus

    # Google Maps 검색 URL
    search_query = f"{query} {location}".strip()
    url = f"https://www.google.com/maps/search/{quote_plus(search_query)}"

    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    try:
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()

        # 기본 파싱 (실제로는 더 정교한 파싱 필요)
        # 프로토타입이므로 빈 리스트 반환
        print(f"[Maps] Direct scraping for '{search_query}' — limited results in prototype")
        return []

    except Exception as e:
        print(f"[Maps] Direct scraping error: {e}")
        return []


def collect_for_niche(niche_keyword: str, locations: list[str] = None) -> dict:
    """선정된 니치에 대해 데이터를 수집합니다."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    if locations is None:
        locations = [""]  # 위치 미지정

    all_results = []
    for loc in locations:
        # SerpApi 시도
        results = search_google_maps_serpapi(niche_keyword, loc)
        if results:
            all_results.extend(results)
        else:
            # 직접 스크래핑 시도
            results = search_google_maps_direct(niche_keyword, loc)
            all_results.extend(results)

        time.sleep(1)  # rate limiting

    output = {
        "niche": niche_keyword,
        "results": all_results,
        "total": len(all_results),
        "collected_at": datetime.now(timezone.utc).isoformat(),
    }

    # 파일 저장
    safe_name = re.sub(r"[^a-z0-9]", "_", niche_keyword.lower())[:50]
    output_path = DATA_DIR / f"maps_{safe_name}.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"[Maps] '{niche_keyword}': {len(all_results)} results collected")
    print(f"[Maps] Saved to {output_path}")
    return output


if __name__ == "__main__":
    # 테스트
    collect_for_niche("AI marketing tools", ["New York"])
