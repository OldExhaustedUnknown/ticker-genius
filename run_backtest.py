"""
Backtest Runner
================
Step C: CRL 예측 검증

사용법:
    python run_backtest.py           # 전체 백테스트
    python run_backtest.py --limit 50 # 50개만 테스트
"""
import argparse
import logging
import sys
from pathlib import Path
from collections import Counter
from dataclasses import dataclass, field

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

# Reduce noise
logging.getLogger("httpx").setLevel(logging.WARNING)

from tickergenius.collection.event_store import EventStore
from tickergenius.collection.predictor import PDUFAPredictor


@dataclass
class BacktestResult:
    """백테스트 결과."""
    total_events: int = 0
    evaluated_events: int = 0  # result가 approved/crl인 이벤트

    # 정확도 메트릭
    true_positives: int = 0   # 예측 CRL, 실제 CRL
    true_negatives: int = 0   # 예측 승인, 실제 승인
    false_positives: int = 0  # 예측 CRL, 실제 승인
    false_negatives: int = 0  # 예측 승인, 실제 CRL

    # 리스크 등급별 통계
    risk_level_counts: dict = field(default_factory=dict)
    risk_level_accuracy: dict = field(default_factory=dict)

    # 상세 결과
    predictions: list = field(default_factory=list)

    @property
    def accuracy(self) -> float:
        if self.evaluated_events == 0:
            return 0.0
        return (self.true_positives + self.true_negatives) / self.evaluated_events

    @property
    def precision(self) -> float:
        """CRL 예측 정밀도."""
        total = self.true_positives + self.false_positives
        return self.true_positives / total if total > 0 else 0.0

    @property
    def recall(self) -> float:
        """CRL 검출률."""
        total = self.true_positives + self.false_negatives
        return self.true_positives / total if total > 0 else 0.0

    @property
    def f1_score(self) -> float:
        """F1 스코어."""
        if self.precision + self.recall == 0:
            return 0.0
        return 2 * (self.precision * self.recall) / (self.precision + self.recall)


def run_backtest(store: EventStore, predictor: PDUFAPredictor, limit: int = None) -> BacktestResult:
    """
    백테스트 실행.

    Args:
        store: 이벤트 저장소
        predictor: CRL 예측기
        limit: 최대 이벤트 수

    Returns:
        BacktestResult
    """
    result = BacktestResult()
    event_ids = store.list_all()

    if limit:
        event_ids = event_ids[:limit]

    result.total_events = len(event_ids)

    risk_level_correct = Counter()
    risk_level_total = Counter()

    for i, event_id in enumerate(event_ids):
        # Load event
        event = store.load(event_id)
        if event is None:
            continue
        # 진행률 표시
        if (i + 1) % 50 == 0:
            print(f"  Progress: {i + 1}/{len(event_ids)}", end="\r", flush=True)

        # 결과가 없는 이벤트 스킵
        if event.result not in ("approved", "crl"):
            continue

        result.evaluated_events += 1
        actual_crl = event.result == "crl"

        # 예측 실행
        try:
            prediction = predictor.predict(event)
            predicted_crl = prediction.crl_probability >= 0.5

            # 혼동 행렬 업데이트
            if predicted_crl and actual_crl:
                result.true_positives += 1
            elif not predicted_crl and not actual_crl:
                result.true_negatives += 1
            elif predicted_crl and not actual_crl:
                result.false_positives += 1
            else:  # not predicted_crl and actual_crl
                result.false_negatives += 1

            # 리스크 등급별 통계
            risk_level_total[prediction.risk_level] += 1
            if (predicted_crl == actual_crl) or \
               (prediction.risk_level == "HIGH" and actual_crl) or \
               (prediction.risk_level == "LOW" and not actual_crl):
                risk_level_correct[prediction.risk_level] += 1

            # 상세 결과 저장
            result.predictions.append({
                "event_id": event.event_id,
                "ticker": event.ticker,
                "drug_name": event.drug_name,
                "pdufa_date": event.pdufa_date,
                "actual_result": event.result,
                "predicted_crl_prob": prediction.crl_probability,
                "risk_level": prediction.risk_level,
                "confidence": prediction.confidence,
                "correct": predicted_crl == actual_crl,
            })

        except Exception as e:
            logging.warning(f"Prediction failed for {event.event_id}: {e}")

    # 리스크 등급별 정확도 계산
    result.risk_level_counts = dict(risk_level_total)
    for level in risk_level_total:
        total = risk_level_total[level]
        correct = risk_level_correct[level]
        result.risk_level_accuracy[level] = correct / total if total > 0 else 0.0

    print()  # 줄바꿈
    return result


