#!/usr/bin/env python3
"""
AutoDir Pipeline Runner
전체 자동화 파이프라인을 실행합니다.

실행 순서:
1. Google Trends RSS 수집
2. Reddit 트렌딩 토픽 수집
3. 니치 스코어링
4. 상위 니치 선택 및 리포트 생성
"""
import sys
import json
from pathlib import Path
from datetime import datetime, timezone

# 프로젝트 루트를 경로에 추가
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from trends_collector import collect_all as collect_trends
from reddit_collector import collect_all as collect_reddit
from hn_collector import collect_stories as collect_hn
from niche_scorer import score_all_signals

DATA_DIR = PROJECT_ROOT / "data"


def run_pipeline(skip_reddit: bool = False) -> dict:
    """전체 파이프라인을 실행합니다."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    results = {"started_at": datetime.now(timezone.utc).isoformat(), "steps": {}}

    # Step 1: Google Trends 수집
    print("\n=== Step 1: Google Trends RSS ===")
    try:
        trends = collect_trends()
        total_trends = sum(len(v) for v in trends.values())
        results["steps"]["trends"] = {
            "status": "success",
            "count": total_trends,
        }
    except Exception as e:
        print(f"[Error] Trends collection failed: {e}")
        results["steps"]["trends"] = {"status": "error", "error": str(e)}

    # Step 2: Reddit 수집
    print("\n=== Step 2: Reddit Trends ===")
    if skip_reddit:
        print("[Skip] Reddit collection skipped (no API credentials)")
        results["steps"]["reddit"] = {"status": "skipped", "reason": "no credentials"}
    else:
        try:
            reddit = collect_reddit()
            results["steps"]["reddit"] = {
                "status": "success",
                "posts": reddit.get("analysis", {}).get("total_posts_analyzed", 0),
                "signals": len(reddit.get("analysis", {}).get("signals", [])),
            }
        except Exception as e:
            print(f"[Error] Reddit collection failed: {e}")
            results["steps"]["reddit"] = {"status": "error", "error": str(e)}

    # Step 2b: HN 수집
    print("\n=== Step 2b: Hacker News ===")
    try:
        hn = collect_hn()
        results["steps"]["hn"] = {
            "status": "success",
            "stories": hn.get("total_stories", 0),
            "signals": len(hn.get("signal_summary", [])),
        }
    except Exception as e:
        print(f"[Error] HN collection failed: {e}")
        results["steps"]["hn"] = {"status": "error", "error": str(e)}

    # Step 3: 니치 스코어링
    print("\n=== Step 3: Niche Scoring ===")
    try:
        scored = score_all_signals()
        results["steps"]["scoring"] = {
            "status": "success",
            "niches_analyzed": scored.get("total_signals_analyzed", 0),
            "top_niches": [
                {"keyword": n["keyword"], "score": n["total_score"]}
                for n in scored.get("niches", [])[:5]
            ],
        }
    except Exception as e:
        print(f"[Error] Scoring failed: {e}")
        results["steps"]["scoring"] = {"status": "error", "error": str(e)}

    # Step 4: 리포트 생성
    print("\n=== Step 4: Report ===")
    results["completed_at"] = datetime.now(timezone.utc).isoformat()

    report_path = DATA_DIR / "pipeline_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"\n[Pipeline] Complete. Report saved to {report_path}")

    # 요약 출력
    print("\n--- Pipeline Summary ---")
    for step_name, step_data in results["steps"].items():
        status = step_data.get("status", "unknown")
        print(f"  {step_name}: {status}")

    if results["steps"].get("scoring", {}).get("top_niches"):
        print("\n--- Top Niches ---")
        for i, niche in enumerate(results["steps"]["scoring"]["top_niches"], 1):
            print(f"  {i}. {niche['keyword']} (score: {niche['score']})")

    return results


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="AutoDir Pipeline Runner")
    parser.add_argument("--skip-reddit", action="store_true", help="Skip Reddit collection (no API credentials)")
    args = parser.parse_args()

    run_pipeline(skip_reddit=args.skip_reddit)
