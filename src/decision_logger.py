"""
Decision Logger
자동화 파이프라인의 모든 의사결정을 기록하고 추적합니다.
"""
import json
from datetime import datetime, timezone
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"
DECISIONS_FILE = DATA_DIR / "decisions.json"


def load_decisions() -> list[dict]:
    """기존 의사결정을 로드합니다."""
    if DECISIONS_FILE.exists():
        with open(DECISIONS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("decisions", [])
    return []


def save_decisions(decisions: list[dict]):
    """의사결정을 저장합니다."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    output = {
        "decisions": decisions,
        "last_updated": datetime.now(timezone.utc).isoformat(),
    }
    with open(DECISIONS_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)


def log_decision(
    question: str,
    decision: str,
    reason: str,
    evidence: str = "",
    source: str = "pipeline",
    outcome: str = "pending",
) -> dict:
    """새로운 의사결정을 기록합니다."""
    decisions = load_decisions()

    # 다음 ID 생성
    existing_ids = [d.get("id", "") for d in decisions]
    next_num = max([int(id.split("-")[1]) for id in existing_ids if id.startswith("D-")] or [0]) + 1
    decision_id = f"D-{next_num:03d}"

    new_decision = {
        "id": decision_id,
        "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "question": question,
        "decision": decision,
        "reason": reason,
        "evidence": evidence,
        "outcome": outcome,
        "source": source,
    }

    decisions.append(new_decision)
    save_decisions(decisions)

    print(f"[Decision] {decision_id}: {question} → {decision}")
    return new_decision


def log_niche_selection(keyword: str, score: float, recommendation: str):
    """니치 선정 의사결정을 기록합니다."""
    return log_decision(
        question=f"니치 '{keyword}'를 실행할 것인가?",
        decision=f"점수 {score}점, 추천 등급: {recommendation}",
        reason=f"스코어링 알고리즘이 {score}점으로 평가. {recommendation} 등급.",
        evidence=f"자동 스코어링 결과. demand + competition + monetization + specificity 합산.",
        source="niche_scorer",
        outcome="validated" if score >= 50 else "pending",
    )


def log_data_collection(source: str, count: int, success: bool):
    """데이터 수집 의사결정을 기록합니다."""
    return log_decision(
        question=f"{source}에서 데이터를 수집할 것인가?",
        decision=f"수집 {'성공' if success else '실패'}: {count}건",
        reason=f"자동 파이프라인에 의해 실행됨.",
        evidence=f"{source} API/스크래핑 결과: {count}건 수집.",
        source=source,
        outcome="validated" if success else "rejected",
    )


def log_site_generation(niche: str, items_count: int):
    """사이트 생성 의사결정을 기록합니다."""
    return log_decision(
        question=f"'{niche}' 디렉토리 사이트를 생성할 것인가?",
        decision=f"생성 진행: {items_count}개 항목",
        reason=f"니치 스코어링 통과. {items_count}개 데이터 항목 확보.",
        evidence=f"파이프라인 자동 판단.",
        source="site_generator",
        outcome="validated",
    )


if __name__ == "__main__":
    # 테스트
    log_decision(
        question="이것은 테스트 의사결정인가?",
        decision="예, 테스트입니다.",
        reason="의사결정 로깅 시스템 테스트.",
        source="test",
        outcome="validated",
    )
