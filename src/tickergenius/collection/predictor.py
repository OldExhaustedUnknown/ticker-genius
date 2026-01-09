"""
PDUFA Predictor
===============
Phase 4: CRL 예측 모듈

단일 책임: PDUFAEvent에서 CRL 확률 예측
- 기존 PDUFAAnalyzer와 연동
- PDUFAEvent → AnalysisContext 변환
- 리스크 등급 분류

참조: docs/M3_BLUEPRINT_v2.md
"""

import logging
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Optional, Any

from .event_models import PDUFAEvent

logger = logging.getLogger(__name__)


@dataclass
class PDUFAPrediction:
    """CRL 예측 결과."""

    crl_probability: float  # 0.0 ~ 1.0
    risk_level: str  # HIGH, ELEVATED, MODERATE, LOW
    confidence: float  # 0.0 ~ 1.0
    factors: list[dict] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    # 메타데이터
    event_id: str = ""
    ticker: str = ""
    drug_name: str = ""
    pdufa_date: str = ""

    def to_dict(self) -> dict:
        """딕셔너리로 변환."""
        return {
            "crl_probability": self.crl_probability,
            "risk_level": self.risk_level,
            "confidence": self.confidence,
            "factors": self.factors,
            "warnings": self.warnings,
            "event_id": self.event_id,
            "ticker": self.ticker,
            "drug_name": self.drug_name,
            "pdufa_date": self.pdufa_date,
        }


class RiskClassifier:
    """
    CRL 확률 기반 리스크 분류기.

    분류 기준:
    - HIGH (≥50%): CRL 가능성 높음
    - ELEVATED (30-50%): 우려 요인 존재
    - MODERATE (15-30%): 일부 리스크
    - LOW (<15%): CRL 가능성 낮음
    """

    THRESHOLDS = {
        "HIGH": 0.50,
        "ELEVATED": 0.30,
        "MODERATE": 0.15,
    }

    def classify(self, crl_probability: float) -> str:
        """
        CRL 확률을 리스크 등급으로 분류.

        Args:
            crl_probability: CRL 확률 (0-1)

        Returns:
            리스크 등급 문자열
        """
        if crl_probability >= self.THRESHOLDS["HIGH"]:
            return "HIGH"
        elif crl_probability >= self.THRESHOLDS["ELEVATED"]:
            return "ELEVATED"
        elif crl_probability >= self.THRESHOLDS["MODERATE"]:
            return "MODERATE"
        else:
            return "LOW"

    def get_description(self, risk_level: str) -> str:
        """리스크 등급 설명."""
        descriptions = {
            "HIGH": "CRL 가능성 높음 - 주의 필요",
            "ELEVATED": "우려 요인 존재 - 모니터링 권장",
            "MODERATE": "일부 리스크 요인 있음",
            "LOW": "CRL 가능성 낮음",
        }
        return descriptions.get(risk_level, "알 수 없음")


