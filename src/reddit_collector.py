"""
Reddit Trending Topics Collector
Reddit API (PRAW)를 사용하여 트렌딩 토픽을 수집합니다.
무료 티어: 100 QPM.
"""
import praw
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from collections import Counter

DATA_DIR = Path(__file__).parent.parent / "data"

# 니치 발견에 유용한 서브레딧
DISCOVERY_SUBREDDITS = [
    "startups",
    "Entrepreneur",
    "SaaS",
    "indiehackers",
    "SideProject",
    "InternetIsBeautiful",
    "YouShouldKnow",
    "LifeProTips",
    "technology",
    "artificial",
]

# "Best X for Y", "Alternative to X" 패턴 감지
NICHE_PATTERNS = [
    r"best\s+(\w[\w\s]+?)\s+for\s+(\w[\w\s]+)",
    r"alternative[s]?\s+to\s+(\w[\w\s]+)",
    r"(\w[\w\s]+?)\s+vs\s+(\w[\w\s]+)",
    r"recommend[ations]*\s+(\w[\w\s]+)",
    r"looking for\s+(\w[\w\s]+)",
    r"any(?:one|body)\s+(?:know|use|tried)\s+(\w[\w\s]+)",
]


def create_reddit_client(client_id: str = None, client_secret: str = None) -> praw.Reddit:
    """Reddit 클라이언트를 생성합니다. 환경변수 또는 인자로 인증."""
    import os

    return praw.Reddit(
        client_id=client_id or os.environ.get("REDDIT_CLIENT_ID", ""),
        client_secret=client_secret or os.environ.get("REDDIT_CLIENT_SECRET", ""),
        user_agent="AutoDir/1.0 (directory site automation)",
    )


def extract_niche_signals(text: str) -> list[str]:
    """텍스트에서 니치 관련 시그널을 추출합니다."""
    signals = []
    text_lower = text.lower()

    for pattern in NICHE_PATTERNS:
        matches = re.findall(pattern, text_lower, re.IGNORECASE)
        for match in matches:
            if isinstance(match, tuple):
                signals.extend([m.strip() for m in match if m.strip()])
            else:
                signals.append(match.strip())

    return signals


def collect_subreddit(reddit: praw.Reddit, subreddit_name: str, limit: int = 50) -> list[dict]:
    """서브레딧에서 핫 포스트를 수집합니다."""
    posts = []
    try:
        subreddit = reddit.subreddit(subreddit_name)

        for post in subreddit.hot(limit=limit):
            # 니치 시그널 추출
            full_text = f"{post.title} {post.selftext}"
            signals = extract_niche_signals(full_text)

            post_data = {
                "subreddit": subreddit_name,
                "title": post.title,
                "score": post.score,
                "num_comments": post.num_comments,
                "url": post.url,
                "permalink": f"https://reddit.com{post.permalink}",
                "created_utc": post.created_utc,
                "selftext_preview": post.selftext[:200] if post.selftext else "",
                "niche_signals": signals,
                "collected_at": datetime.now(timezone.utc).isoformat(),
            }
            posts.append(post_data)

    except Exception as e:
        print(f"[Reddit] Error collecting r/{subreddit_name}: {e}")

    return posts


def aggregate_signals(all_posts: list[dict]) -> dict:
    """수집된 포스트에서 니치 시그널을 집계합니다."""
    signal_counter = Counter()
    signal_sources = {}

    for post in all_posts:
        for signal in post.get("niche_signals", []):
            signal_counter[signal] += 1
            if signal not in signal_sources:
                signal_sources[signal] = []
            signal_sources[signal].append({
                "title": post["title"],
                "subreddit": post["subreddit"],
                "score": post["score"],
            })

    # 빈도순 정렬
    aggregated = []
    for signal, count in signal_counter.most_common(50):
        aggregated.append({
            "keyword": signal,
            "mention_count": count,
            "sources": signal_sources[signal][:5],  # 상위 5개 출처만
            "avg_score": sum(s["score"] for s in signal_sources[signal]) / count,
        })

    return {"signals": aggregated, "total_posts_analyzed": len(all_posts)}


def collect_all(client_id: str = None, client_secret: str = None) -> dict:
    """모든 서브레딧에서 데이터를 수집하고 분석합니다."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    reddit = create_reddit_client(client_id, client_secret)
    all_posts = []

    for sub_name in DISCOVERY_SUBREDDITS:
        posts = collect_subreddit(reddit, sub_name)
        all_posts.extend(posts)
        print(f"[Reddit] r/{sub_name}: {len(posts)} posts collected")

    # 니치 시그널 집계
    analysis = aggregate_signals(all_posts)

    # 저장
    output = {
        "posts": all_posts,
        "analysis": analysis,
        "collected_at": datetime.now(timezone.utc).isoformat(),
    }

    output_path = DATA_DIR / "reddit_trends.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"[Reddit] {len(all_posts)} posts collected, {len(analysis['signals'])} niche signals found")
    print(f"[Reddit] Saved to {output_path}")
    return output


if __name__ == "__main__":
    collect_all()
