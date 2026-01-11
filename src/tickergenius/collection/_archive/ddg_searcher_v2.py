"""
DDG Clinical Searcher v2
========================
고도화된 DuckDuckGo 기반 임상 데이터 검색.

핵심 개선:
1. 약물 식별 강화 - drug_name + indication + year 조합
2. 결과 검증 - 약물명이 결과에 실제 포함 확인
3. 컨텍스트 분리 - 다른 약물 정보 혼입 방지
"""

import logging
import re
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from ddgs import DDGS

logger = logging.getLogger(__name__)


@dataclass
class SearchEvidence:
    """검색 근거."""
    text: str
    source_url: str = ""
    drug_mentioned: bool = False
    confidence: float = 0.0


@dataclass
class ClinicalSearchResultV2:
    """고도화된 검색 결과."""
    # 검색 성공 여부
    found: bool = False

    # Primary Endpoint
    endpoint_met: Optional[bool] = None
    endpoint_confidence: float = 0.0
    endpoint_evidence: list[SearchEvidence] = field(default_factory=list)

    # P-value
    p_value: Optional[str] = None
    p_value_numeric: Optional[float] = None

    # Effect Size
    effect_size: Optional[str] = None
    effect_type: Optional[str] = None  # "HR", "OR", "RR", "%"

    # AdCom
    adcom_held: Optional[bool] = None
    adcom_vote: Optional[str] = None  # "14-1"
    adcom_vote_ratio: Optional[float] = None  # 0.93

    # Approval Type
    approval_type: Optional[str] = None  # "nda", "bla", "anda"

    # 메타데이터
    searched_at: str = field(default_factory=lambda: datetime.now().isoformat())
    queries_used: list[str] = field(default_factory=list)
    total_results_analyzed: int = 0
    drug_mention_rate: float = 0.0  # 검색 결과 중 약물명 언급 비율


