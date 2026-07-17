import json
import os
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import requests

DATA_DIR = Path(__file__).parent.parent / "data"
API_URL = "https://openapi.naver.com/v1/datalab/search"


class NaverDataLabError(RuntimeError):
    pass


def credentials_configured() -> bool:
    return bool(
        os.environ.get("NAVER_CLIENT_ID", "").strip()
        and os.environ.get("NAVER_CLIENT_SECRET", "").strip()
    )


def _load_korean_keywords(limit: int = 5) -> list[str]:
    trends_path = DATA_DIR / "google_trends.json"
    if not trends_path.exists():
        return []

    with open(trends_path, "r", encoding="utf-8") as file:
        trends_data = json.load(file)

    keywords = []
    seen = set()
    for trend in trends_data.get("KR", []):
        keyword = str(trend.get("title", "")).strip()
        key = keyword.casefold()
        if keyword and key not in seen:
            keywords.append(keyword)
            seen.add(key)
        if len(keywords) >= limit:
            break
    return keywords


def _request_trends(keywords: list[str], start_date: date, end_date: date) -> dict:
    if not credentials_configured():
        raise NaverDataLabError(
            "NAVER_CLIENT_ID와 NAVER_CLIENT_SECRET이 설정되지 않았습니다."
        )

    payload = {
        "startDate": start_date.isoformat(),
        "endDate": end_date.isoformat(),
        "timeUnit": "week",
        "keywordGroups": [
            {"groupName": keyword, "keywords": [keyword]} for keyword in keywords
        ],
    }
    headers = {
        "X-Naver-Client-Id": os.environ["NAVER_CLIENT_ID"].strip(),
        "X-Naver-Client-Secret": os.environ["NAVER_CLIENT_SECRET"].strip(),
        "Content-Type": "application/json",
    }

    try:
        response = requests.post(API_URL, headers=headers, json=payload, timeout=15)
    except requests.RequestException as error:
        raise NaverDataLabError("Naver DataLab 네트워크 요청에 실패했습니다.") from error

    if response.status_code != 200:
        raise NaverDataLabError(f"Naver DataLab HTTP 오류: {response.status_code}")

    try:
        return response.json()
    except ValueError as error:
        raise NaverDataLabError("Naver DataLab 응답이 JSON이 아닙니다.") from error


def _summarize_result(result: dict) -> dict:
    observations = [
        item
        for item in result.get("data", [])
        if isinstance(item, dict) and isinstance(item.get("ratio"), (int, float))
    ]
    ratios = [float(item["ratio"]) for item in observations]
    first_ratio = ratios[0] if ratios else 0.0
    latest_ratio = ratios[-1] if ratios else 0.0

    summary = {
        "observation_count": len(ratios),
        "first_ratio": round(first_ratio, 2),
        "latest_ratio": round(latest_ratio, 2),
        "peak_ratio": round(max(ratios, default=0.0), 2),
        "average_ratio": round(sum(ratios) / len(ratios), 2) if ratios else 0.0,
        "delta_ratio": round(latest_ratio - first_ratio, 2),
    }
    return {
        "title": result.get("title", ""),
        "keywords": result.get("keywords", []),
        "data": observations,
        "summary": summary,
    }


def collect_all(keywords: list[str] | None = None) -> dict:
    selected_keywords = keywords or _load_korean_keywords()
    selected_keywords = list(
        dict.fromkeys(
            keyword.strip() for keyword in selected_keywords if keyword.strip()
        )
    )[:5]
    if not selected_keywords:
        raise NaverDataLabError("Naver 조회 대상 한국어 키워드가 없습니다.")

    end_date = date.today()
    start_date = end_date - timedelta(days=84)
    response = _request_trends(selected_keywords, start_date, end_date)
    results = [_summarize_result(result) for result in response.get("results", [])]
    if len(results) != len(selected_keywords):
        raise NaverDataLabError(
            f"Naver DataLab 결과 수 불일치: 요청 {len(selected_keywords)}개, 응답 {len(results)}개"
        )
    if any(not result["data"] for result in results):
        raise NaverDataLabError("Naver DataLab 결과에 관측값이 없습니다.")
    output = {
        "source": "naver_datalab_search_trend",
        "api_url": API_URL,
        "time_unit": "week",
        "period": {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
        },
        "requested_keywords": selected_keywords,
        "results": results,
        "request_count": 1,
        "collected_at": datetime.now(timezone.utc).isoformat(),
    }

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    output_path = DATA_DIR / "naver_trends.json"
    with open(output_path, "w", encoding="utf-8") as file:
        json.dump(output, file, ensure_ascii=False, indent=2)

    print(f"[Naver] {len(results)} keyword trends collected")
    print(f"[Naver] Saved to {output_path}")
    return output


if __name__ == "__main__":
    collect_all()
