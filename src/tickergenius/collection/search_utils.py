"""
Search Utilities
=================
공용 검색 쿼리 빌더 및 결과 검증 유틸리티.

참조: docs/SEARCH_IMPROVEMENT_DESIGN.md
"""

import re
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """검색 결과 검증 결과."""
    is_valid: bool
    confidence: float
    errors: list[str]
    warnings: list[str]

    @classmethod
    def valid(cls, confidence: float = 1.0) -> "ValidationResult":
        return cls(is_valid=True, confidence=confidence, errors=[], warnings=[])

    @classmethod
    def invalid(cls, errors: list[str]) -> "ValidationResult":
        return cls(is_valid=False, confidence=0.0, errors=errors, warnings=[])


class SearchQueryBuilder:
    """검색 쿼리 빌더."""

    @staticmethod
    def drug_name_variants(drug_name: str) -> list[str]:
        """
        약물명 변형 생성.

        Examples:
            "Opdivo Plus Yervoy" -> ["Opdivo Plus Yervoy", "Opdivo", "Yervoy"]
            "IBTROZI (Taletrectinib)" -> ["IBTROZI (Taletrectinib)", "IBTROZI", "Taletrectinib"]
        """
        if not drug_name:
            return []

        variants = []

        # 1. 전체 이름 (정확 매칭용)
        variants.append(drug_name)

        # 2. 첫 단어 (브랜드명)
        parts = drug_name.split()
        if parts:
            brand = parts[0].strip("()")
            if brand and brand != drug_name:
                variants.append(brand)

        # 3. 괄호 안 제네릭명 추출
        generic_match = re.search(r'\(([^)]+)\)', drug_name)
        if generic_match:
            generic = generic_match.group(1)
            if generic and generic not in variants:
                variants.append(generic)

        # 4. "plus" 처리 (조합 약물)
        if " plus " in drug_name.lower():
            base = drug_name.lower().split(" plus ")[0].strip()
            if base and base.title() not in variants:
                variants.append(base.title())

            # 두 번째 약물도 추가
            second = drug_name.lower().split(" plus ")[1].strip()
            if second:
                second_clean = second.split()[0].title()
                if second_clean not in variants:
                    variants.append(second_clean)

        # 5. 하이픈 처리 (AXS-05 -> AXS05, AXS-05)
        if "-" in drug_name:
            no_hyphen = drug_name.replace("-", "")
            if no_hyphen not in variants:
                variants.append(no_hyphen)

        # 6. sNDA/sBLA 표기 제거
        for suffix in [" sNDA", " sBLA", " NDA", " BLA"]:
            for v in list(variants):
                if suffix in v:
                    clean = v.replace(suffix, "").strip()
                    if clean and clean not in variants:
                        variants.append(clean)

        # 중복 제거 (순서 유지)
        seen = set()
        unique = []
        for v in variants:
            v_lower = v.lower()
            if v_lower not in seen:
                seen.add(v_lower)
                unique.append(v)

        return unique

    @staticmethod
    def build_crl_query(ticker: str, drug_name: str) -> str:
        """CRL 검색 쿼리 생성."""
        brand = drug_name.split()[0] if drug_name else ""
        return f'{ticker} "{brand}" FDA "complete response letter" OR CRL'

    @staticmethod
    def build_designation_query(
        ticker: str,
        drug_name: str,
        designation: str
    ) -> str:
        """
        FDA 지정 검색 쿼리 생성.

        Args:
            designation: "btd", "orphan", "priority", "fast_track"
        """
        brand = drug_name.split()[0] if drug_name else ""

        designation_terms = {
            "btd": '"breakthrough therapy designation" OR "breakthrough therapy"',
            "orphan": '"orphan drug designation" OR "orphan designation"',
            "priority": '"priority review" OR "priority review designation"',
            "fast_track": '"fast track designation" OR "fast track"',
        }

        term = designation_terms.get(designation, designation)
        return f'{ticker} "{brand}" FDA {term}'

    @staticmethod
    def build_adcom_query(ticker: str, drug_name: str) -> str:
        """AdCom 검색 쿼리 생성."""
        brand = drug_name.split()[0] if drug_name else ""
        return f'{ticker} "{brand}" FDA "advisory committee" OR AdCom'