class DDGClinicalSearcherV2:
    """
    고도화된 DuckDuckGo 임상 데이터 검색기.

    핵심 원칙:
    1. 검색 결과에서 약물명이 명시적으로 언급된 경우만 신뢰
    2. 여러 쿼리로 교차 검증
    3. 다른 약물 정보 혼입 감지 및 필터링
    """

    MIN_INTERVAL = 2.5  # Rate limit (초)
    MIN_DRUG_MENTION_RATE = 0.3  # 최소 약물 언급 비율

    # Primary Endpoint 패턴 (그룹화)
    ENDPOINT_POSITIVE_PATTERNS = [
        r"met\s+(?:its\s+)?primary\s+endpoint",
        r"achieved\s+(?:its\s+)?primary\s+endpoint",
        r"primary\s+endpoint\s+(?:was\s+)?met",
        r"positive\s+(?:top-?line|phase\s*[23i]+)\s+results?",
        r"statistically\s+significant\s+(?:improvement|reduction|benefit)",
        r"demonstrated\s+(?:statistically\s+)?significant",
        r"showed\s+(?:statistically\s+)?significant",
    ]

    ENDPOINT_NEGATIVE_PATTERNS = [
        r"did\s+not\s+meet\s+(?:its\s+)?primary\s+endpoint",
        r"failed\s+to\s+(?:meet|achieve)\s+(?:its\s+)?primary",
        r"primary\s+endpoint\s+(?:was\s+)?not\s+met",
        r"negative\s+(?:top-?line|phase\s*[23i]+)\s+results?",
        r"did\s+not\s+(?:reach|achieve)\s+statistical\s+significance",
        r"discontinued\s+(?:the\s+)?(?:trial|study|development)",
        r"terminated\s+(?:the\s+)?program",
    ]

    # P-value 패턴
    PVALUE_PATTERNS = [
        (r"p\s*[=<]\s*(0\.\d+)", "exact"),
        (r"p\s*<\s*(0\.0+1)", "threshold"),
        (r"p\s*[-]?\s*value\s*(?:of|=|:)?\s*(0\.\d+)", "labeled"),
        (r"\(p\s*[=<]\s*(0\.\d+)\)", "parenthetical"),
    ]

    # Effect Size 패턴
    EFFECT_SIZE_PATTERNS = [
        (r"hazard\s+ratio\s*(?:of|=|:)?\s*([\d.]+)", "HR"),
        (r"HR\s*(?:of|=|:)?\s*([\d.]+)", "HR"),
        (r"odds\s+ratio\s*(?:of|=|:)?\s*([\d.]+)", "OR"),
        (r"OR\s*(?:of|=|:)?\s*([\d.]+)", "OR"),
        (r"(?:relative\s+)?risk\s+(?:ratio|reduction)\s*(?:of|=|:)?\s*([\d.]+)", "RR"),
        (r"(\d+(?:\.\d+)?)\s*%\s*(?:reduction|improvement|response)", "%"),
    ]

    # AdCom 패턴
    ADCOM_PATTERNS = [
        r"advisory\s+committee\s+(?:meeting|review|vote)",
        r"(?:FDA\s+)?ad\s*com\s+(?:meeting|vote|recommend)",
        r"ODAC\s+(?:meeting|vote|recommend)",
        r"voted\s+(\d+)\s*[-–to]+\s*(\d+)",
        r"(\d+)\s*[-–to]+\s*(\d+)\s+(?:vote|in\s+favor)",
        r"recommend(?:ed|s)?\s+(?:approval|approvable)",
        r"voted\s+(?:unanimously\s+)?(?:in\s+favor|to\s+recommend)",
    ]

    # Approval Type 패턴
    APPROVAL_TYPE_PATTERNS = {
        "bla": [
            r"\bBLA\b",
            r"biologics?\s+license\s+application",
            r"biologic(?:s)?\s+(?:drug\s+)?application",
        ],
        "nda": [
            r"\bNDA\b",
            r"new\s+drug\s+application",
        ],
        "anda": [
            r"\bANDA\b",
            r"abbreviated\s+(?:new\s+drug\s+)?application",
            r"generic\s+(?:drug\s+)?application",
        ],
        "snda": [
            r"\bsNDA\b",
            r"\bsBLA\b",
            r"supplemental\s+(?:new\s+drug\s+|biologics?\s+license\s+)?application",
            r"label\s+expansion",
            r"(?:new|additional)\s+indication",
        ],
        "505b2": [
            r"505\s*\(\s*b\s*\)\s*\(\s*2\s*\)",
            r"505b2",
        ],
    }

    def __init__(self):
        self._last_request = 0

    def _rate_limit(self):
        """Rate limit 적용."""
        elapsed = time.time() - self._last_request
        if elapsed < self.MIN_INTERVAL:
            time.sleep(self.MIN_INTERVAL - elapsed)
        self._last_request = time.time()

    def search(
        self,
        ticker: str,
        drug_name: str,
        pdufa_date: str = None,
        indication: str = None,
    ) -> ClinicalSearchResultV2:
        """
        고도화된 임상 데이터 검색.

        Args:
            ticker: 티커 심볼
            drug_name: 약물명 (브랜드명)
            pdufa_date: PDUFA 날짜 (YYYYMMDD)
            indication: 적응증 (옵션)

        Returns:
            ClinicalSearchResultV2
        """
        result = ClinicalSearchResultV2()

        # 약물명 정규화 (괄호 내용 제거, 소문자화)
        clean_drug_name = self._normalize_drug_name(drug_name)

        # PDUFA year 추출
        year = pdufa_date[:4] if pdufa_date and len(pdufa_date) >= 4 else None

        # 검색 쿼리 구성 (우선순위 순)
        queries = self._build_queries(ticker, clean_drug_name, year, indication)
        result.queries_used = queries

        # 검색 실행 및 결과 수집
        all_results = []
        for query in queries[:3]:  # 상위 3개 쿼리만 사용
            try:
                self._rate_limit()
                search_results = DDGS().text(query, max_results=5)
                all_results.extend(search_results)
            except Exception as e:
                logger.warning(f"DDG search failed for '{query[:50]}...': {e}")

        if not all_results:
            return result

        # 결과 분석 (약물명 언급 확인)
        analyzed = self._analyze_results(all_results, clean_drug_name, drug_name)
        result.total_results_analyzed = len(all_results)
        result.drug_mention_rate = analyzed["mention_rate"]

        # 약물 언급률이 너무 낮으면 결과 신뢰 불가
        if analyzed["mention_rate"] < self.MIN_DRUG_MENTION_RATE:
            logger.info(f"  Low drug mention rate ({analyzed['mention_rate']:.1%}), skipping")
            return result

        # 약물명이 언급된 텍스트만 사용
        relevant_text = analyzed["relevant_text"]

        # Primary Endpoint 분석
        self._analyze_endpoint(result, relevant_text, analyzed["evidences"])

        # P-value 추출
        self._extract_pvalue(result, relevant_text)

        # Effect Size 추출
        self._extract_effect_size(result, relevant_text)

        # AdCom 분석
        self._analyze_adcom(result, relevant_text)

        # Approval Type 분류
        self._classify_approval_type(result, relevant_text)

        result.found = (
            result.endpoint_met is not None
            or result.p_value is not None
            or result.adcom_held is not None
            or result.approval_type is not None
        )

        return result

    def _normalize_drug_name(self, drug_name: str) -> str:
        """약물명 정규화."""
        # 괄호 내용 제거
        name = re.sub(r'\s*\([^)]*\)', '', drug_name)
        # 특수문자 제거
        name = re.sub(r'[^\w\s-]', '', name)
        # 연속 공백 정리
        name = ' '.join(name.split())
        return name.strip()

    def _build_queries(
        self,
        ticker: str,
        drug_name: str,
        year: str = None,
        indication: str = None,
    ) -> list[str]:
        """검색 쿼리 구성."""
        queries = []

        # 1. 기본 쿼리: 약물명 + phase 3 + primary endpoint
        base = f'"{drug_name}" phase 3 primary endpoint'
        if year:
            base += f" {year}"
        queries.append(base)

        # 2. 티커 + 약물명 + 임상 결과
        queries.append(f'{ticker} "{drug_name}" clinical trial results')

        # 3. 약물명 + FDA + approval
        queries.append(f'"{drug_name}" FDA approval NDA BLA')

        # 4. indication이 있으면 추가 쿼리
        if indication:
            queries.append(f'"{drug_name}" {indication} phase 3 results')

        # 5. AdCom 전용 쿼리
        queries.append(f'"{drug_name}" FDA advisory committee')

        return queries

    def _analyze_results(
        self,
        results: list[dict],
        clean_drug_name: str,
        original_drug_name: str,
    ) -> dict:
        """검색 결과 분석."""
        relevant_texts = []
        evidences = []
        mention_count = 0

        # 약물명 패턴 (여러 형태)
        drug_patterns = [
            clean_drug_name.lower(),
            original_drug_name.lower(),
            clean_drug_name.split()[0].lower() if clean_drug_name else "",
        ]
        drug_patterns = [p for p in drug_patterns if len(p) > 2]

        for r in results:
            title = r.get("title", "")
            body = r.get("body", "")
            url = r.get("href", "")
            combined = f"{title} {body}".lower()

            # 약물명 언급 확인
            mentioned = any(p in combined for p in drug_patterns)

            if mentioned:
                mention_count += 1
                relevant_texts.append(f"{title} {body}")
                evidences.append(SearchEvidence(
                    text=body[:300],
                    source_url=url,
                    drug_mentioned=True,
                ))

        mention_rate = mention_count / len(results) if results else 0

        return {
            "relevant_text": " ".join(relevant_texts),
            "evidences": evidences,
            "mention_rate": mention_rate,
            "mention_count": mention_count,
        }

    def _analyze_endpoint(
        self,
        result: ClinicalSearchResultV2,
        text: str,
        evidences: list[SearchEvidence],
    ) -> None:
        """Primary endpoint 분석."""
        text_lower = text.lower()

        positive_count = sum(
            1 for p in self.ENDPOINT_POSITIVE_PATTERNS
            if re.search(p, text_lower)
        )
        negative_count = sum(
            1 for p in self.ENDPOINT_NEGATIVE_PATTERNS
            if re.search(p, text_lower)
        )

        if positive_count > 0 or negative_count > 0:
            if positive_count > negative_count:
                result.endpoint_met = True
                result.endpoint_confidence = min(0.9, 0.6 + positive_count * 0.1)
            elif negative_count > positive_count:
                result.endpoint_met = False
                result.endpoint_confidence = min(0.9, 0.6 + negative_count * 0.1)
            else:
                # 동점이면 positive 우선 (보수적)
                result.endpoint_met = True
                result.endpoint_confidence = 0.5

            result.endpoint_evidence = evidences[:3]

    def _extract_pvalue(self, result: ClinicalSearchResultV2, text: str) -> None:
        """P-value 추출."""
        text_lower = text.lower()

        for pattern, _ in self.PVALUE_PATTERNS:
            match = re.search(pattern, text_lower)
            if match:
                try:
                    value = match.group(1)
                    result.p_value = value
                    result.p_value_numeric = float(value)
                    return
                except (ValueError, IndexError):
                    continue

        # "p<0.001" 형태 처리
        if "p<0.0001" in text_lower or "p < 0.0001" in text_lower:
            result.p_value = "<0.0001"
            result.p_value_numeric = 0.00005
        elif "p<0.001" in text_lower or "p < 0.001" in text_lower:
            result.p_value = "<0.001"
            result.p_value_numeric = 0.0005

    def _extract_effect_size(self, result: ClinicalSearchResultV2, text: str) -> None:
        """Effect size 추출."""
        text_lower = text.lower()

        for pattern, effect_type in self.EFFECT_SIZE_PATTERNS:
            match = re.search(pattern, text_lower)
            if match:
                try:
                    result.effect_size = match.group(1)
                    result.effect_type = effect_type
                    return
                except (ValueError, IndexError):
                    continue

    def _analyze_adcom(self, result: ClinicalSearchResultV2, text: str) -> None:
        """AdCom 분석."""
        text_lower = text.lower()

        # AdCom 언급 확인
        adcom_mentioned = any(
            re.search(p, text_lower) for p in self.ADCOM_PATTERNS[:4]
        )

        if adcom_mentioned:
            result.adcom_held = True

            # 투표 결과 추출
            vote_match = re.search(r"voted?\s+(\d+)\s*[-–to]+\s*(\d+)", text_lower)
            if not vote_match:
                vote_match = re.search(r"(\d+)\s*[-–to]+\s*(\d+)\s+vote", text_lower)

            if vote_match:
                try:
                    yes = int(vote_match.group(1))
                    no = int(vote_match.group(2))
                    result.adcom_vote = f"{yes}-{no}"
                    result.adcom_vote_ratio = yes / (yes + no) if (yes + no) > 0 else None
                except (ValueError, ZeroDivisionError):
                    pass

    def _classify_approval_type(self, result: ClinicalSearchResultV2, text: str) -> None:
        """Approval type 분류."""
        text_lower = text.lower()

        # 우선순위: ANDA > sNDA > BLA > NDA > 505b2
        for app_type in ["anda", "snda", "bla", "nda", "505b2"]:
            patterns = self.APPROVAL_TYPE_PATTERNS.get(app_type, [])
            if any(re.search(p, text_lower, re.IGNORECASE) for p in patterns):
                result.approval_type = app_type
                return