class PDUFAPredictor:
    """
    PDUFA CRL 예측기.

    PDUFAEvent를 받아서 CRL 확률을 예측합니다.
    기존 PDUFAAnalyzer와 연동하여 승인 확률을 계산한 후,
    CRL 확률 = 1 - 승인 확률로 변환합니다.

    Usage:
        predictor = PDUFAPredictor()
        prediction = predictor.predict(event)
        explanation = predictor.explain(prediction)
    """

    def __init__(self):
        """초기화."""
        self._analyzer = None
        self._classifier = RiskClassifier()

    @property
    def analyzer(self):
        """지연 로딩된 PDUFAAnalyzer."""
        if self._analyzer is None:
            try:
                from tickergenius.analysis.pdufa import PDUFAAnalyzer
                self._analyzer = PDUFAAnalyzer()
            except ImportError:
                logger.warning("PDUFAAnalyzer not available, using fallback")
                self._analyzer = None
        return self._analyzer

    def predict(self, event: PDUFAEvent) -> PDUFAPrediction:
        """
        CRL 확률 예측.

        Args:
            event: PDUFAEvent

        Returns:
            PDUFAPrediction
        """
        # 컨텍스트 변환
        context = self._event_to_context(event)

        # 분석 실행
        if self.analyzer:
            try:
                result = self.analyzer.analyze(context)
                approval_prob = result.probability
                confidence = result.confidence_score
                factors = [
                    {
                        "name": f.name,
                        "adjustment": f.adjustment,
                        "applied": f.applied,
                        "confidence": f.confidence,
                    }
                    for f in result.factors
                    if f.applied
                ]
                warnings = result.data_quality_warnings
            except Exception as e:
                logger.error(f"Analysis failed: {e}")
                approval_prob, confidence, factors, warnings = self._fallback_analysis(event)
        else:
            approval_prob, confidence, factors, warnings = self._fallback_analysis(event)

        # CRL 확률 계산
        crl_probability = 1.0 - approval_prob

        # 리스크 분류
        risk_level = self._classifier.classify(crl_probability)

        return PDUFAPrediction(
            crl_probability=crl_probability,
            risk_level=risk_level,
            confidence=confidence,
            factors=factors,
            warnings=warnings,
            event_id=event.event_id,
            ticker=event.ticker,
            drug_name=event.drug_name,
            pdufa_date=event.pdufa_date,
        )

    def explain(self, prediction: PDUFAPrediction) -> str:
        """
        예측 결과 설명 생성.

        Args:
            prediction: PDUFAPrediction

        Returns:
            설명 문자열
        """
        lines = [
            f"=== CRL 예측 결과 ===",
            f"",
            f"티커: {prediction.ticker}",
            f"약물: {prediction.drug_name}",
            f"PDUFA: {prediction.pdufa_date}",
            f"",
            f"CRL 확률: {prediction.crl_probability:.1%}",
            f"리스크 등급: {prediction.risk_level}",
            f"신뢰도: {prediction.confidence:.1%}",
            f"",
        ]

        # 리스크 등급 설명
        lines.append(f"평가: {self._classifier.get_description(prediction.risk_level)}")
        lines.append("")

        # 주요 요인
        if prediction.factors:
            lines.append("=== 주요 요인 ===")
            for factor in prediction.factors[:5]:  # 상위 5개
                adj = factor.get("adjustment", 0)
                direction = "▲" if adj > 0 else "▼" if adj < 0 else "─"
                lines.append(f"  {direction} {factor.get('name', 'Unknown')}: {adj:+.1%}")

        # 경고
        if prediction.warnings:
            lines.append("")
            lines.append("=== 주의 사항 ===")
            for warning in prediction.warnings:
                lines.append(f"  ⚠ {warning}")

        return "\n".join(lines)

    def _event_to_context(self, event: PDUFAEvent):
        """
        PDUFAEvent를 AnalysisContext로 변환.

        Args:
            event: PDUFAEvent

        Returns:
            AnalysisContext
        """
        try:
            from tickergenius.analysis.pdufa._context import (
                AnalysisContext,
                FDADesignations,
                AdComInfo,
                ClinicalInfo,
                ManufacturingInfo,
            )
        except ImportError:
            # Fallback for testing without full analysis module
            return self._create_minimal_context(event)

        # PDUFA 날짜 파싱
        pdufa_date = self._parse_date(event.pdufa_date)

        # FDA 지정
        fda_designations = FDADesignations(
            breakthrough_therapy=event.btd or False,
            priority_review=event.priority_review or False,
            fast_track=event.fast_track or False,
            orphan_drug=event.orphan_drug or False,
            accelerated_approval=event.accelerated_approval or False,
        )

        # AdCom 정보
        adcom_date = self._parse_date(event.adcom_date) if event.adcom_date else None
        adcom = AdComInfo(
            was_held=event.adcom_held or False,
            vote_ratio=event.adcom_vote_ratio,
            adcom_date=adcom_date,
        )

        # 임상 정보
        clinical = ClinicalInfo(
            phase=event.phase or "phase3",
            primary_endpoint_met=event.primary_endpoint_met,
            nct_id=event.nct_id,
        )

        # 제조 정보
        manufacturing = ManufacturingInfo(
            pai_passed=event.pai_passed or False,
            has_warning_letter=event.warning_letter_active or False,
        )

        # 재제출 여부
        is_resubmission = event.submission_type == "resubmission"

        return AnalysisContext(
            ticker=event.ticker,
            drug_name=event.drug_name,
            pdufa_date=pdufa_date,
            is_resubmission=is_resubmission,
            fda_designations=fda_designations,
            adcom=adcom,
            clinical=clinical,
            manufacturing=manufacturing,
        )

    def _create_minimal_context(self, event: PDUFAEvent):
        """분석 모듈 없을 때 최소 컨텍스트."""
        @dataclass
        class MinimalContext:
            ticker: str
            drug_name: str
            pdufa_date: Optional[date] = None
            is_resubmission: bool = False
            fda_designations: Any = None
            adcom: Any = None
            clinical: Any = None
            manufacturing: Any = None

        @dataclass
        class MinimalDesignations:
            breakthrough_therapy: bool = False
            priority_review: bool = False
            fast_track: bool = False
            orphan_drug: bool = False
            accelerated_approval: bool = False
            def count(self): return sum([
                self.breakthrough_therapy, self.priority_review,
                self.fast_track, self.orphan_drug, self.accelerated_approval
            ])

        @dataclass
        class MinimalAdcom:
            was_held: bool = False
            vote_ratio: Optional[float] = None
            adcom_date: Optional[date] = None

        @dataclass
        class MinimalClinical:
            phase: str = "phase3"
            primary_endpoint_met: Optional[bool] = None
            nct_id: Optional[str] = None

        @dataclass
        class MinimalManufacturing:
            pai_passed: bool = False
            has_warning_letter: bool = False
            pai_status: Optional[str] = None

        return MinimalContext(
            ticker=event.ticker,
            drug_name=event.drug_name,
            pdufa_date=self._parse_date(event.pdufa_date),
            is_resubmission=event.submission_type == "resubmission",
            fda_designations=MinimalDesignations(
                breakthrough_therapy=event.btd or False,
                priority_review=event.priority_review or False,
                fast_track=event.fast_track or False,
                orphan_drug=event.orphan_drug or False,
                accelerated_approval=event.accelerated_approval or False,
            ),
            adcom=MinimalAdcom(
                was_held=event.adcom_held or False,
                vote_ratio=event.adcom_vote_ratio,
            ),
            clinical=MinimalClinical(
                phase=event.phase or "phase3",
                primary_endpoint_met=event.primary_endpoint_met,
                nct_id=event.nct_id,
            ),
            manufacturing=MinimalManufacturing(
                pai_passed=event.pai_passed or False,
                has_warning_letter=event.warning_letter_active or False,
            ),
        )

    def _fallback_analysis(self, event: PDUFAEvent) -> tuple:
        """
        분석기 없을 때 fallback 분석.

        간단한 규칙 기반 점수 계산.
        """
        score = 0.70  # 기본 승인률
        factors = []
        warnings = ["분석기 미사용 - 규칙 기반 추정"]

        # BTD: +5%
        if event.btd:
            score += 0.05
            factors.append({"name": "BTD", "adjustment": 0.05, "applied": True, "confidence": 0.8})

        # Priority Review: +3%
        if event.priority_review:
            score += 0.03
            factors.append({"name": "Priority Review", "adjustment": 0.03, "applied": True, "confidence": 0.8})

        # Primary Endpoint Met: +15% / -25%
        if event.primary_endpoint_met is True:
            score += 0.15
            factors.append({"name": "Primary Endpoint Met", "adjustment": 0.15, "applied": True, "confidence": 0.9})
        elif event.primary_endpoint_met is False:
            score -= 0.25
            factors.append({"name": "Primary Endpoint NOT Met", "adjustment": -0.25, "applied": True, "confidence": 0.9})

        # AdCom 투표
        if event.adcom_held and event.adcom_vote_ratio is not None:
            if event.adcom_vote_ratio > 0.7:
                score += 0.10
                factors.append({"name": "AdCom Positive", "adjustment": 0.10, "applied": True, "confidence": 0.85})
            elif event.adcom_vote_ratio < 0.5:
                score -= 0.20
                factors.append({"name": "AdCom Negative", "adjustment": -0.20, "applied": True, "confidence": 0.85})

        # Warning Letter: -15%
        if event.warning_letter_active:
            score -= 0.15
            factors.append({"name": "Warning Letter", "adjustment": -0.15, "applied": True, "confidence": 0.7})

        # 범위 제한
        score = max(0.10, min(0.95, score))
        confidence = 0.60  # fallback은 낮은 신뢰도

        return score, confidence, factors, warnings

    @staticmethod
    def _parse_date(date_str: Optional[str]) -> Optional[date]:
        """날짜 문자열 파싱."""
        if not date_str:
            return None

        normalized = str(date_str).replace("-", "")[:8]

        try:
            dt = datetime.strptime(normalized, "%Y%m%d")
            return dt.date()
        except ValueError:
            return None


__all__ = ["PDUFAPredictor", "PDUFAPrediction", "RiskClassifier"]