def print_report(result: BacktestResult):
    """백테스트 결과 출력."""
    print("\n" + "=" * 60)
    print("BACKTEST RESULTS - Step C")
    print("=" * 60)

    print(f"\n--- Dataset ---")
    print(f"Total events: {result.total_events}")
    print(f"Evaluated events: {result.evaluated_events} (with approved/crl result)")

    print(f"\n--- Confusion Matrix ---")
    print(f"                  Predicted")
    print(f"               Approved  CRL")
    print(f"  Actual  Approved  {result.true_negatives:4d}  {result.false_positives:4d}")
    print(f"          CRL       {result.false_negatives:4d}  {result.true_positives:4d}")

    print(f"\n--- Metrics ---")
    print(f"Accuracy:  {result.accuracy:.1%}")
    print(f"Precision: {result.precision:.1%} (CRL 예측 시 실제 CRL 비율)")
    print(f"Recall:    {result.recall:.1%} (실제 CRL 중 예측 성공 비율)")
    print(f"F1 Score:  {result.f1_score:.3f}")

    print(f"\n--- Risk Level Distribution ---")
    for level in ["HIGH", "ELEVATED", "MODERATE", "LOW"]:
        count = result.risk_level_counts.get(level, 0)
        accuracy = result.risk_level_accuracy.get(level, 0)
        pct = count / result.evaluated_events * 100 if result.evaluated_events > 0 else 0
        print(f"  {level:10} {count:4d} ({pct:5.1f}%)  accuracy: {accuracy:.1%}")

    # 틀린 예측 샘플
    wrong_predictions = [p for p in result.predictions if not p["correct"]]
    if wrong_predictions:
        print(f"\n--- Wrong Predictions (sample) ---")
        for p in wrong_predictions[:10]:
            actual = "CRL" if p["actual_result"] == "crl" else "Approved"
            print(f"  {p['ticker']}/{p['drug_name']} ({p['pdufa_date']})")
            print(f"    Actual: {actual}, Predicted CRL prob: {p['predicted_crl_prob']:.1%}, Risk: {p['risk_level']}")

    print("\n" + "=" * 60)


def main():
    parser = argparse.ArgumentParser(description="Backtest Runner")
    parser.add_argument("--limit", type=int, help="Limit number of events")
    parser.add_argument("--export", type=str, help="Export results to CSV")
    args = parser.parse_args()

    print("=" * 60)
    print("Backtest Runner - Step C")
    print("=" * 60)

    # Initialize
    store = EventStore(base_dir=Path("data/events"))
    predictor = PDUFAPredictor()

    # Run backtest
    print("\nRunning backtest...")
    result = run_backtest(store, predictor, limit=args.limit)

    # Print report
    print_report(result)

    # Export if requested
    if args.export:
        import json
        with open(args.export, "w") as f:
            json.dump({
                "total_events": result.total_events,
                "evaluated_events": result.evaluated_events,
                "accuracy": result.accuracy,
                "precision": result.precision,
                "recall": result.recall,
                "f1_score": result.f1_score,
                "confusion_matrix": {
                    "true_positives": result.true_positives,
                    "true_negatives": result.true_negatives,
                    "false_positives": result.false_positives,
                    "false_negatives": result.false_negatives,
                },
                "risk_level_counts": result.risk_level_counts,
                "predictions": result.predictions,
            }, f, indent=2)
        print(f"\nResults exported to: {args.export}")


if __name__ == "__main__":
    main()