def enrich_event_v2(
    ticker: str,
    drug_name: str,
    pdufa_date: str = None,
    indication: str = None,
) -> dict:
    """
    고도화된 이벤트 enrichment.

    Returns:
        {
            "found": bool,
            "primary_endpoint_met": bool or None,
            "endpoint_confidence": float,
            "p_value": str or None,
            "p_value_numeric": float or None,
            "effect_size": str or None,
            "adcom_held": bool or None,
            "adcom_vote": str or None,
            "approval_type": str or None,
            "drug_mention_rate": float,
            "queries_used": list[str],
        }
    """
    searcher = DDGClinicalSearcherV2()
    result = searcher.search(
        ticker=ticker,
        drug_name=drug_name,
        pdufa_date=pdufa_date,
        indication=indication,
    )

    return {
        "found": result.found,
        "primary_endpoint_met": result.endpoint_met,
        "endpoint_confidence": result.endpoint_confidence,
        "p_value": result.p_value,
        "p_value_numeric": result.p_value_numeric,
        "effect_size": result.effect_size,
        "effect_type": result.effect_type,
        "adcom_held": result.adcom_held,
        "adcom_vote": result.adcom_vote,
        "adcom_vote_ratio": result.adcom_vote_ratio,
        "approval_type": result.approval_type,
        "drug_mention_rate": result.drug_mention_rate,
        "queries_used": result.queries_used,
        "total_results_analyzed": result.total_results_analyzed,
    }