class SearchResultValidator:
    """검색 결과 검증기."""

    # 신뢰할 수 있는 출처 도메인
    TRUSTED_DOMAINS = {
        "tier1": [
            "fda.gov",
            "sec.gov",
            "clinicaltrials.gov",
        ],
        "tier2": [
            "biospace.com",
            "fiercepharma.com",
            "fiercebiotech.com",
            "reuters.com",
            "businesswire.com",
            "prnewswire.com",
            "globenewswire.com",
        ],
        "tier3": [
            "seekingalpha.com",
            "biopharmcatalyst.com",
            "yahoo.com",
            "bloomberg.com",
        ],
    }

    @classmethod
    def get_source_tier(cls, url: str) -> int:
        """URL에서 소스 티어 결정."""
        url_lower = url.lower()
        for tier, domains in cls.TRUSTED_DOMAINS.items():
            for domain in domains:
                if domain in url_lower:
                    return int(tier[-1])
        return 4  # 알 수 없는 소스

    @classmethod
    def validate_date_format(cls, date_str: str) -> bool:
        """날짜 형식 검증 (YYYYMMDD)."""
        if not date_str:
            return False

        # 하이픈 제거
        normalized = date_str.replace("-", "").replace("/", "")[:8]

        if len(normalized) != 8:
            return False

        try:
            datetime.strptime(normalized, "%Y%m%d")
            return True
        except ValueError:
            return False

    @classmethod
    def validate_crl_result(
        cls,
        result: dict,
        expected_ticker: str,
        expected_drug: str,
        max_date: str = None
    ) -> ValidationResult:
        """
        CRL 검색 결과 검증.

        Args:
            result: 검색 결과 dict (date, source, url, content)
            expected_ticker: 예상 티커
            expected_drug: 예상 약물명
            max_date: 최대 날짜 (이 날짜 이전이어야 함)
        """
        errors = []
        warnings = []
        confidence = 1.0

        # 1. 날짜 형식 검증
        date = result.get("date", "")
        if not cls.validate_date_format(date):
            errors.append(f"Invalid date format: {date}")

        # 2. 날짜 범위 검증
        if max_date and date:
            if date > max_date.replace("-", ""):
                errors.append(f"Date {date} is after max_date {max_date}")

        # 3. 소스 신뢰도 검증
        url = result.get("url", "")
        tier = cls.get_source_tier(url)
        if tier > 3:
            warnings.append(f"Low confidence source: {url}")
            confidence *= 0.7

        # 4. 컨텐츠 내 티커/약물명 확인
        content = result.get("content", "").upper()
        if content:
            if expected_ticker and expected_ticker.upper() not in content:
                warnings.append(f"Ticker {expected_ticker} not found in content")
                confidence *= 0.8

            # 약물명 변형 중 하나라도 있으면 OK
            drug_variants = SearchQueryBuilder.drug_name_variants(expected_drug)
            drug_found = any(v.upper() in content for v in drug_variants)
            if not drug_found:
                warnings.append(f"Drug name not found in content")
                confidence *= 0.7

        if errors:
            return ValidationResult.invalid(errors)

        return ValidationResult(
            is_valid=True,
            confidence=confidence,
            errors=errors,
            warnings=warnings
        )

    @classmethod
    def validate_designation_result(
        cls,
        result: dict,
        expected_ticker: str,
        expected_drug: str,
        designation_type: str,
    ) -> ValidationResult:
        """
        FDA 지정 검색 결과 검증.

        Args:
            designation_type: "btd", "orphan", "priority", "fast_track"
        """
        errors = []
        warnings = []
        confidence = 1.0

        # 소스 신뢰도
        url = result.get("url", "")
        tier = cls.get_source_tier(url)
        if tier > 2:
            warnings.append(f"Lower confidence source for designation: {url}")
            confidence *= 0.8

        # 컨텐츠 내 지정 키워드 확인
        content = result.get("content", "").upper()
        designation_keywords = {
            "btd": ["BREAKTHROUGH THERAPY", "BTD"],
            "orphan": ["ORPHAN DRUG", "ORPHAN DESIGNATION"],
            "priority": ["PRIORITY REVIEW"],
            "fast_track": ["FAST TRACK"],
        }

        keywords = designation_keywords.get(designation_type, [])
        keyword_found = any(kw in content for kw in keywords)
        if not keyword_found:
            errors.append(f"Designation keyword not found for {designation_type}")

        # 티커/약물명 확인
        if expected_ticker and expected_ticker.upper() not in content:
            warnings.append(f"Ticker not found in content")
            confidence *= 0.85

        if errors:
            return ValidationResult.invalid(errors)

        return ValidationResult(
            is_valid=True,
            confidence=confidence,
            errors=errors,
            warnings=warnings
        )


def extract_date_from_text(text: str) -> Optional[str]:
    """
    텍스트에서 날짜 추출.

    Returns:
        YYYYMMDD 형식 날짜 또는 None
    """
    if not text:
        return None

    # 패턴 1: Month DD, YYYY (예: January 15, 2024)
    month_pattern = re.compile(
        r"(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2}),?\s+(\d{4})",
        re.IGNORECASE
    )

    # 패턴 2: YYYY-MM-DD
    iso_pattern = re.compile(r"(\d{4})-(\d{2})-(\d{2})")

    # 패턴 3: MM/DD/YYYY
    slash_pattern = re.compile(r"(\d{1,2})/(\d{1,2})/(\d{4})")

    month_map = {
        "january": "01", "february": "02", "march": "03", "april": "04",
        "may": "05", "june": "06", "july": "07", "august": "08",
        "september": "09", "october": "10", "november": "11", "december": "12",
    }

    # 패턴 1 시도
    match = month_pattern.search(text)
    if match:
        month = month_map[match.group(1).lower()]
        day = match.group(2).zfill(2)
        year = match.group(3)
        return f"{year}{month}{day}"

    # 패턴 2 시도
    match = iso_pattern.search(text)
    if match:
        return f"{match.group(1)}{match.group(2)}{match.group(3)}"

    # 패턴 3 시도
    match = slash_pattern.search(text)
    if match:
        month = match.group(1).zfill(2)
        day = match.group(2).zfill(2)
        year = match.group(3)
        return f"{year}{month}{day}"

    return None
