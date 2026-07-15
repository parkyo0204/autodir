"""
Niche Scorer
수집된 데이터를 기반으로 니치의 수익화 가능성을 자동 평가합니다.
"""
import json
from datetime import datetime, timezone
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"


def score_niche(keyword: str, context: dict) -> dict:
    """단일 니치의 점수를 계산합니다.

    점수 구성 (0-100):
    - demand_score (0-25): 수요 지표 (멘션 빈도, 포스트 점수)
    - competition_score (0-20): 경쟁도 (낮을수록 좋음)
    - monetization_score (0-25): 수익화 가능성
    - specificity_score (0-20): 니치의 구체성
    - signal_type_bonus (0-10): 시그널 타입 보너스
    """

    # 수요 점수: 멘션 빈도 + 평균 포스트 점수
    mention_count = context.get("mention_count", 0)
    avg_score = context.get("avg_score", 0)
    demand_score = min(25, (mention_count * 2) + min(10, avg_score / 200))

    # 경쟁 점수: 키워드 길이가 길수록 구체적 → 경쟁 낮음
    word_count = len(keyword.split())
    competition_score = min(20, word_count * 4)

    # 수익화 점수
    monetization_keywords = [
        "tool", "software", "app", "service", "platform", "saas",
        "buy", "price", "cheap", "best", "alternative", "compare",
        "review", "recommend", "professional", "business", "enterprise",
        "hosting", "database", "api", "dashboard", "analytics",
    ]
    keyword_lower = keyword.lower()
    monetization_hits = sum(1 for kw in monetization_keywords if kw in keyword_lower)
    monetization_score = min(25, monetization_hits * 8)

    # 구체성 점수
    specificity_indicators = [
        "free", "online", "local", "near", "best", "top", "cheap",
        "premium", "professional", "small", "large", "remote", "virtual",
        "vs", "alternative", "for",
    ]
    specificity_hits = sum(1 for si in specificity_indicators if si in keyword_lower)
    specificity_score = min(20, (word_count * 3) + (specificity_hits * 4))

    # 시그널 타입 보너스
    signal_type = context.get("signal_type", "")
    type_bonus = {
        "best-for": 10,
        "comparison": 9,
        "alternative": 9,
        "product": 7,
        "problem": 6,
        "category": 3,
    }.get(signal_type, 0)

    # 광범위 키워드 페널티
    broad_keywords = ["ai", "app", "tool", "software", "platform", "service"]
    if keyword_lower.strip() in broad_keywords:
        penalty = 15
    else:
        penalty = 0

    total_score = demand_score + competition_score + monetization_score + specificity_score + type_bonus - penalty
    total_score = max(0, min(100, total_score))

    return {
        "keyword": keyword,
        "total_score": round(total_score, 1),
        "breakdown": {
            "demand": round(demand_score, 1),
            "competition": round(competition_score, 1),
            "monetization": round(monetization_score, 1),
            "specificity": round(specificity_score, 1),
        },
        "recommendation": _get_recommendation(total_score),
        "suggested_subdomain": _to_subdomain(keyword),
        "scored_at": datetime.now(timezone.utc).isoformat(),
    }


def _get_recommendation(score: float) -> str:
    """점수 기반 추천 등급을 반환합니다."""
    if score >= 70:
        return "STRONG — 즉시 실행 추천"
    elif score >= 50:
        return "GOOD — 실행 가치 있음"
    elif score >= 30:
        return "MODERATE — 추가 검증 필요"
    else:
        return "WEAK — 다른 니치 탐색 권장"


def _to_subdomain(keyword: str) -> str:
    """키워드를 서브도메인 형태로 변환합니다."""
    # 공백을 하이픈으로, 특수문자 제거, 소문자 변환
    import re
    subdomain = keyword.lower().strip()
    subdomain = re.sub(r"[^a-z0-9\s-]", "", subdomain)
    subdomain = re.sub(r"\s+", "-", subdomain)
    subdomain = re.sub(r"-+", "-", subdomain)
    return subdomain[:63]  # 서브도메인 최대 길이


def score_all_signals() -> dict:
    """수집된 모든 니치 시그널을 점수화합니다."""
    # Reddit 데이터 로드
    reddit_path = DATA_DIR / "reddit_trends.json"
    if not reddit_path.exists():
        print("[Scorer] No Reddit data found.")
        reddit_data = {"analysis": {"signals": []}}
    else:
        with open(reddit_path, "r", encoding="utf-8") as f:
            reddit_data = json.load(f)

    # HN 데이터 로드
    hn_path = DATA_DIR / "hn_trends.json"
    hn_signals = []
    if hn_path.exists():
        with open(hn_path, "r", encoding="utf-8") as f:
            hn_data = json.load(f)
            hn_signals = hn_data.get("signal_summary", [])

    # Google Trends 데이터 로드 (보조)
    trends_path = DATA_DIR / "google_trends.json"
    trend_keywords = set()
    if trends_path.exists():
        with open(trends_path, "r", encoding="utf-8") as f:
            trends_data = json.load(f)
            for geo_trends in trends_data.values():
                for trend in geo_trends:
                    trend_keywords.add(trend.get("title", "").lower())

    # 니치 스코어링
    signals = reddit_data.get("analysis", {}).get("signals", [])
    scored_niches = []
    scored_keywords = set()

    for signal in signals:
        keyword = signal.get("keyword", "")
        context = {
            "mention_count": signal.get("mention_count", 0),
            "avg_score": signal.get("avg_score", 0),
        }

        scored = score_niche(keyword, context)
        scored_keywords.add(keyword.lower())

        # Google Trends 보너스
        if keyword.lower() in trend_keywords:
            scored["total_score"] = min(100, scored["total_score"] + 10)
            scored["google_trends_match"] = True

        scored_niches.append(scored)

    # HN 시그널 추가 (Reddit에 없는 것만)
    for hn_sig in hn_signals:
        kw = hn_sig.get("keyword", "")
        if kw.lower() not in scored_keywords:
            context = {
                "mention_count": hn_sig.get("count", 0),
                "avg_score": 0,
                "signal_type": hn_sig.get("type", "category"),
            }
            scored = score_niche(kw, context)
            if kw.lower() in trend_keywords:
                scored["total_score"] = min(100, scored["total_score"] + 10)
                scored["google_trends_match"] = True
            scored_niches.append(scored)

    # 점수순 정렬
    scored_niches.sort(key=lambda x: x["total_score"], reverse=True)

    # 저장
    output = {
        "niches": scored_niches[:20],  # 상위 20개만 저장
        "total_signals_analyzed": len(signals),
        "scored_at": datetime.now(timezone.utc).isoformat(),
    }

    output_path = DATA_DIR / "scored_niches.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"[Scorer] {len(scored_niches)} niches scored, top 20 saved")
    if scored_niches:
        top = scored_niches[0]
        print(f"[Scorer] Top niche: '{top['keyword']}' (score: {top['total_score']}, {top['recommendation']})")

    return output


if __name__ == "__main__":
    score_all_signals()
